from __future__ import annotations

from .types import Problem


class PromptBank:
    def __init__(self, config: dict):
        self.config = config

    def informal_plan(self, problem: Problem) -> list[dict[str, str]]:
        return [
            {'role': 'system', 'content': self.config['prompts']['informal_plan_system']},
            {'role': 'user', 'content': (
                'Task: produce a concise proof plan for the Lean problem below.\n\n'
                f'Lean header:\n{problem.header}\n\n'
                f'Theorem statement:\n{problem.formal_statement}\n\n'
                f'Problem description:\n{problem.informal_prefix}\n\n'
                'Requirements:\n'
                '- Output natural language only.\n'
                '- Do not output Lean code.\n'
                '- Focus on the current theorem and its context.\n'
                '- Keep the plan concise and actionable.'
            )},
        ]

    def informal_decision(self, problem: Problem, verifier_error: str, proof_code: str) -> list[dict[str, str]]:
        return [
            {'role': 'system', 'content': self.config['prompts']['informal_decision_system']},
            {'role': 'user', 'content': (
                'Task: decide the next action after the failed Lean proof attempt below.\n\n'
                f'Lean header:\n{problem.header}\n\n'
                f'Theorem statement:\n{problem.formal_statement}\n\n'
                f'Previous proof attempt:\n{proof_code}\n\n'
                f'Verifier error:\n{verifier_error}\n\n'
                'Requirements:\n'
                '- Output exactly one label on the first line: CONTINUE, DECOMPOSE, or IMPOSSIBLE.\n'
                '- CONTINUE means the proof looks close and the next attempt should continue without regenerating the plan.\n'
                '- DECOMPOSE means the theorem is too hard and should be split into independent lemmas.\n'
                '- IMPOSSIBLE means the current proof attempt shows no progress and the theorem appears unprovable with the current approach.\n'
                '- After the first line, you may add one short explanation line.\n'
                '- Do not output Lean code.\n'
                '- If you choose DECOMPOSE, the lemmas must be independent and self-contained.'
            )},
        ]

    def formal_proof(self, problem: Problem, proof_code: str, verifier_error: str, informal_plan: str) -> list[dict[str, str]]:
        messages = [
            {'role': 'system', 'content': self.config['prompts']['formal_system']},
            {'role': 'user', 'content': (
                'Task: prove the Lean theorem below.\n\n'
                f'Lean header:\n{problem.header}\n\n'
                f'Theorem statement:\n{problem.formal_statement}\n\n'
                'Additional instructions:\n'
                '- Use the current Lean context and any provided plan or prior attempts.\n'
                '- Do not get stuck in repetitive self-checking loops; make decisive progress.\n'
                '- Return only Lean code. Do not explain your reasoning.'
            )},
        ]
        if informal_plan:
            messages.append({'role': 'assistant', 'content': self.config['prompts']['proof_plan_prefix'] + '\n' + informal_plan})
        if proof_code:
            messages.append({'role': 'assistant', 'content': self.config['prompts']['previous_attempt_prefix'] + '\n' + proof_code})
        if verifier_error:
            messages.append({'role': 'user', 'content': self.config['prompts']['verifier_error_prefix'] + '\n' + verifier_error})
        messages.append({
            'role': 'user',
            'content': (
                self.config['prompts']['formal_skeleton_instruction'] + '\n\n'
                'Return the final Lean code inside exactly one fenced code block formatted as:\n'
                '```lean4\n'
                '<Lean code here>\n'
                '```\n'
                'If you produce multiple code blocks, only the last one will be used.'
            ),
        })
        return messages
