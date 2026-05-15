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

    def informal_decision(self, problem: Problem, verifier_error: str, proof_code: str) -> list[dict[str, str]]:
        return [
            {'role': 'system', 'content': self.config['prompts']['informal_decision_system']},
            {'role': 'user', 'content': (
                'Decide the next action after a failed Lean proof attempt.\n'
                'Choose exactly one label on the first line: CONTINUE, DECOMPOSE, or IMPOSSIBLE.\n'
                'CONTINUE means the proof looks close and the next attempt should continue without regenerating the plan.\n'
                'DECOMPOSE means the theorem looks too hard and should be split into lemmas. If you choose DECOMPOSE, you must also provide a numbered list of natural-language lemmas on the following lines. The lemmas must be independent: do not make later lemmas depend on earlier lemmas by name or by assuming only their conclusions; if a logical intermediate statement is needed, include it in full.\n'
                'IMPOSSIBLE means the current proof attempt shows no progress and the theorem appears unprovable with the current approach.\n'
                'After the first line, you may add one short explanation line. Do not output Lean code.\n\n'
                f'Lean header:\n{problem.header}\n\n'
                f'Lean statement:\n{problem.formal_statement}\n\n'
                f'Previous proof attempt:\n{proof_code}\n\n'
                f'Verifier error:\n{verifier_error}\n'
            )},
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
        messages.append({'role': 'user', 'content': self.config['prompts']['formal_skeleton_instruction']})
        return messages
