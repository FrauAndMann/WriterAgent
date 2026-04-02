from openai import OpenAI
from writer_agent.config import Config


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.lm_studio_url
        self.model = config.model_name
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

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature or self.config.temperature,
            top_p=self.config.top_p,
        )
        return response.choices[0].message.content

    def chat(self, messages: list[dict], max_tokens: int = 4000) -> str:
        """Direct multi-turn chat for brainstorm mode."""
        model = self.get_available_model()
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )
        return response.choices[0].message.content

    def count_tokens(self, text: str) -> int:
        """Rough token count estimate (~4 chars per token for English, ~2 for Cyrillic)."""
        cyrillic_chars = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        other_chars = len(text) - cyrillic_chars
        return int(cyrillic_chars / 2 + other_chars / 4)
