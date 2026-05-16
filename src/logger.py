from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import sys
from collections import defaultdict


@dataclass
class Event:
    timestamp: str
    level: str
    theorem: str
    stage: str
    message: str


class RunLogger:
    def __init__(self, traces_dir: Path, enabled: bool = True):
        self.traces_dir = traces_dir
        self.enabled = enabled
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self._events_by_theorem: dict[str, list[dict]] = defaultdict(list)

    def emit(self, theorem: str, stage: str, message: str, level: str = 'INFO') -> None:
        event = Event(
            timestamp=datetime.now().isoformat(timespec='seconds'),
            level=level,
            theorem=theorem,
            stage=stage,
            message=message,
        )
        if self.enabled:
            print(f"[{event.timestamp}] [{event.level}] [{event.stage}] {event.theorem}: {event.message}", flush=True)
        self._events_by_theorem[theorem].append(event.__dict__)
        with (self.traces_dir / 'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(event.__dict__, ensure_ascii=False) + '\n')

    def theorem_events(self, theorem: str) -> list[dict]:
        return list(self._events_by_theorem.get(theorem, []))
