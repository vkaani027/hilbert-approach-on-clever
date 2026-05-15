from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Problem:
    name: str
    header: str
    formal_statement: str
    informal_prefix: str = ""
    split: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttemptResult:
    success: bool
    proof_code: str = ""
    error: str = ""
    elapsed_seconds: float = 0.0
    attempts: int = 0
    lemmas: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    name: str
    status: str
    proof_path: str | None
    elapsed_seconds: float
    error: str = ""
