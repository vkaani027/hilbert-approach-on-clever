from __future__ import annotations

import json
from pathlib import Path
from .types import Problem


def _from_dict(item: dict) -> Problem:
    return Problem(
        name=item.get('name') or item.get('theorem_name') or item.get('id') or 'unknown',
        header=item.get('header', ''),
        formal_statement=item.get('formal_statement', ''),
        informal_prefix=item.get('informal_prefix', ''),
        split=item.get('split', ''),
        extra={k: v for k, v in item.items() if k not in {'name', 'theorem_name', 'id', 'header', 'formal_statement', 'informal_prefix', 'split'}},
    )


def load_problems(path: Path) -> list[Problem]:
    if path.suffix == '.jsonl':
        items = []
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(_from_dict(json.loads(line)))
                except json.JSONDecodeError:
                    continue
        return items
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, list):
        return [_from_dict(item) for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [_from_dict(data)]
    return []
