from __future__ import annotations

from dataclasses import dataclass
from openai import OpenAI


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 1024


class OpenAILLM:
    def __init__(self, config: LLMConfig):
        self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)
        self.config = config

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content or ""
