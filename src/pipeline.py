from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from .dataset import load_problems
from .llm import LLMConfig, OpenAILLM
from .prompts import PromptBank
from .types import RunResult, Problem
from .verifier import LeanVerifier
from .workflow import write_result_files, parse_decision, parse_lemma_list


def _make_llm(section: dict) -> OpenAILLM:
    return OpenAILLM(LLMConfig(**section))


def _save_trace(traces_dir: Path, name: str, payload: dict) -> None:
    traces_dir.mkdir(parents=True, exist_ok=True)
    (traces_dir / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _prove_problem(problem: Problem, formal: OpenAILLM, informal: OpenAILLM, verifier: LeanVerifier, config: dict, prompts: PromptBank, traces_dir: Path, proofs_dir: Path) -> RunResult:
    start = perf_counter()
    max_formal_attempts = config['workflow']['max_formal_attempts']
    max_outer_loops = config['workflow']['max_outer_loops']
    max_lemma_rounds = config['workflow']['max_lemma_rounds']
    proof_code = ''
    verifier_error = ''
    informal_plan = ''
    lemmas: list[str] = []

    for _ in range(max_outer_loops):
        informal_plan = informal.complete(prompts.informal_plan(problem))
        for _ in range(max_formal_attempts):
            proof_code = formal.complete(prompts.formal_proof(problem, proof_code, verifier_error, informal_plan))
            verification = verifier.verify(problem.header + '\n' + proof_code)
            if verification.success:
                proof_path = proofs_dir / f'{problem.name}.lean'
                proof_path.write_text(problem.header + '\n' + proof_code, encoding='utf-8')
                result = RunResult(problem.name, 'success', str(proof_path), perf_counter() - start, '')
                _save_trace(traces_dir, problem.name, {'problem': asdict(problem), 'informal_plan': informal_plan, 'proof_code': proof_code, 'result': asdict(result), 'lemmas': lemmas})
                return result
            verifier_error = verification.output

        decision_text = informal.complete(prompts.informal_decision(problem, verifier_error, proof_code, 'continue'))
        decision = parse_decision(decision_text)
        if decision == 'impossible':
            result = RunResult(problem.name, 'failed', None, perf_counter() - start, verifier_error)
            _save_trace(traces_dir, problem.name, {'problem': asdict(problem), 'informal_plan': informal_plan, 'decision': decision_text, 'result': asdict(result), 'lemmas': lemmas})
            return result
        if decision == 'decompose':
            lemma_text = informal.complete(prompts.informal_decision(problem, verifier_error, proof_code, 'decompose'))
            lemmas = parse_lemma_list(lemma_text)[: config['workflow']['max_lemma_count']]
            for lemma_round, lemma in enumerate(lemmas[:max_lemma_rounds]):
                lemma_problem = Problem(name=f'{problem.name}__lemma_{lemma_round}', header=problem.header, formal_statement=lemma, informal_prefix=problem.informal_prefix, split=problem.split, extra=problem.extra)
                lemma_result = _prove_problem(lemma_problem, formal, informal, verifier, config, prompts, traces_dir, proofs_dir)
                if lemma_result.status != 'success':
                    result = RunResult(problem.name, 'failed', None, perf_counter() - start, f'lemma failed: {lemma}')
                    _save_trace(traces_dir, problem.name, {'problem': asdict(problem), 'informal_plan': informal_plan, 'decision': decision_text, 'lemmas': lemmas, 'result': asdict(result)})
                    return result
        else:
            verifier_error = verifier_error[:4000]

    result = RunResult(problem.name, 'failed', None, perf_counter() - start, verifier_error)
    _save_trace(traces_dir, problem.name, {'problem': asdict(problem), 'informal_plan': informal_plan, 'result': asdict(result), 'lemmas': lemmas})
    return result


def run_pipeline(config):
    data = config.raw['data']
    formal = _make_llm(config.raw['formal_llm'])
    informal = _make_llm(config.raw['informal_llm'])
    verifier = LeanVerifier(**config.raw['verifier'])
    prompts = PromptBank(config.raw)

    input_path = Path(data['input_path'])
    output_dir = Path(data['output_dir'])
    proofs_dir = Path(data['proofs_dir'])
    traces_dir = Path(data['traces_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)
    proofs_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    problems = load_problems(input_path)
    if data.get('max_samples'):
        problems = problems[: data['max_samples']]

    results = []
    workers = int(data.get('workers', 1))
    if workers > 1 and len(problems) > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(_prove_problem, problem, formal, informal, verifier, config.raw, prompts, traces_dir, proofs_dir): problem for problem in problems}
            for future in as_completed(future_map):
                result = future.result()
                write_result_files(output_dir, result, '')
                results.append(asdict(result))
    else:
        for problem in problems:
            result = _prove_problem(problem, formal, informal, verifier, config.raw, prompts, traces_dir, proofs_dir)
            write_result_files(output_dir, result, '')
            results.append(asdict(result))

    (output_dir / 'results.jsonl').write_text('\n'.join(json.dumps(item, ensure_ascii=False) for item in results), encoding='utf-8')
    (output_dir / 'metrics_summary.json').write_text(json.dumps({'total': len(results), 'success': sum(1 for r in results if r['status'] == 'success')}, indent=2, ensure_ascii=False), encoding='utf-8')
