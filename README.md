<h1 align="center">WriterAgent</h1>

<p align="center">
  <strong>CLI-агент для написания дарк-романтических романов эпического масштаба</strong><br>
  <em>LM Studio + SQLite + Python</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-160%20passing-brightgreen" alt="160 Tests">
</p>

---

## О проекте

WriterAgent — CLI-инструмент для профессионального написания романов с интерактивным агентом, анализом стиля автора, глубокой памятью сюжета и каскадной системой настроек. Проектируется для novels до **600 000 слов**, с системой контекста, вписывающейся в окно контекста любой модели.

**Ключевые возможности:**
- Интерактивный **агент-писатель** — 13 инструментов для создания персонажей, глав, сюжетов, экспорта
- **Token-based routing** — мгновенный запуск read-only команд без вызова LLM
- **State machine** сессий — полный жизненный цикл: spawning → ready → running ⇄ waiting → paused → completed
- **Session persistence** — автосохранение каждого сообщения в SQLite, автовосстановление при крашах
- Автоматический анализ стиля автора из текстовых примеров
- Генерация с 8 типами сцен, иерархическими summary (3 уровня), plot state machine
- Каскадная конфигурация: env > local TOML > global TOML > defaults
- Проверка консистентности (мёртвые персонажи, разрешённые нити)
- Экспорт в Markdown, TXT, DOCX
- Работает полностью локально через LM Studio

---

## Архитектура

```
┌────────────────────────────────────────────────────────────────────┐
│                         CLI (Typer + Rich)                         │
│  new │ chat │ write │ show │ revise │ brainstorm │ config │ export │
└──┬───────┬─────────┬──────────┬──────────┬────────────────────────┘
   │       │         │          │          │
   ▼       ▼         ▼          ▼          ▼
┌──────┐ ┌───────┐ ┌──────────┐ ┌──────┐ ┌──────────┐
│Brain-│ │ Agent │ │ Chapter  │ │Con-  │ │ Exporter │
│storm │ │Engine │ │ Generator│ │text  │ │          │
│Engine│ │+13    │ │ +Scenes  │ │Check │ │          │
│      │ │ tools │ │ +Style   │ │      │ │          │
└──┬───┘ └──┬────┘ └───┬──────┘ └──────┘ └──────────┘
   │        │          │
   │  ┌─────┴──────┐   │
   │  │ Intent     │   │
   │  │ Router     │   │
   │  │ (fast path)│   │
   │  └────────────┘   │
   │                   │
   ▼                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                   LM Studio Client (OpenAI API)                  │
└──────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                     SQLite Database (11 tables)                  │
│  projects │ characters │ chapters │ plot_threads │ relationships │
│  world_elements │ style_profiles │ brainstorm_sessions           │
│  timeline_events │ plot_states │ agent_sessions                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Milestones

| Milestone | Описание | Статус |
|-----------|----------|--------|
| 1. Core Agent | Foundation, Style Analysis, Brainstorm, Generation, CLI, Consistency | ✅ |
| 2. Settings System | Cascading TOML config, CLI config, auto-detect | ✅ |
| 3. Generation Quality | Scene prompts, style injector, hierarchical summaries, plot state machine | ✅ |
| 4. Interactive Agent | AgentEngine с 13 tools, embedded JSON tool calling | ✅ |
| 5. Session & Routing | Session persistence, state machine, token-based routing | ✅ |

---

## Установка

### Требования

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) с загруженной моделью (рекомендуется Qwen 2.5 7B+ или аналог)

### Установка из исходников

```bash
git clone https://github.com/FrauAndMann/WriterAgent.git
cd WriterAgent
pip install -e ".[dev]"
```

### Проверка установки

```bash
writer-agent version
# WriterAgent v0.1.0
```

---

## Конфигурация

Каскадная система настроек: **env vars > local `writer.toml` > global `~/.writer-agent/config.toml` > defaults**.

### Переменные окружения

| Переменная | По умолчанию | Описание |
|-----------|--------------|----------|
| `WRITER_LM_STUDIO_URL` | `http://localhost:1234/v1` | URL LM Studio API |
| `WRITER_MODEL_NAME` | `""` (авто) | Имя модели (пустое = автоопределение) |
| `WRITER_MAX_CONTEXT_TOKENS` | `8192` | Максимальный размер контекста |
| `WRITER_TEMPERATURE` | `0.8` | Температура генерации |
| `WRITER_TOP_P` | `0.95` | Top-p сэмплирование |

### CLI конфигурация

```bash
writer-agent config set generation.temperature 0.9
writer-agent config set lmstudio.model_name "my-model"
writer-agent config get generation.temperature
```

### 5 групп настроек

| Группа | Настройки |
|--------|-----------|
| `lmstudio` | `url`, `model_name`, `api_key` |
| `generation` | `temperature`, `top_p`, `max_tokens`, `target_words` |
| `context` | `max_tokens`, `summary_levels` |
| `model_overrides` | per-model параметры |
| `paths` | `db_path`, `output_dir`, `examples_dir` |

---

## CLI — справка команд

### `writer-agent version`

Показать версию.

```bash
writer-agent version
```

### `writer-agent new <title>`

Создать новый проект. Инициализирует базу данных и создаёт проект со статусом `brainstorming`.

```bash
writer-agent new "Тёмная страсть"
```

### `writer-agent list`

Показать список всех проектов в виде таблицы (Rich).

```bash
writer-agent list
```

### `writer-agent status <title>`

Показать детальный статус проекта: количество глав, общее слово, список персонажей.

```bash
writer-agent status "Тёмная страсть"
```

### `writer-agent chat <title>`

Запустить **интерактивного агента** — LLM-оркестратор с 13 инструментами. Агент автоматически создаёт персонажей, пишет главы, показывает статус проекта, экспортирует роман — всё через диалог.

```bash
writer-agent chat "Тёмная страсть"
```

**Возможности агента (13 инструментов):**

| Инструмент | Описание |
|-----------|----------|
| `create_character` | Создать персонажа (имя, описание, характер, предыстория, арка) |
| `create_plot_thread` | Создать сюжетную нить (имя, описание, важность 1-10) |
| `create_world_element` | Создать элемент мира (локация, артефакт, фракция, магия) |
| `create_relationship` | Определить отношения между персонажами |
| `list_characters` | Показать всех персонажей проекта |
| `list_plot_threads` | Показать все сюжетные нити |
| `show_chapter` | Показать содержание главы или список глав |
| `show_project_status` | Обзор проекта: главы, слова, персонажи |
| `show_plot_state` | Текущее состояние plot state machine |
| `write_chapter` | Сгенерировать следующую главу |
| `revise_chapter` | Переработать существующую главу |
| `export_novel` | Экспорт в md/txt/docx |
| `save_note` | Сохранить заметку или идею |

**Встроенные команды агента:**

| Команда | Описание |
|---------|----------|
| `/help` | Справка по командам |
| `/session` | Статистика текущей сессии |
| `/quit` | Выйти из агента |

**Fast path:** запросы типа "покажи персонажей", "статус проекта" обрабатываются мгновенно через token-based routing, **без вызова LLM**.

**Session persistence:** все сообщения автосохраняются в SQLite. При перезапуске агент автоматически продолжает прерванную сессию.

**State machine:** сессия проходит через явные состояния с валидацией переходов — краш-безопасность и автовосстановление.

### `writer-agent brainstorm <title>`

Запустить интерактивный brainstorm-режим.

```bash
writer-agent brainstorm "Тёмная страсть"
```

**Команды внутри brainstorm:**

| Команда | Описание |
|---------|----------|
| `/help` | Справка |
| `/save char <name> <desc>` | Сохранить персонажа |
| `/save plot <name> <desc>` | Сохранить сюжетную нить |
| `/save world <name> <desc>` | Сохранить элемент мира |
| `/characters` | Показать персонажей |
| `/plots` | Показать сюжетные нити |
| `/done` | Завершить brainstorm |
| `/quit` | Выйти без финализации |

### `writer-agent write <title>`

Сгенерировать следующую главу. Автоматически собирает контекст, классифицирует сцену, инжектирует стиль, отслеживает plot state.

```bash
writer-agent write "Тёмная страсть"
writer-agent write "Тёмная страсть" -o "Глава с погоней" -w 3000 -t 0.85
```

**Параметры:**
- `--outline` / `-o` — план/набросок главы
- `--words` / `-w` — целевое количество слов (по умолчанию 3000)
- `--temp` / `-t` — температура (0.0-2.0, по умолчанию 0.85)

**Что происходит внутри:**
1. Определяется номер следующей главы
2. `ContextBuilder` собирает контекст по приоритетам с иерархическими summary
3. `SceneClassifier` определяет тип сцены (8 типов)
4. `StyleInjector` конвертирует профиль стиля в инструкции
5. `PromptAssembler` оркестрирует: scene + style + plot + context
6. LLM генерирует главу
7. Генерируются 3 уровня summary (arc 20w / compact 50w / detail 300w)
8. Обновляется plot state machine
9. Глава автосохраняется в файл

### `writer-agent show <title>`

Показать список глав или содержание конкретной главы.

```bash
writer-agent show "Тёмная страсть"          # список глав
writer-agent show "Тёмная страсть" -c 3     # показать главу 3
```

### `writer-agent revise <title>`

Переработать существующую главу.

```bash
writer-agent revise "Тёмная страсть" --chapter 3 --instructions "Добавь диалоги"
```

### `writer-agent analyze-style <directory>`

Проанализировать стиль письма из текстовых примеров (txt, md, docx, pdf).

```bash
writer-agent analyze-style ./my_examples/
```

**Метрики:** средняя длина предложения, доля диалогов, POV, частотные слова, типы предложений, характерные отрывки.

### `writer-agent export <title>`

Экспортировать роман в файл.

```bash
writer-agent export "Тёмная страсть"               # Markdown
writer-agent export "Тёмная страсть" --format txt   # Plain text
writer-agent export "Тёмная страсть" --format docx  # Word
```

### `writer-agent config`

Управление каскадной конфигурацией.

```bash
writer-agent config set generation.temperature 0.9
writer-agent config get lmstudio.url
```

---

## Тестирование

```
160 tests passing, 0 failures, 14 test files
```

| Файл | Тестов | Что тестирует |
|------|--------|---------------|
| `test_session_persistence.py` | 34 | State machine (SessionState), AgentSessionRepo, AgentEngine lifecycle |
| `test_generation_quality.py` | 32 | Scene prompts, style injector, hierarchical summaries, plot state, prompt assembler |
| `test_intent_router.py` | 30 | Token-based routing, токенизация, best_match, все 13 tools |
| `test_agent.py` | 21 | AgentEngine, tool registry, tool execution, chat loop, system prompt |
| `test_config.py` | 7 | Cascading TOML settings, env vars, auto-detect |
| `test_generator.py` | 6 | ChapterGenerator, LLM integration, summary generation, style loading |
| `test_llm_client.py` | 4 | OpenAI-compatible API, auto-detect model |
| `test_database.py` | 4 | SQLite schema, CRUD operations |
| `test_parser.py` | 4 | txt/md/docx/pdf parsing |
| `test_context.py` | 4 | ContextBuilder, token budgets, hierarchical summaries |
| `test_cli.py` | 4 | CLI commands (version, new, list, analyze-style) |
| `test_brainstorm.py` | 4 | BrainstormEngine, sessions, character save |
| `test_style.py` | 3 | StyleAnalyzer metrics |
| `test_consistency.py` | 3 | Dead character / resolved thread detection |

```bash
# Запуск всех тестов
pytest tests/ -v

# Запуск конкретного модуля
pytest tests/test_agent.py -v
```

---

## Структура проекта

```
WriterAgent/
├── pyproject.toml
├── README.md
├── src/writer_agent/
│   ├── __init__.py
│   ├── cli.py                          # CLI-команды (Typer + Rich)
│   ├── config.py                       # Базовая конфигурация
│   ├── settings.py                     # Cascading TOML settings
│   ├── db/
│   │   ├── database.py                 # SQLite + schema (11 tables) + migration
│   │   └── repositories.py             # CRUD-репозитории + AgentSessionRepo
│   ├── llm/
│   │   ├── client.py                   # LM Studio клиент (OpenAI SDK)
│   │   ├── prompts.py                  # Системные промпты (writer, brainstorm, agent)
│   │   └── scene_prompts.py            # 8 типов сцен + explicit
│   ├── analysis/
│   │   ├── parser.py                   # Парсеры txt/md/docx/pdf
│   │   ├── style.py                    # Анализатор стиля
│   │   └── style_injector.py           # Конвертация метрик в инструкции
│   ├── engine/
│   │   ├── agent.py                    # AgentEngine — интерактивный агент
│   │   ├── agent_tools.py              # 13 ToolDef + реализации
│   │   ├── brainstorm.py               # Brainstorm engine
│   │   ├── context.py                  # Контекст-билдер (приоритеты + бюджеты)
│   │   ├── generator.py                # Генератор глав + 3-level summaries
│   │   ├── consistency.py              # Проверка консистентности
│   │   ├── intent_router.py            # Token-based intent routing
│   │   ├── plot_state.py               # Plot state machine (JSON tracking)
│   │   ├── prompt_assembler.py         # Оркестрация: scene + style + plot + context
│   │   └── session_state.py            # SessionState enum + transition validation
│   └── export/
│       └── exporter.py                 # Экспорт md/txt/docx
└── tests/
    ├── test_agent.py                   # 21 test
    ├── test_brainstorm.py              # 4 tests
    ├── test_cli.py                     # 4 tests
    ├── test_config.py                  # 7 tests
    ├── test_consistency.py             # 3 tests
    ├── test_context.py                 # 4 tests
    ├── test_database.py                # 4 tests
    ├── test_generation_quality.py      # 32 tests
    ├── test_generator.py               # 6 tests
    ├── test_intent_router.py           # 30 tests
    ├── test_llm_client.py              # 4 tests
    ├── test_parser.py                  # 4 tests
    ├── test_session_persistence.py     # 34 tests
    └── test_style.py                   # 3 tests
```

---

## Схема базы данных

**11 таблиц:**

```
projects              — Романы (name, genre, tropes JSON, status, target_words)
  │
  ├── characters      — Персонажи (name, description, personality, arc, status)
  ├── chapters        — Главы (chapter_number, title, summary, full_text, word_count,
  │                              compact_summary, arc_summary)
  ├── plot_threads    — Сюжетные нити (name, status, importance, introduced/resolved)
  ├── relationships   — Отношения (char_a, char_b, type, evolution)
  ├── world_elements  — Элементы мира (category, name, description, metadata JSON)
  ├── timeline_events — Таймлайн (event_order, description, characters/threads JSON)
  └── plot_states     — Plot state machine (chapter_number, state JSON, version)

style_profiles        — Профили стиля (независимые от проектов)
brainstorm_sessions   — Brainstorm (messages JSON, notes)
agent_sessions        — Агент-сессии (messages JSON, status, input/output tokens)
```

---

## Workflow

```
1. writer-agent analyze-style ./examples/    → Анализ стиля автора
2. writer-agent new "Мой роман"              → Создание проекта
3. writer-agent brainstorm "Мой роман"       → Brainstorm (персонажи, сюжет, мир)
4. writer-agent chat "Мой роман"             → Интерактивный агент (создание + написание)
5. writer-agent write "Мой роман" -w 3000    → Генерация глав (повторять)
6. writer-agent revise "Мой роман" -c 3 ...  → Переработка глав
7. writer-agent export "Мой роман" -f docx   → Экспорт
```

---

## Git Commits

| # | Hash | Описание |
|---|------|----------|
| 1 | `6466bd7` | feat: project skeleton, config module, and database layer |
| 2 | `8669a82` | chore: remove cached files from tracking |
| 3 | `b9a1139` | feat: LM Studio client and document parsers |
| 4 | `c66a710` | feat: style analyzer for vocabulary, patterns, POV detection |
| 5 | `95d17ee` | feat: engine layer, full CLI, consistency checker, style integration |
| 6 | `7245c80` | docs: comprehensive README with API reference |
| 7 | `673c384` | docs: settings system design |
| 8 | `2d80bb3` | feat: cascading settings system with TOML, CLI config, auto-detect |
| 9 | `5087746` | docs: generation quality design |
| 10 | `eed4630` | feat: generation quality — scene prompts, style injector, summaries, plot state |
| 11 | `f07866f` | feat: uncensored prompt system — explicit writing instructions |
| 12 | `f6d8118` | feat: add --outline, --words, --temp options to write command |
| 13 | `bff5969` | feat: add show command + auto-save chapter to file after write |
| 14 | `1399c47` | feat: interactive agent mode — Milestone 4 |
| 15 | `1cf7c04` | feat: session persistence — auto-save/restore agent conversations to SQLite |
| 16 | `2bade80` | feat: state machine sessions — explicit lifecycle for agent conversations |
| 17 | `be26337` | feat: token-based intent routing — fast tool matching without LLM call |

---

## Лицензия

MIT
