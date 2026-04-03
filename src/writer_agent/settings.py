"""Cascading settings system: env > local TOML > global TOML > API > defaults."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any


# ── Nested setting groups ────────────────────────────────────────────────────


@dataclass
class LMStudioSettings:
    url: str = "http://localhost:1234/v1"
    model_name: str = ""  # empty = auto-detect


@dataclass
class GenerationSettings:
    temperature: float = 0.85
    top_p: float = 0.95
    top_k: int = 0  # 0 = disabled
    min_p: float = 0.0  # 0 = disabled
    repetition_penalty: float = 1.0  # 1.0 = no penalty
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_output_tokens: int = 0  # 0 = auto (from model)
    seed: int = -1  # -1 = random


@dataclass
class ContextSettings:
    budget_tokens: int = 6000
    history_chapters: int = 5
    summary_max_sentences: int = 5
    passage_tail_chars: int = 2000
    multi_chapter_threshold: int = 5


@dataclass
class ModelOverrideSettings:
    max_context_tokens: int = 0  # 0 = auto-detect
    max_output_tokens: int = 0  # 0 = auto-detect
    supports_reasoning: bool = False
    reasoning_budget_tokens: int = 0


@dataclass
class PathsSettings:
    db_path: str = "data/writer_agent.db"
    examples_dir: str = "data/examples"
    output_dir: str = "data/novels"


# ── Section name → dataclass mapping ────────────────────────────────────────

SECTION_MAP: dict[str, type] = {
    "lmstudio": LMStudioSettings,
    "generation": GenerationSettings,
    "context": ContextSettings,
    "model_overrides": ModelOverrideSettings,
    "paths": PathsSettings,
}

# Section → env-prefix mapping
SECTION_ENV: dict[str, str] = {
    "lmstudio": "WRITER_LM_STUDIO_",
    "generation": "WRITER_",
    "context": "WRITER_CONTEXT_",
    "model_overrides": "WRITER_",
    "paths": "WRITER_",
}

# Explicit env-var name overrides (field → exact env name)
ENV_NAME_MAP: dict[str, str] = {
    "url": "WRITER_LM_STUDIO_URL",
    "model_name": "WRITER_MODEL_NAME",
    "temperature": "WRITER_TEMPERATURE",
    "top_p": "WRITER_TOP_P",
    "top_k": "WRITER_TOP_K",
    "min_p": "WRITER_MIN_P",
    "repetition_penalty": "WRITER_REPETITION_PENALTY",
    "frequency_penalty": "WRITER_FREQUENCY_PENALTY",
    "presence_penalty": "WRITER_PRESENCE_PENALTY",
    "max_output_tokens": "WRITER_MAX_OUTPUT_TOKENS",
    "seed": "WRITER_SEED",
    "budget_tokens": "WRITER_CONTEXT_BUDGET",
    "history_chapters": "WRITER_HISTORY_CHAPTERS",
    "summary_max_sentences": "WRITER_SUMMARY_MAX_SENTENCES",
    "passage_tail_chars": "WRITER_PASSAGE_TAIL_CHARS",
    "multi_chapter_threshold": "WRITER_MULTI_CHAPTER_THRESHOLD",
    "max_context_tokens": "WRITER_MAX_CONTEXT_TOKENS",
    "supports_reasoning": "WRITER_SUPPORTS_REASONING",
    "reasoning_budget_tokens": "WRITER_REASONING_BUDGET",
    "db_path": "WRITER_DB_PATH",
    "examples_dir": "WRITER_EXAMPLES_DIR",
    "output_dir": "WRITER_OUTPUT_DIR",
}


# ── Source tracking ──────────────────────────────────────────────────────────

SOURCE_DEFAULT = "default"
SOURCE_GLOBAL = "global"
SOURCE_LOCAL = "local"
SOURCE_ENV = "env"
SOURCE_API = "api"


# ── Main Settings class ─────────────────────────────────────────────────────


@dataclass
class Settings:
    lmstudio: LMStudioSettings = field(default_factory=LMStudioSettings)
    generation: GenerationSettings = field(default_factory=GenerationSettings)
    context: ContextSettings = field(default_factory=ContextSettings)
    model_overrides: ModelOverrideSettings = field(default_factory=ModelOverrideSettings)
    paths: PathsSettings = field(default_factory=PathsSettings)

    # Source tracking: {(section, field_name): source_tag}
    _sources: dict[tuple[str, str], str] = field(default_factory=dict)

    # ── Loading ──────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, local_dir: Path | None = None) -> Settings:
        """Load settings from global + local TOML, then apply env overrides."""
        settings = cls()

        global_path = cls._global_path()
        if global_path.exists():
            global_data = _read_toml(global_path)
            _apply_toml(settings, global_data, SOURCE_GLOBAL)

        if local_dir is None:
            local_dir = Path.cwd()
        local_path = local_dir / "writer.toml"
        if local_path.exists():
            local_data = _read_toml(local_path)
            _apply_toml(settings, local_data, SOURCE_LOCAL)

        _apply_env(settings)

        return settings

    def resolve(self, api_capabilities: dict | None = None) -> Settings:
        """Full cascade: apply API-detected capabilities for unset fields."""
        if api_capabilities:
            self._apply_api(api_capabilities)
        return self

    # ── Access helpers ───────────────────────────────────────────────────────

    def get_value(self, dotted_key: str) -> tuple[Any, str]:
        """Get resolved value and its source. Returns (value, source)."""
        section, key = _parse_key(dotted_key)
        group = getattr(self, section)
        value = getattr(group, key)
        source = self._sources.get((section, key), SOURCE_DEFAULT)
        return value, source

    def set_value(self, dotted_key: str, value: Any, scope: str = "local") -> None:
        """Set a value in memory (call save() to persist)."""
        section, key = _parse_key(dotted_key)
        group = getattr(self, section)
        field_type = type(getattr(group, key))
        converted = _convert_value(value, field_type)
        setattr(group, key, converted)
        self._sources[(section, key)] = scope

    def save(self, scope: str = "local", local_dir: Path | None = None) -> None:
        """Persist current settings to TOML file."""
        import tomli_w

        if scope == "global":
            path = self._global_path()
        else:
            base = local_dir or Path.cwd()
            path = base / "writer.toml"

        path.parent.mkdir(parents=True, exist_ok=True)

        # Collect only scoped keys
        data: dict[str, dict] = {}
        for (section, key), source in self._sources.items():
            if source == scope or (scope == "local" and source == SOURCE_LOCAL):
                data.setdefault(section, {})
                data[section][key] = getattr(getattr(self, section), key)

        # Merge with existing file
        if path.exists():
            existing = _read_toml(path)
            for sec, vals in existing.items():
                if sec not in data:
                    data[sec] = vals
                else:
                    for k, v in vals.items():
                        if k not in data[sec]:
                            data[sec][k] = v

        path.write_text(tomli_w.dumps(data), encoding="utf-8")

    def unset_key(self, dotted_key: str, scope: str = "local") -> None:
        """Remove a key from TOML file (revert to lower priority)."""
        import tomli_w

        if scope == "global":
            path = self._global_path()
        else:
            base = Path.cwd()
            path = base / "writer.toml"

        if not path.exists():
            return

        section, key = _parse_key(dotted_key)
        data = _read_toml(path)
        if section in data and key in data[section]:
            del data[section][key]
            if not data[section]:
                del data[section]
            path.write_text(tomli_w.dumps(data), encoding="utf-8")

    def all_keys(self) -> list[tuple[str, str, Any, str]]:
        """Return all (section, key, value, source) tuples."""
        result = []
        for section_name in SECTION_MAP:
            group = getattr(self, section_name)
            for f in fields(group):
                value = getattr(group, f.name)
                source = self._sources.get((section_name, f.name), SOURCE_DEFAULT)
                result.append((section_name, f.name, value, source))
        return result

    # ── API capabilities ─────────────────────────────────────────────────────

    def _apply_api(self, caps: dict) -> None:
        """Apply auto-detected model capabilities for unset fields."""
        mo = self.model_overrides
        if mo.max_context_tokens == 0 and "max_context_tokens" in caps:
            mo.max_context_tokens = caps["max_context_tokens"]
            self._sources[("model_overrides", "max_context_tokens")] = SOURCE_API
        if mo.max_output_tokens == 0 and "max_output_tokens" in caps:
            mo.max_output_tokens = caps["max_output_tokens"]
            self._sources[("model_overrides", "max_output_tokens")] = SOURCE_API
        if not mo.supports_reasoning and caps.get("supports_reasoning"):
            mo.supports_reasoning = True
            self._sources[("model_overrides", "supports_reasoning")] = SOURCE_API

    # ── Paths ────────────────────────────────────────────────────────────────

    @staticmethod
    def _global_path() -> Path:
        return Path.home() / ".writer-agent" / "config.toml"

    @property
    def db_path(self) -> Path:
        return Path(self.paths.db_path)

    @property
    def output_dir_path(self) -> Path:
        return Path(self.paths.output_dir)

    @property
    def examples_dir_path(self) -> Path:
        return Path(self.paths.examples_dir)


# ── Helper functions ─────────────────────────────────────────────────────────


def _parse_key(dotted_key: str) -> tuple[str, str]:
    """Parse 'generation.temperature' into ('generation', 'temperature')."""
    parts = dotted_key.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid key format: '{dotted_key}'. Use 'section.field'.")
    section, key = parts
    if section not in SECTION_MAP:
        raise ValueError(f"Unknown section: '{section}'. Valid: {list(SECTION_MAP)}")
    group_cls = SECTION_MAP[section]
    if key not in {f.name for f in fields(group_cls)}:
        raise ValueError(f"Unknown field: '{key}' in section '{section}'")
    return section, key


def _read_toml(path: Path) -> dict:
    """Read TOML file, return dict. Empty dict if not exists."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _apply_toml(settings: Settings, data: dict, source: str) -> None:
    """Apply TOML data to settings, tracking sources."""
    for section, values in data.items():
        if section not in SECTION_MAP:
            continue
        group = getattr(settings, section)
        for key, value in values.items():
            if hasattr(group, key):
                field_type = type(getattr(group, key))
                setattr(group, key, _convert_value(value, field_type))
                settings._sources[(section, key)] = source


def _apply_env(settings: Settings) -> None:
    """Apply environment variable overrides."""
    for field_name, env_name in ENV_NAME_MAP.items():
        raw = os.getenv(env_name)
        if raw is None:
            continue
        # Find which section this field belongs to
        for section_name, section_cls in SECTION_MAP.items():
            if field_name in {f.name for f in fields(section_cls)}:
                group = getattr(settings, section_name)
                current = getattr(group, field_name)
                setattr(group, field_name, _convert_value(raw, type(current)))
                settings._sources[(section_name, field_name)] = SOURCE_ENV
                break


def _convert_value(raw: Any, target_type: type) -> Any:
    """Convert a value to the target type."""
    if isinstance(raw, target_type):
        return raw
    if target_type == bool:
        if isinstance(raw, str):
            return raw.lower() in ("true", "1", "yes")
        return bool(raw)
    if target_type == int:
        return int(float(raw))
    if target_type == float:
        return float(raw)
    if target_type == str:
        return str(raw)
    return raw


# ── Model auto-detection ─────────────────────────────────────────────────────

# Known model family → default context length
MODEL_CONTEXT_GUESSES: dict[str, int] = {
    "qwen2.5": 131072,
    "qwen2": 32768,
    "qwen": 32768,
    "llama-3.3": 131072,
    "llama-3.1": 131072,
    "llama-3": 8192,
    "mistral": 32768,
    "mixtral": 32768,
    "deepseek-r1": 131072,
    "deepseek-v3": 131072,
    "deepseek": 32768,
    "gemma2": 32768,
    "gemma": 8192,
    "phi-3": 32768,
    "phi-4": 16384,
    "command-r": 131072,
    "solar": 32768,
    "yi": 32768,
    "starcoder2": 16384,
    "codestral": 32768,
}

# Models known to support reasoning/thinking tokens
REASONING_MODELS: set[str] = {
    "deepseek-r1",
    "qwen-qwq",
    "qwq",
    "think",
}


def guess_context_from_model_name(model_id: str) -> dict:
    """Guess model capabilities from model ID string."""
    model_lower = model_id.lower()
    context_length = 8192  # safe default
    supports_reasoning = False

    # Check for specific model family matches (longest first)
    for family, ctx in sorted(MODEL_CONTEXT_GUESSES.items(), key=lambda x: -len(x[0])):
        if family in model_lower:
            context_length = ctx
            break

    # Check for reasoning support
    for pattern in REASONING_MODELS:
        if pattern in model_lower:
            supports_reasoning = True
            break

    # Size-based fallback: if no family matched, try parameter count
    if context_length == 8192:
        import re
        size_match = re.search(r"(\d+)b", model_lower)
        if size_match:
            size = int(size_match.group(1))
            if size >= 70:
                context_length = 131072
            elif size >= 30:
                context_length = 32768

    return {
        "model_name": model_id,
        "max_context_tokens": context_length,
        "max_output_tokens": min(context_length // 2, 8192),
        "supports_reasoning": supports_reasoning,
    }


def detect_model_capabilities(client) -> dict:
    """Auto-detect model from LM Studio API."""
    models = client.models.list()
    if not models.data:
        raise RuntimeError("No models loaded in LM Studio")

    model_id = models.data[0].id
    caps = guess_context_from_model_name(model_id)

    # Try to get more info from LM Studio
    try:
        # LM Studio may expose additional metadata
        import httpx
        resp = httpx.get(f"{client.base_url}/models", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for m in data.get("data", []):
                if m.get("id") == model_id:
                    meta = m.get("metadata", {})
                    if "context_length" in meta:
                        caps["max_context_tokens"] = int(meta["context_length"])
                    break
    except Exception:
        pass

    return caps
