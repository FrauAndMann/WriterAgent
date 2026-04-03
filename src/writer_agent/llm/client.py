from __future__ import annotations

from typing import TYPE_CHECKING

from openai import OpenAI

if TYPE_CHECKING:
    from writer_agent.settings import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.lmstudio.url
        self.model = settings.lmstudio.model_name
        self._client = OpenAI(base_url=self.base_url, api_key="lm-studio")

    def get_available_model(self) -> str:
        if self.model:
            return self.model
        models = self._client.models.list()
        if models.data:
            return models.data[0].id
        raise RuntimeError("No models available in LM Studio")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context_blocks: list[str] | None = None,
        max_tokens: int = 4000,
        temperature: float | None = None,
    ) -> str:
        model = self.get_available_model()
        messages = [{"role": "system", "content": system_prompt}]

        if context_blocks:
            context_text = "\n\n".join(context_blocks)
            messages.append({"role": "user", "content": f"[Context]\n{context_text}"})
            messages.append({"role": "assistant", "content": "Context received."})

        messages.append({"role": "user", "content": user_prompt})

        gen = self.settings.generation
        effective_max = gen.max_output_tokens if gen.max_output_tokens > 0 else max_tokens

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": effective_max,
            "temperature": temperature or gen.temperature,
            "top_p": gen.top_p,
        }
        if gen.top_k > 0:
            kwargs["top_k"] = gen.top_k
        if gen.min_p > 0:
            kwargs["min_p"] = gen.min_p
        if gen.repetition_penalty != 1.0:
            kwargs["repetition_penalty"] = gen.repetition_penalty
        if gen.frequency_penalty != 0.0:
            kwargs["frequency_penalty"] = gen.frequency_penalty
        if gen.presence_penalty != 0.0:
            kwargs["presence_penalty"] = gen.presence_penalty
        if gen.seed >= 0:
            kwargs["seed"] = gen.seed

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def chat(self, messages: list[dict], max_tokens: int = 4000) -> str:
        """Direct multi-turn chat for brainstorm mode."""
        model = self.get_available_model()
        gen = self.settings.generation
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=gen.max_output_tokens if gen.max_output_tokens > 0 else max_tokens,
            temperature=gen.temperature,
            top_p=gen.top_p,
        )
        return response.choices[0].message.content

    def count_tokens(self, text: str) -> int:
        """Rough token count estimate (~4 chars per token for English, ~2 for Cyrillic)."""
        cyrillic_chars = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        other_chars = len(text) - cyrillic_chars
        return int(cyrillic_chars / 2 + other_chars / 4)
