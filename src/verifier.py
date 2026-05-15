from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    success: bool
    output: str
    returncode: int


class LeanVerifier:
    def __init__(self, lean_command: str, timeout_seconds: int = 60, max_retries: int = 0):
        self.lean_command = lean_command
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _run_once(self, lean_code: str, workdir: Path | None = None) -> VerificationResult:
        with tempfile.NamedTemporaryFile('w', suffix='.lean', delete=False, encoding='utf-8') as f:
            f.write(lean_code)
            temp_path = Path(f.name)
        try:
            cmd = self.lean_command.split() + [str(temp_path)]
            proc = subprocess.run(
                cmd,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            output = (proc.stdout or '') + (proc.stderr or '')
            return VerificationResult(proc.returncode == 0, output, proc.returncode)
        except subprocess.TimeoutExpired as exc:
            return VerificationResult(False, f'Timeout after {self.timeout_seconds}s: {exc}', -1)
        finally:
            temp_path.unlink(missing_ok=True)

    def verify(self, lean_code: str, workdir: Path | None = None) -> VerificationResult:
        last_result = None
        for _ in range(self.max_retries + 1):
            last_result = self._run_once(lean_code, workdir)
            if last_result.success:
                return last_result
        assert last_result is not None
        return last_result
