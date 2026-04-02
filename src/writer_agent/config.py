from pathlib import Path
from dataclasses import dataclass, field
import os


@dataclass
class Config:
    lm_studio_url: str = "http://localhost:1234/v1"
    model_name: str = ""
    max_context_tokens: int = 8192
    temperature: float = 0.8
    top_p: float = 0.95
    db_path: Path = field(default_factory=lambda: Path("data/writer_agent.db"))
    examples_dir: Path = field(default_factory=lambda: Path("data/examples"))
    output_dir: Path = field(default_factory=lambda: Path("data/novels"))

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            lm_studio_url=os.getenv("WRITER_LM_STUDIO_URL", cls.lm_studio_url),
            model_name=os.getenv("WRITER_MODEL_NAME", cls.model_name),
            max_context_tokens=int(os.getenv("WRITER_MAX_CONTEXT_TOKENS", str(cls.max_context_tokens))),
            temperature=float(os.getenv("WRITER_TEMPERATURE", str(cls.temperature))),
            top_p=float(os.getenv("WRITER_TOP_P", str(cls.top_p))),
        )
