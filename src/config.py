from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class Config:
    raw: dict

    def __getitem__(self, key):
        return self.raw[key]


def load_config(path: Path) -> Config:
    with path.open('r', encoding='utf-8') as f:
        return Config(yaml.safe_load(f))
