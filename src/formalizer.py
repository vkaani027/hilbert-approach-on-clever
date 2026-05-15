from __future__ import annotations

import re
from dataclasses import dataclass

from .llm import LLMConfig, OpenAILLM
from .types import Problem


@dataclass
class FormalizerResult:
    theorem_code: str
    raw_output: str


def extract_lean_code(text_input: str) -> str:
    matches = re.findall(r'```lean4\n(.*?)\n```', text_input, re.DOTALL)
    if matches:
        return matches[-1].strip()
    matches = re.findall(r'```lean\n(.*?)\n```', text_input, re.DOTALL)
    if matches:
        return matches[-1].strip()
    raise ValueError('formalizer output missing Lean code block')


class Formalizer:
    def __init__(self, section: dict, prompt_section: dict):
        self.model = OpenAILLM(LLMConfig(**section))
        self.prompt_section = prompt_section

    def formalize(self, problem: Problem, theorem_name: str | None = None, informal_statement: str | None = None) -> FormalizerResult:
        name = theorem_name or problem.name
        statement = informal_statement or problem.informal_prefix or problem.formal_statement
        prompt = self.prompt_section['user_template'].format(problem_name=name, nl_statement=statement)
        messages = [
            {'role': 'system', 'content': self.prompt_section['system']},
            {'role': 'user', 'content': prompt},
        ]
        raw = self.model.complete(messages)
        theorem_code = extract_lean_code(raw)
        return FormalizerResult(theorem_code=theorem_code, raw_output=raw)
