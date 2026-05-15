from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class LemmaNode:
    name: str
    kind: str
    children: list['LemmaNode'] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'kind': self.kind,
            'children': [child.to_dict() for child in self.children],
        }


class LemmaTree:
    def __init__(self, root_name: str):
        self.root = LemmaNode(name=root_name, kind='theorem')

    def add_children(self, parent: LemmaNode, names: list[str]) -> list[LemmaNode]:
        nodes = [LemmaNode(name=name, kind='lemma') for name in names]
        parent.children.extend(nodes)
        return nodes

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.root.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
