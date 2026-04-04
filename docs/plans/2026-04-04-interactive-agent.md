# Milestone 4: Interactive Agent Mode

## Goal

Созд an interactive agent mode similar to Claude Code CLI. User launches `writer-agent chat "Title"`, types natural language commands, and the agent orchestrates multi-step workflows using existing tools.

## Architecture

```
writer-agent chat "Моя Тёмная Кровь"
         │
    ┌────▼─────┐
    │  CLI REPL  │  ← Rich console, input/output loop
    └────┬──────┘
         │
    ┌────▼──────────────┐
    │  AgentEngine       │  ← conversation history, tool parsing
    │  - chat(msg)       │
    │  - parse_response()│
    │  - execute_tool()  │
    └────┬──────────────┘
         │
    ┌────▼──────────────┐
    │  Tool Registry     │  ← 12 tools wrapping existing functionality
    │  - create_character │
    │  - write_chapter    │
    │  - show_chapter     │
    │  - ...              │
    └─────────────────────┘
```

## Tool Calling Protocol

Since LM Studio / local models may not support native function calling, use embedded JSON:

LLM response:
```
Сейчас создам концепцию...

```tool
{"name": "create_character", "args": {"name": "Елена", "description": "..."}}
```

```result
{"success": true, "id": 5}
```

Отлично, персонаж создан!
```

## Files

### NEW: `src/writer_agent/engine/agent.py`
- `AgentEngine` class with:
  - `__init__(db, llm_client, project_id)`
  - `chat(user_message) -> str` — main method: send to LLM, parse tools, execute, return text
  - `_parse_tool_calls(response) -> list[dict]` — extract ```tool``` blocks
  - `_execute_tool(name, args) -> dict` — dispatch to tool function
  - `_format_result(result) -> str` — format tool result for LLM
  - Conversation history management (list of messages)

### NEW: `src/writer_agent/engine/agent_tools.py`
- Tool registry dict with 12 tools:
  - `create_character(name, description, personality, background)`
  - `create_plot_thread(name, description, importance)`
  - `create_world_element(name, category, description)`
  - `list_characters()`
  - `list_plot_threads()`
  - `write_chapter(outline, target_words, temperature)`
  - `revise_chapter(chapter_number, instructions)`
  - `show_chapter(chapter_number)`
  - `show_project_status()`
  - `show_plot_state()`
  - `export_novel(format)`
  - `save_note(content)` — freeform notes
- Each tool: `{"name", "description", "params", "fn"}`

### MODIFY: `src/writer_agent/llm/prompts.py`
- Add `SYSTEM_AGENT` — agent system prompt with:
  - Role: proactive creative writing assistant
  - Tool list with descriptions and params
  - JSON format specification for tool calls
  - Behavioral guidelines (think step by step, report progress)

### MODIFY: `src/writer_agent/cli.py`
- Add `chat` command:
  - Takes `title` argument
  - Creates DB, LLM client, AgentEngine
  - REPL loop with Rich formatting
  - Slash commands: `/help`, `/status`, `/undo`, `/quit`

## Implementation Tasks

1. Create `agent_tools.py` — tool registry with all 12 tools
2. Create `agent.py` — AgentEngine with tool parsing loop
3. Add `SYSTEM_AGENT` to prompts.py
4. Add `chat` command to CLI
5. Tests for agent tools + engine
6. Verification — full test suite

## Key Design Decisions

- **No native function calling** — use embedded JSON in LLM responses (works with any model)
- **Reuse existing repos** — tools just call ChapterRepo, ProjectRepo, etc.
- **Conversation in memory** — no DB storage for agent sessions (simpler, like Claude Code)
- **Max 20 messages** in history to avoid context overflow
- **Tool results fed back as assistant messages** — LLM sees its own tool calls and results
