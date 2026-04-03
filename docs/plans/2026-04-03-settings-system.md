# Settings System Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## Goal

Заменить плоский `Config` dataclass на каскадную систему настроек с TOML-файлами, CLI-управлением и автоопределением параметров модели из LM Studio.

## Design Decisions

1. **Хранение:** TOML-файлы (глобальный + локальный) + env-vars
2. **Приоритет:** env > local toml > global toml > LM Studio API > code defaults
3. **Группы:** Generation + Context/Memory (v1). Style + Brainstorm — позже.
4. **CLI:** `config set/get/list/reset` (flat) + `config` без аргументов (interactive) + `config show` (pretty print с источниками)
5. **Auto-detect:** LM Studio `/v1/models` для model name. `/v1/model/info` или guess по имени для context/max_tokens.

---

## TOML Structure

### Global: `~/.writer-agent/config.toml`

```toml
[lmstudio]
url = "http://localhost:1234/v1"
# model_name = ""          # auto-detect

[generation]
temperature = 0.85
top_p = 0.95
# top_k = 40
# min_p = 0.05
# repetition_penalty = 1.0
# frequency_penalty = 0.0
# presence_penalty = 0.0

[context]
budget_tokens = 6000       # tokens reserved for context blocks
history_chapters = 5       # how many recent chapter summaries to include
summary_max_sentences = 5  # LLM summary target length
passage_tail_chars = 2000  # tail of previous chapter to include

[model_overrides]
# Only override when LM Studio auto-detect is insufficient
# max_context_tokens = 32768
# max_output_tokens = 8000
# supports_reasoning = false
# reasoning_budget_tokens = 0

[paths]
# db_path = "data/writer_agent.db"
# examples_dir = "data/examples"
# output_dir = "data/novels"
```

### Local: `writer.toml` (project root)

```toml
# Project-specific overrides only
[generation]
temperature = 0.9
max_output_tokens = 6000

[context]
history_chapters = 3  # shorter memory for short stories
```

---

## Settings Groups (v1)

### `[lmstudio]` — LM Studio connection

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `url` | `str` | `"http://localhost:1234/v1"` | `WRITER_LM_STUDIO_URL` | API endpoint |
| `model_name` | `str` | `""` (auto) | `WRITER_MODEL_NAME` | Model ID. Empty = auto-detect from `/v1/models` |

### `[generation]` — Sampling & output parameters

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `temperature` | `float` | `0.85` | `WRITER_TEMPERATURE` | Randomness (0.0-2.0) |
| `top_p` | `float` | `0.95` | `WRITER_TOP_P` | Nucleus sampling |
| `top_k` | `int` | `0` (off) | `WRITER_TOP_K` | Top-K sampling. 0 = disabled |
| `min_p` | `float` | `0.0` (off) | `WRITER_MIN_P` | Min probability filter. 0 = disabled |
| `repetition_penalty` | `float` | `1.0` (off) | `WRITER_REPETITION_PENALTY` | 1.0 = no penalty |
| `frequency_penalty` | `float` | `0.0` | `WRITER_FREQUENCY_PENALTY` | -2.0 to 2.0 |
| `presence_penalty` | `float` | `0.0` | `WRITER_PRESENCE_PENALTY` | -2.0 to 2.0 |
| `max_output_tokens` | `int` | `0` (auto) | `WRITER_MAX_OUTPUT_TOKENS` | Max response tokens. 0 = use model limit |
| `seed` | `int` | `-1` (off) | `WRITER_SEED` | Reproducibility. -1 = random |

### `[context]` — Context building & memory

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `budget_tokens` | `int` | `6000` | `WRITER_CONTEXT_BUDGET` | Token budget for context blocks |
| `history_chapters` | `int` | `5` | `WRITER_HISTORY_CHAPTERS` | Recent chapter summaries to include |
| `summary_max_sentences` | `int` | `5` | `WRITER_SUMMARY_MAX_SENTENCES` | Target sentences in LLM summary |
| `passage_tail_chars` | `int` | `2000` | `WRITER_PASSAGE_TAIL_CHARS` | Characters from prev chapter tail |
| `multi_chapter_threshold` | `int` | `5` | `WRITER_MULTI_CHAPTER_THRESHOLD` | Switch to multi-chapter mode after N chapters |

### `[model_overrides]` — Manual model capability overrides

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `max_context_tokens` | `int` | `0` (auto) | `WRITER_MAX_CONTEXT_TOKENS` | Model context window. 0 = auto-detect |
| `max_output_tokens` | `int` | `0` (auto) | `WRITER_MAX_OUTPUT_TOKENS` | Model max output. 0 = auto-detect |
| `supports_reasoning` | `bool` | `false` | `WRITER_SUPPORTS_REASONING` | Does model support reasoning/thinking tokens? |
| `reasoning_budget_tokens` | `int` | `0` | `WRITER_REASONING_BUDGET` | Tokens reserved for reasoning. 0 = disabled |

### `[paths]` — File system paths

| Key | Type | Default | Env | Description |
|-----|------|---------|-----|-------------|
| `db_path` | `str` | `"data/writer_agent.db"` | `WRITER_DB_PATH` | Database path |
| `examples_dir` | `str` | `"data/examples"` | `WRITER_EXAMPLES_DIR` | Style examples directory |
| `output_dir` | `str` | `"data/novels"` | `WRITER_OUTPUT_DIR` | Export output directory |

---

## Resolution Priority

```
1. Environment variable  (WRITER_GENERATION_TEMPERATURE=0.9)
2. Local TOML            (./writer.toml)
3. Global TOML           (~/.writer-agent/config.toml)
4. LM Studio API         (auto-detected capabilities)
5. Code defaults          (hardcoded in Settings dataclass)
```

Example: `temperature` resolution:
1. `WRITER_TEMPERATURE` set? → use it
2. `./writer.toml` has `[generation] temperature`? → use it
3. `~/.writer-agent/config.toml` has `[generation] temperature`? → use it
4. N/A (not auto-detectable from API)
5. Default: `0.85`

Example: `max_context_tokens` resolution:
1. `WRITER_MAX_CONTEXT_TOKENS` set? → use it
2. `./writer.toml` has `[model_overrides] max_context_tokens`? → use it
3. `~/.writer-agent/config.toml` has `[model_overrides] max_context_tokens`? → use it
4. LM Studio API: try to detect from model metadata → use it
5. Default: `8192`

---

## Model Auto-Detection

On startup, when `model_name` is empty or `max_context_tokens`/`max_output_tokens` are 0:

```python
def detect_model_capabilities(client: OpenAI) -> dict:
    """Auto-detect model from LM Studio."""
    models = client.models.list()
    if not models.data:
        raise RuntimeError("No models loaded in LM Studio")

    model_id = models.data[0].id

    # Try to get detailed info from LM Studio
    # LM Studio may expose context_length in model metadata
    # If not available, guess from model name patterns
    context_length = guess_context_from_model_name(model_id)

    return {
        "model_name": model_id,
        "max_context_tokens": context_length,
        "max_output_tokens": min(context_length // 2, 8192),
    }

# Pattern-based guesses:
MODEL_CONTEXT_GUESSES = {
    "7b": 32768,
    "8b": 32768,
    "12b": 32768,
    "14b": 32768,
    "32b": 32768,
    "70b": 32768,
    "72b": 131072,
    "104b": 131072,
    "qwen": 32768,
    "qwen2": 32768,
    "qwen2.5": 131072,
    "mistral": 32768,
    "llama-3": 8192,
    "llama-3.1": 131072,
    "llama-3.3": 131072,
    "deepseek-r1": 131072,
    "deepseek-v3": 131072,
    "gemma": 8192,
    "gemma2": 32768,
    "phi-3": 32768,
    "command-r": 131072,
}
```

---

## CLI Commands

### `writer-agent config set <key> <value> [--global|--local]`

```bash
writer-agent config set generation.temperature 0.9
writer-agent config set generation.temperature 0.9 --global
writer-agent config set context.budget_tokens 8000
writer-agent config set model_overrides.max_context_tokens 32768
```

Default scope: `--local` if `writer.toml` exists, else `--global`.

### `writer-agent config get <key>`

```bash
writer-agent config get generation.temperature
# 0.9 (from: ./writer.toml)
```

Shows resolved value + source.

### `writer-agent config list [--global|--local]`

```bash
writer-agent config list
# Shows all settings with sources:
# generation.temperature    0.9    (local)
# generation.top_p          0.95   (global)
# context.budget_tokens     6000   (default)
```

### `writer-agent config show`

Rich-formatted display of all settings with color-coded sources:

```
┌─────────────────────────────────────────────────┐
│ WriterAgent Configuration                       │
├──────────────────────────────────────────────────┤
│ [lmstudio]                                       │
│   url              http://localhost:1234/v1  (df) │
│   model_name       qwen2.5-7b-instruct      (auto)│
│                                                   │
│ [generation]                                      │
│   temperature      0.9                       (loc) │
│   top_p            0.95                      (glb) │
│   top_k            —                         (df)  │
│   max_output_tokens 6000                      (loc) │
│                                                   │
│ [context]                                         │
│   budget_tokens    6000                      (df)  │
│   history_chapters 5                         (df)  │
│                                                   │
│ [model_overrides]                                 │
│   max_context_tokens 32768                   (api) │
│   supports_reasoning false                    (df)  │
└──────────────────────────────────────────────────┘

Sources: (df)efault (glb)al (loc)al (env) (api)auto-detect
```

### `writer-agent config reset <key>`

Removes the key from TOML file, reverting to next priority level.

### `writer-agent config` (no args = interactive)

Rich interactive menu:

```
? Select section:
  > Generation (temperature, sampling, output limits)
    Context & Memory (budget, history, summaries)
    Model (LM Studio URL, auto-detect, overrides)
    Paths (database, examples, output)

? generation.temperature [current: 0.9]: _
? generation.top_p [current: 0.95]: _
? generation.max_output_tokens [current: 6000]: _
```

---

## Implementation Plan

### Task 1: Settings Dataclass + TOML Loader

**Files:** `src/writer_agent/settings.py` (new)

- `Settings` dataclass with all groups as nested dataclasses
- `GenerationSettings`, `ContextSettings`, `ModelOverrideSettings`, `PathsSettings`, `LMStudioSettings`
- `Settings.load()` — reads global TOML, then local TOML, merges
- `Settings.from_env()` — applies env-var overrides
- `Settings.resolve()` — full cascade: env > local > global > defaults
- Each field has `source` tracking (for `config show`)

### Task 2: Model Auto-Detection

**Files:** `src/writer_agent/settings.py`

- `detect_model_capabilities(client)` — queries LM Studio API
- `guess_context_from_model_name(model_id)` — pattern matching
- Integration: called during `resolve()` when model_overrides fields are 0/empty

### Task 3: CLI Config Commands

**Files:** `src/writer_agent/cli.py` (modify)

- Add `config` command group with subcommands: `set`, `get`, `list`, `show`, `reset`
- Interactive mode when no subcommand
- Rich-formatted output for `show`

### Task 4: Migrate Config → Settings

**Files:** all files importing `Config`

- Replace `Config` with `Settings` everywhere
- `LLMClient` reads all generation params from Settings
- `ContextBuilder` reads context params from Settings
- `Database` reads paths from Settings
- Remove old `config.py`
- Update tests

### Task 5: Tests

**Files:** `tests/test_settings.py` (new)

- Test TOML loading (global + local merge)
- Test env-var override priority
- Test model auto-detection with mock
- Test `config set/get/list/reset` CLI commands
- Test resolution cascade

---

## Summary

| Aspect | Decision |
|--------|----------|
| Storage | TOML (global + local) + env-vars |
| Priority | env > local > global > API > defaults |
| Groups (v1) | lmstudio, generation, context, model_overrides, paths |
| CLI | set/get/list/show/reset + interactive |
| Auto-detect | LM Studio API + model name patterns |
| Backward compat | `Config.from_env()` wrapper during migration |
