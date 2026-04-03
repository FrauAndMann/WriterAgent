"""Legacy Config wrapper — delegates to Settings."""

from __future__ import annotations

import warnings
from pathlib import Path
from dataclasses import dataclass, field

from writer_agent.settings import Settings


@dataclass
class Config:
    """Legacy config. Use Settings instead."""

    lm_studio_url: str = "http://localhost:1234/v1"
    model_name: str = ""
    max_context_tokens: int = 8192
    temperature: float = 0.85
    top_p: float = 0.95
    db_path: Path = field(default_factory=lambda: Path("data/writer_agent.db"))
    examples_dir: Path = field(default_factory=lambda: Path("data/examples"))
    output_dir: Path = field(default_factory=lambda: Path("data/novels"))

    @classmethod
    def from_env(cls) -> Config:
        warnings.warn("Config.from_env() is deprecated. Use Settings.load()", DeprecationWarning, stacklevel=2)
        return cls()

    @classmethod
    def from_settings(cls, settings: Settings) -> Config:
        return cls(
            lm_studio_url=settings.lmstudio.url,
            model_name=settings.lmstudio.model_name,
            max_context_tokens=settings.model_overrides.max_context_tokens or 8192,
            temperature=settings.generation.temperature,
            top_p=settings.generation.top_p,
            db_path=Path(settings.paths.db_path),
            examples_dir=Path(settings.paths.examples_dir),
            output_dir=Path(settings.paths.output_dir),
        )
