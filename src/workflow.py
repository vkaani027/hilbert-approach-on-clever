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
    lowered = text.lower()
    if 'impossible' in lowered or '???' in lowered or 'fail' in lowered:
        return 'impossible'
    if 'lemma' in lowered or '??' in lowered or 'decompose' in lowered or '?' in lowered:
        return 'decompose'
    return 'continue'


def parse_lemma_list(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip('-? 	')
        if stripped:
            lines.append(stripped)
    return lines[:5]
