from __future__ import annotations

from .types import Problem


class PromptBank:
    def __init__(self, config: dict):
        self.config = config

    def informal_plan(self, problem: Problem) -> list[dict[str, str]]:
        return [
            {'role': 'system', 'content': self.config['prompts']['informal_plan_system']},
            {'role': 'user', 'content': problem.informal_prefix + '\n' + problem.formal_statement},
        ]

    def informal_decision(self, problem: Problem, verifier_error: str, proof_code: str, mode: str) -> list[dict[str, str]]:
        if mode == 'decompose':
            system = self.config['prompts']['informal_decompose_system']
        elif mode == 'continue':
            system = self.config['prompts']['informal_continue_system']
        else:
            system = self.config['prompts']['informal_impossible_system']
        user = problem.header + '\n' + problem.formal_statement + '\n' + verifier_error + '\n' + proof_code
        return [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ]

    def formal_proof(self, problem: Problem, proof_code: str, verifier_error: str, informal_plan: str) -> list[dict[str, str]]:
        messages = [
            {'role': 'system', 'content': self.config['prompts']['formal_system']},
            {'role': 'user', 'content': problem.header + '\n' + problem.formal_statement},
        ]
        if informal_plan:
            messages.append({'role': 'assistant', 'content': self.config['prompts']['proof_plan_prefix'] + '\n' + informal_plan})
        if proof_code:
            messages.append({'role': 'assistant', 'content': self.config['prompts']['previous_attempt_prefix'] + '\n' + proof_code})
        if verifier_error:
            messages.append({'role': 'user', 'content': self.config['prompts']['verifier_error_prefix'] + '\n' + verifier_error})
        return messages
