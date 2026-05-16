from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from .dataset import load_problems
from .formalizer import Formalizer
from .llm import LLMConfig, OpenAILLM
from .logger import RunLogger
from .lemma_tree import LemmaTree, LemmaNode
from .prompts import PromptBank
from .types import RunResult, Problem
from .verifier import LeanVerifier
from .workflow import write_result_files, parse_decision, parse_lemma_list, ensure_required_contents


def _make_llm(section: dict) -> OpenAILLM:
    return OpenAILLM(LLMConfig(**section))


def _save_trace(traces_dir: Path, name: str, payload: dict) -> None:
    traces_dir.mkdir(parents=True, exist_ok=True)
    (traces_dir / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _finalize_failure(problem: Problem, start: float, verifier_error: str, informal_plan: str, lemmas: list[str], traces_dir: Path, logger: RunLogger, reason: str, status: str = 'failed', extra_trace: dict | None = None) -> RunResult:
    result = RunResult(problem.name, status, None, perf_counter() - start, reason)
    trace_payload = {
        'problem': asdict(problem),
        'informal_plan': informal_plan,
        'lemmas': lemmas,
        'result': asdict(result),
        'verifier_error': verifier_error,
    }
    if extra_trace:
        trace_payload.update(extra_trace)
    _save_trace(traces_dir, problem.name, trace_payload)
    logger.emit(problem.name, status, reason)
    return result


def _save_result(output_dir: Path, result: RunResult, proof_code: str = '') -> None:
    write_result_files(output_dir, result, proof_code)


def _lemma_statement(name: str, statement: str) -> str:
    statement = statement.strip()
    if statement.endswith(':= by'):
        return statement
    if ':=' in statement:
        return statement
    if statement.endswith('by'):
        return statement
    return f'{statement} := by\n  sorry'


def _make_sorry_skeleton(header: str, theorem: str, lemma_statements: list[str]) -> tuple[str, list[str]]:
    named_lemmas = []
    sections = [header.rstrip()]
    for index, statement in enumerate(lemma_statements):
        statement = statement.strip()
        if not statement:
            continue
        named_lemmas.append(f'lemma_{index}')
        sections.append(statement)
    theorem_block = theorem.rstrip()
    if not theorem_block.startswith('theorem '):
        theorem_block = f'theorem correctness : {theorem_block}'
    if ':=' not in theorem_block:
        theorem_block = theorem_block + ' := by\n  sorry'
    sections.append(theorem_block)
    return '\n\n'.join(sections).strip() + '\n', named_lemmas
def _fill_skeleton_with_formal(problem: Problem, formal: OpenAILLM, informal_plan: str, skeleton: str, verifier_error: str) -> str:
    messages = [
        {'role': 'system', 'content': 'You are a formal Lean prover. Fill in the proof while preserving the theorem and lemma statements. Output Lean code only.'},
        {'role': 'user', 'content': problem.header + '\n\n' + skeleton},
    ]
    if informal_plan:
        messages.append({'role': 'assistant', 'content': 'Proof plan:\n' + informal_plan})
    if verifier_error:
        messages.append({'role': 'user', 'content': 'Verifier error:\n' + verifier_error})
    return formal.complete(messages)


def _extract_formal_output(text: str) -> str:
    index = text.rfind('lean4')
    if index == -1:
        return text.strip()
    extracted = text[index + len('lean4'):].lstrip('\r\n')
    if extracted.endswith('```'):
        extracted = extracted[:-3].rstrip()
    return extracted


def _compose_verified_proof(header: str, proof_body: str) -> str:
    parts = [part.strip() for part in [header, proof_body] if part and part.strip()]
    return '\n'.join(parts)


def _strip_formalizer_preamble(text: str) -> str:
    stripped = text.lstrip()
    index = stripped.find('theorem ')
    if index == -1:
        return stripped
    return stripped[index:]


def _prove_problem(problem: Problem, formalizer: Formalizer, formal: OpenAILLM, informal: OpenAILLM, verifier: LeanVerifier, config: dict, prompts: PromptBank, traces_dir: Path, proofs_dir: Path, logger: RunLogger, tree: LemmaTree, parent: LemmaNode | None = None) -> RunResult:
    start = perf_counter()
    max_formal_attempts = config['workflow']['max_formal_attempts']
    max_outer_loops = config['workflow']['max_outer_loops']
    max_lemma_rounds = config['workflow']['max_lemma_rounds']
    proof_code = ''
    verifier_error = ''
    informal_plan = ''
    lemmas: list[str] = []
    current_node = parent or tree.root
    header = problem.header
    theorem = problem.formal_statement.strip()

    logger.emit(problem.name, 'start', 'begin theorem')
    logger.emit(problem.name, 'input', 'input is treated as Lean code; main theorem is not formalized')

    informal_plan = informal.complete(prompts.informal_plan(problem))
    logger.emit(problem.name, 'informal_plan', 'proof plan generated')

    for _ in range(max_outer_loops):
        for attempt_index in range(max_formal_attempts):
            logger.emit(problem.name, 'formal_attempt', f'formal attempt {attempt_index + 1}/{max_formal_attempts}')
            proof_code = formal.complete(prompts.formal_proof(problem, proof_code, verifier_error, informal_plan))
            proof_code = _extract_formal_output(proof_code)
            if not ensure_required_contents(proof_code, ['by']):
                verifier_error = 'formal proof output missing required Lean contents'
                logger.emit(problem.name, 'verify_fail', verifier_error)
                continue
            verified_proof = _compose_verified_proof(header, proof_code)
            verification = verifier.verify(verified_proof)
            if verification.success:
                proof_path = proofs_dir / f'{problem.name}.lean'
                proof_path.write_text(verified_proof, encoding='utf-8')
                result = RunResult(problem.name, 'success', str(proof_path), perf_counter() - start, '')
                _save_trace(traces_dir, problem.name, {
                    'problem': asdict(problem),
                    'informal_plan': informal_plan,
                    'formal_raw_output': formal_output_raw,
                    'formal_raw_output_extracted': proof_code,
                    'verified_proof': verified_proof,
                    'formal_raw_output_raw': formal_output_raw,
                    'result': asdict(result),
                    'lemmas': lemmas,
                })
                logger.emit(problem.name, 'success', f'solved in {result.elapsed_seconds:.1f}s')
                return result
            verifier_error = verification.output
            logger.emit(problem.name, 'verify_fail', 'verification failed; retrying')

        decision_text = informal.complete(prompts.informal_decision(problem, verifier_error, proof_code))
        decision = parse_decision(decision_text)
        if not decision:
            verifier_error = 'informal decision output empty or invalid'
            logger.emit(problem.name, 'decision_fail', verifier_error)
            continue
        logger.emit(problem.name, 'decision', f'Informal decision: {decision}')
        if decision == 'continue':
            continue
        if decision == 'impossible':
            continue

        if decision == 'decompose':
            lemma_text = informal.complete(prompts.informal_decision(problem, verifier_error, proof_code))
            if not lemma_text.strip():
                continue
            lemmas = parse_lemma_list(lemma_text)[: config['workflow']['max_lemma_count']]
            if not lemmas:
                continue
            lemma_nodes = tree.add_children(current_node, lemmas)
            logger.emit(problem.name, 'decompose', f'expanded into {len(lemmas)} lemmas')

            formalized_lemmas: list[str] = []
            lemma_problems: list[Problem] = []
            for lemma_round, (lemma, lemma_node) in enumerate(zip(lemmas[:max_lemma_rounds], lemma_nodes[:max_lemma_rounds])):
                lemma_name = f'{problem.name}__lemma_{lemma_round}'
                try:
                    formalized_result = formalizer.formalize(
                        problem,
                        theorem_name=lemma_name,
                        informal_statement=lemma,
                        plan=informal_plan,
                        header=header,
                        theorem=theorem,
                    )
                    formalized_result_code = _strip_formalizer_preamble(formalized_result.theorem_code)
                    if not ensure_required_contents(formalized_result_code, ['theorem', 'by']):
                        raise ValueError(f'formalizer output missing theorem/by for {lemma_name}')
                except Exception as exc:
                    return _finalize_failure(problem, start, verifier_error, informal_plan, lemmas, traces_dir, logger, f'formalizer failed for {lemma_name}: {exc}', extra_trace={'informal_decision': decision_text, 'formal_raw_output': proof_code, 'lemma_text': lemma})

                formalized_lemmas.append(formalized_result_code)
                lemma_problem = Problem(
                    name=lemma_name,
                    header=problem.header,
                    formal_statement=formalized_result.theorem_code,
                    informal_prefix=problem.informal_prefix,
                    split=problem.split,
                    extra={**problem.extra, 'source_lemma_text': lemma, 'formalizer_raw_output': formalized_result.raw_output},
                )
                lemma_problems.append(lemma_problem)
                _save_trace(traces_dir, lemma_name, {
                    'source_lemma_text': lemma,
                    'formalized_lemma': formalized_result_code,
                    'formalizer_raw_output': formalized_result.raw_output,
                })

            skeleton, named_lemmas = _make_sorry_skeleton(header, theorem, formalized_lemmas)
            _save_trace(traces_dir, problem.name, {
                'problem': asdict(problem),
                'informal_plan': informal_plan,
                'lemma_text': lemma_text,
                'formalized_lemmas': formalized_lemmas,
                'proof_skeleton': skeleton,
                'named_lemmas': named_lemmas,
                'lemmas': lemmas,
            })

            formal_output_raw = _fill_skeleton_with_formal(problem, formal, informal_plan, skeleton, verifier_error)
            proof_code = _extract_formal_output(formal_output_raw)
            verified_proof = _compose_verified_proof(header, proof_code)
            verification = verifier.verify(verified_proof)
            if verification.success:
                proof_path = proofs_dir / f'{problem.name}.lean'
                proof_path.write_text(verified_proof, encoding='utf-8')
                result = RunResult(problem.name, 'success', str(proof_path), perf_counter() - start, '')
                _save_trace(traces_dir, problem.name, {
                    'problem': asdict(problem),
                    'informal_plan': informal_plan,
                    'formal_raw_output_raw': formal_output_raw,
                    'formal_raw_output_extracted': proof_code,
                    'verified_proof': verified_proof,
                    'lemma_text': lemma_text,
                    'formalized_lemmas': formalized_lemmas,
                    'proof_skeleton': skeleton,
                    'named_lemmas': named_lemmas,
                    'result': asdict(result),
                    'lemmas': lemmas,
                })
                logger.emit(problem.name, 'success', f'solved in {result.elapsed_seconds:.1f}s')
                return result
            verifier_error = verification.output
            logger.emit(problem.name, 'verify_fail', 'proof skeleton failed after lemma decomposition; retrying')
            continue

        verifier_error = verifier_error[:4000]

    return _finalize_failure(problem, start, verifier_error, informal_plan, lemmas, traces_dir, logger, 'max retries exceeded', extra_trace={'formal_raw_output': proof_code})

def run_pipeline(config):
    data = config.raw['data']
    formalizer = Formalizer(config.raw['formalizer_llm'], config.raw['formalizer_prompt'])
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

    logger = RunLogger(traces_dir, enabled=bool(config.raw.get('runtime', {}).get('show_progress', True)))
    logger.emit('pipeline', 'start', f'loading input from {input_path}')
    problems = load_problems(input_path)
    if data.get('max_samples'):
        problems = problems[: data['max_samples']]
    logger.emit('pipeline', 'load', f'loaded {len(problems)} problems')

    results = []
    workers = int(data.get('workers', 1))
    if workers > 1 and len(problems) > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {}
            for problem in problems:
                tree = LemmaTree(problem.name)
                future = executor.submit(_prove_problem, problem, formalizer, formal, informal, verifier, config.raw, prompts, traces_dir, proofs_dir, logger, tree)
                future_map[future] = (problem, tree)
            for future in as_completed(future_map):
                problem, tree = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = RunResult(problem.name, 'failed', None, 0.0, f'unhandled exception: {exc}')
                    _save_trace(traces_dir, problem.name, {
                        'problem': asdict(problem),
                        'result': asdict(result),
                        'exception': repr(exc),
                    })
                tree.save(traces_dir / f'{problem.name}_lemma_tree.json')
                write_result_files(output_dir, result, '')
                results.append(asdict(result))
    else:
        for problem in problems:
            tree = LemmaTree(problem.name)
            try:
                result = _prove_problem(problem, formalizer, formal, informal, verifier, config.raw, prompts, traces_dir, proofs_dir, logger, tree)
            except Exception as exc:
                result = RunResult(problem.name, 'failed', None, 0.0, f'unhandled exception: {exc}')
                _save_trace(traces_dir, problem.name, {
                    'problem': asdict(problem),
                    'result': asdict(result),
                    'exception': repr(exc),
                })
            tree.save(traces_dir / f'{problem.name}_lemma_tree.json')
            write_result_files(output_dir, result, '')
            results.append(asdict(result))

    (output_dir / 'results.jsonl').write_text('\n'.join(json.dumps(item, ensure_ascii=False) for item in results), encoding='utf-8')
    (output_dir / 'metrics_summary.json').write_text(json.dumps({'total': len(results), 'success': sum(1 for r in results if r['status'] == 'success')}, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.emit('pipeline', 'done', f'finished {len(results)} problems')
