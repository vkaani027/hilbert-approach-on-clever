from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from time import perf_counter
import json

from .types import Problem, RunResult


def build_skeleton(problem: Problem, lemma_text: str = '') -> str:
    return f"""{problem.header}

{problem.formal_statement}

{lemma_text}
"""


def write_result_files(base: Path, result: RunResult, proof_code: str = '') -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{result.name}.json").write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding='utf-8')
    if proof_code:
        (base / f"{result.name}.lean").write_text(proof_code, encoding='utf-8')


def elapsed(start: float) -> float:
    return perf_counter() - start


def parse_decision(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ''
    first_line = stripped.splitlines()[0].strip().upper()
    if first_line in {'CONTINUE', 'IMPOSSIBLE', 'DECOMPOSE'}:
        return first_line.lower()
    return ''


def parse_lemma_list(text: str) -> list[str]:
    lemmas = []
    started = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if not started and upper in {'CONTINUE', 'IMPOSSIBLE', 'DECOMPOSE'}:
            started = True
            continue
        if started:
            if stripped[:1].isdigit() and '.' in stripped[:4]:
                lemma_text = stripped.split('.', 1)[1].strip()
                if lemma_text:
                    lemmas.append(lemma_text)
            elif stripped.startswith(('-', '*', '•')):
                lemma_text = stripped[1:].strip()
                if lemma_text:
                    lemmas.append(lemma_text)
    return lemmas[:5]


def ensure_required_contents(text: str, required: list[str]) -> bool:
    return all(part in text for part in required)
