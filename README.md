<h1 align="center">WriterAgent</h1>

<p align="center">
  <strong>CLI-агент для написания дарк-романтических романов эпического масштаба</strong><br>
  <em>LM Studio + SQLite + Python</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/tests-38%20passing-brightgreen" alt="38 Tests">
</p>

---

## О проекте

WriterAgent — CLI-инструмент для профессионального написания романов с интерактивным brainstorm, анализом стиля автора и глубокой памятью сюжета. Проектируется для novels до **600 000 слов**, с системой контекста, вписывающейся в окно контекста любой модели.

**Ключевые возможности:**
- Интерактивный brainstorm-диалог с LLM для создания мира, персонажей и сюжета
- Автоматический анализ стиля автора из текстовых примеров
- Генерация глав с контекстной памятью (персонажи, отношения, сюжетные нити, предыдущие главы)
- Проверка консистентности (мёртвые персонажи, разрешённые нити)
- Экспорт в Markdown, TXT, DOCX
- Работает полностью локально через LM Studio

---

## Архитектура

```
┌──────────────────────────────────────────────────────┐
│                    CLI (Typer + Rich)                 │
│  new │ brainstorm │ write │ revise │ analyze │ export │
└──────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Brain-   │ │ Chapter  │ │ Context  │ │ Exporter │
│ storm    │ │ Generator│ │ Builder  │ │          │
│ Engine   │ │          │ │          │ │          │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────┘
     │            │            │
     ▼            ▼            ▼
┌──────────────────────────────────────────────────────┐
│                LM Studio Client                      │
│           (OpenAI-compatible API)                    │
└──────────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│                SQLite Database                       │
│  projects │ characters │ chapters │ plot_threads     │
│  relationships │ world_elements │ style_profiles     │
│  brainstorm_sessions │ timeline_events               │
└──────────────────────────────────────────────────────┘
```

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

Все параметры настраиваются через переменные окружения:

| Переменная | По умолчанию | Описание |
|-----------|--------------|----------|
| `WRITER_LM_STUDIO_URL` | `http://localhost:1234/v1` | URL LM Studio API |
| `WRITER_MODEL_NAME` | `""` (авто) | Имя модели (пустое = автоопределение) |
| `WRITER_MAX_CONTEXT_TOKENS` | `8192` | Максимальный размер контекста |
| `WRITER_TEMPERATURE` | `0.8` | Температура генерации |
| `WRITER_TOP_P` | `0.95` | Top-p сэмплирование |

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

**Параметры:**
- `title` (обязательный) — название проекта/романа

### `writer-agent list`

Показать список всех проектов в виде таблицы (Rich). Выводит ID, название, жанр, статус, дату создания.

```bash
writer-agent list
```

### `writer-agent status <title>`

Показать детальный статус проекта: количество глав, общее слово, список персонажей.

```bash
writer-agent status "Тёмная страсть"
```

**Параметры:**
- `title` (обязательный) — название проекта

### `writer-agent brainstorm <title>`

Запустить интерактивный brainstorm-режим. Многоходовый диалог с LLM для создания концепции романа, персонажей и сюжета.

```bash
writer-agent brainstorm "Тёмная страсть"
```

**Параметры:**
- `title` (обязательный) — название проекта (существующего или нового)

**Команды внутри brainstorm:**

| Команда | Описание |
|---------|----------|
| `/help` | Показать справку по командам |
| `/save char <name> <desc>` | Сохранить персонажа в базу |
| `/save plot <name> <desc>` | Сохранить сюжетную нить |
| `/save world <name> <desc>` | Сохранить элемент мира |
| `/characters` | Показать сохранённых персонажей |
| `/plots` | Показать сохранённые сюжетные нити |
| `/done` | Завершить brainstorm, перевести проект в статус `outlined` |
| `/quit` | Выйти из brainstorm без финализации |

**Пример сессии:**
```
You> Хочу историю о вампире-мафиози, который влюбляется в следователя

Agent> [Rich Markdown ответ с идеями]

You> /save char Данте Мафия вампиров, 300 лет, холодный и расчётливый
Saved character: Данте

You> /save char Елена Следователь, охотится на мафию, не знает о вампирах
Saved character: Елена

You> /done
Project finalized and ready for writing!
```

### `writer-agent write <title>`

Сгенерировать следующую главу. Автоматически определяет номер следующей главы, собирает контекст из памяти, загружает профиль стиля и вызывает LLM.

```bash
writer-agent write "Тёмная страсть"
```

**Параметры:**
- `title` (обязательный) — название проекта

**Что происходит внутри:**
1. Определяется номер следующей главы (последняя + 1)
2. `ContextBuilder` собирает контекст по приоритетам (см. ниже)
3. Загружается профиль стиля из БД (если есть)
4. LLM генерирует главу
5. LLM создаёт сжатое summary главы
6. Глава сохраняется в БД

### `writer-agent revise <title> <chapter> [instructions]`

Переработать существующую главу по указаниям автора.

```bash
writer-agent revise "Тёмная страсть" 3 "Добавь больше диалогов, усиль напряжение"
```

**Параметры:**
- `title` (обязательный) — название проекта
- `chapter` (обязательный) — номер главы
- `instructions` (опциональный) — инструкции для переработки (если не указаны, будет запрошен интерактивно)

### `writer-agent analyze-style <directory>`

Проанализировать стиль письма из текстовых примеров. Поддерживает txt, md, docx, pdf. Создаёт профиль стиля в БД, который автоматически используется при генерации.

```bash
writer-agent analyze-style ./my_examples/
```

**Параметры:**
- `directory` (обязательный) — путь к директории с текстовыми примерами

**Метрики анализа:**
- Средняя длина предложения
- Доля диалогов в тексте
- POV (первое/третье лицо)
- Частотные слова (топ-30, без стоп-слов)
- Характерные отрывки
- Типы предложений (повествовательные, вопросительные, восклицательные)

### `writer-agent export <title> [fmt]`

Экспортировать роман в файл. Форматы: `md` (по умолчанию), `txt`, `docx`.

```bash
writer-agent export "Тёмная страсть"          # Markdown
writer-agent export "Тёмная страсть" --fmt txt # Plain text
writer-agent export "Тёмная страсть" --fmt docx # Word
```

**Параметры:**
- `title` (обязательный) — название проекта
- `fmt` (опциональный, по умолчанию `md`) — формат экспорта: `md`, `txt`, `docx`

---

## API — подробная документация модулей

### `writer_agent.config` — Конфигурация

```python
from writer_agent.config import Config
```

#### `Config` (dataclass)

Основной конфигурационный объект. Создаётся из дефолтных значений или переменных окружения.

| Поле | Тип | По умолчанию | Описание |
|------|-----|-------------|----------|
| `lm_studio_url` | `str` | `"http://localhost:1234/v1"` | URL LM Studio API |
| `model_name` | `str` | `""` | Имя модели (пустое = автоопределение) |
| `max_context_tokens` | `int` | `8192` | Максимальное количество токенов в контексте |
| `temperature` | `float` | `0.8` | Температура генерации (0.1-2.0) |
| `top_p` | `float` | `0.95` | Top-p nucleus sampling |
| `db_path` | `Path` | `"data/writer_agent.db"` | Путь к базе данных |
| `examples_dir` | `Path` | `"data/examples"` | Директория с примерами текстов |
| `output_dir` | `Path` | `"data/novels"` | Директория для экспорта |

#### `Config.from_env() -> Config`

Создаёт конфигурацию из переменных окружения с fallback на дефолтные значения.

```python
config = Config.from_env()
```

---

### `writer_agent.db.database` — База данных

```python
from writer_agent.db.database import Database
```

#### `Database`

SQLite-оболочка с инициализацией схемы из 9 таблиц.

##### `Database(path: Path)`

Создаёт подключение к базе. Директория создаётся автоматически.

```python
db = Database(Path("data/writer_agent.db"))
```

##### `Database.initialize()`

Создаёт все таблицы, если они не существуют. Вызывать после конструктора.

```python
db.initialize()
```

##### `Database.execute(sql: str, params=()) -> cursor`

Выполняет SQL-запрос. Возвращает cursor. Все строки возвращаются как `sqlite3.Row`.

```python
rows = db.execute("SELECT * FROM projects WHERE id = ?", (1,)).fetchall()
```

##### `Database.connection -> sqlite3.Connection`

Доступ к raw-подключению для транзакций.

---

### `writer_agent.db.repositories` — CRUD-репозитории

9 репозиториев для работы с данными. Все методы возвращают `dict` (через `sqlite3.Row`).

#### `ProjectRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(name: str, genre: str = "", description: str = "", tropes: list = None, target_words: int = 600000)` | `int` | Создать проект |
| `get` | `get(project_id: int)` | `dict` | Получить по ID |
| `get_by_name` | `get_by_name(name: str)` | `dict` | Найти по названию |
| `list` | `list()` | `list[dict]` | Все проекты (по дате, DESC) |
| `update_status` | `update_status(project_id: int, status: str)` | `None` | Обновить статус |

**Статусы проекта:** `brainstorming` → `outlined` → `writing` → `complete`

#### `CharacterRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, name: str, description: str = "", personality: str = "", full_name: str = "", background: str = "", arc: str = "", metadata: dict = None)` | `int` | Создать персонажа |
| `get` | `get(char_id: int)` | `dict` | Получить по ID |
| `list_by_project` | `list_by_project(project_id: int)` | `list[dict]` | Персонажи проекта |
| `update` | `update(char_id: int, **kwargs)` | `None` | Обновить поля (name, status, description и т.д.) |
| `get_relationships` | `get_relationships(char_id: int)` | `list[dict]` | Отношения персонажа |

**Статусы персонажа:** `active`, `dead`, `absent`

#### `ChapterRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, chapter_number: int, title: str = "", summary: str = "", full_text: str = "")` | `int` | Создать главу. Автоматически считает `word_count` |
| `get` | `get(chapter_id: int)` | `dict` | Получить по ID |
| `get_by_number` | `get_by_number(project_id: int, chapter_number: int)` | `dict` | Получить по номеру главы |
| `list_by_project` | `list_by_project(project_id: int)` | `list[dict]` | Все главы проекта (по номеру) |
| `get_latest` | `get_latest(project_id: int)` | `dict` | Последняя глава |
| `update_text` | `update_text(chapter_id: int, full_text: str)` | `None` | Обновить текст и пересчитать `word_count` |

#### `PlotThreadRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, name: str, description: str = "", status: str = "active", importance: int = 5)` | `int` | Создать сюжетную нить |
| `get` | `get(thread_id: int)` | `dict` | Получить по ID |
| `list_by_project` | `list_by_project(project_id: int, status: str = None)` | `list[dict]` | Нити проекта. Фильтр по `status` опционален. Сортировка по `importance` DESC |
| `resolve` | `resolve(thread_id: int, resolved_chapter: int = None)` | `None` | Пометить как разрешённую |

#### `RelationshipRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, char_a: str, char_b: str, type: str = "", description: str = "", evolution: str = "")` | `int` | Создать отношение между персонажами |
| `get` | `get(rel_id: int)` | `dict` | Получить по ID |
| `list_by_project` | `list_by_project(project_id: int)` | `list[dict]` | Отношения проекта |

#### `WorldElementRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, name: str, category: str = "", description: str = "", metadata: dict = None)` | `int` | Создать элемент мира |
| `get` | `get(elem_id: int)` | `dict` | Получить по ID |
| `list_by_project` | `list_by_project(project_id: int)` | `list[dict]` | Элементы мира проекта (по category, name) |

#### `StyleProfileRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(name: str, source_files: list = None, analysis: dict = None, sample_passages: list = None)` | `int` | Сохранить профиль стиля |
| `get` | `get(profile_id: int)` | `dict` | Получить по ID |
| `list` | `list()` | `list[dict]` | Все профили (по дате, DESC) |

#### `BrainstormSessionRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, notes: str = "")` | `int` | Создать сессию brainstorm |
| `get` | `get(session_id: int)` | `dict` | Получить сессию |
| `add_message` | `add_message(session_id: int, role: str, content: str)` | `None` | Добавить сообщение (role: "user" / "assistant") |
| `get_messages` | `get_messages(session_id: int)` | `list[dict]` | Все сообщения сессии |

#### `TimelineEventRepo`

| Метод | Сигнатура | Возвращает | Описание |
|-------|-----------|------------|----------|
| `create` | `create(project_id: int, description: str = "", chapter_id: int = None, event_order: int = 0, characters_involved: list = None, plot_threads: list = None)` | `int` | Создать событие таймлайна |
| `get_by_chapter` | `get_by_chapter(chapter_id: int)` | `list[dict]` | События главы |
| `get_by_project` | `get_by_project(project_id: int)` | `list[dict]` | Все события проекта |

---

### `writer_agent.llm.client` — LLM-клиент

```python
from writer_agent.llm.client import LLMClient
from writer_agent.config import Config
```

#### `LLMClient`

OpenAI-совместимый клиент для LM Studio.

##### `LLMClient(config: Config)`

Создаёт клиент. Подключение к LM Studio через OpenAI SDK.

```python
client = LLMClient(Config())
```

##### `get_available_model() -> str`

Возвращает имя модели. Если `config.model_name` пустое, автоматически определяет первую доступную модель через `/v1/models`.

```python
model = client.get_available_model()  # "qwen2.5-7b-instruct-q4_k_m"
```

##### `generate(system_prompt: str, user_prompt: str, context_blocks: list[str] | None = None, max_tokens: int = 4000, temperature: float | None = None) -> str`

Генерация текста. `context_blocks` инъектируются как pseudo-turn между system и user сообщениями (system → [context] → assistant: "Context received" → user). Это даёт модели «память» без раздувания system prompt.

```python
text = client.generate(
    system_prompt="Ты писатель.",
    user_prompt="Напиши первую главу.",
    context_blocks=["Персонаж: Елена — следователь", "Предыдущая глава: Они встретились."],
    max_tokens=4000,
)
```

##### `chat(messages: list[dict], max_tokens: int = 4000) -> str`

Прямой multi-turn чат для brainstorm-режима. Принимает полный список сообщений.

```python
response = client.chat(
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "Предложи идею"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "Развей идею"},
    ],
    max_tokens=2000,
)
```

##### `count_tokens(text: str) -> int`

Грубая оценка токенов: ~2 символа на токен для кириллицы, ~4 для латиницы.

```python
tokens = client.count_tokens("Длинный текст на русском.")  # ~11
```

---

### `writer_agent.llm.prompts` — Системные промпты

```python
from writer_agent.llm.prompts import SYSTEM_WRITER, SYSTEM_BRAINSTORM
```

| Константа | Описание |
|-----------|----------|
| `SYSTEM_WRITER` | Промпт для генерации глав. Профессиональный дарк-романтик novelist, Russian |
| `SYSTEM_BRAINSTORM` | Промпт для brainstorm. Креативный консультант, tropes, subversion |

---

### `writer_agent.analysis.parser` — Парсеры документов

```python
from writer_agent.analysis.parser import parse_document, parse_directory
```

#### `parse_document(path: Path) -> str`

Парсит документ в plain text. Поддерживаемые форматы: `.txt`, `.md`, `.docx`, `.pdf`. Выбрасывает `ValueError` для неподдерживаемых форматов.

```python
text = parse_document(Path("draft.docx"))
```

#### `parse_directory(dir_path: Path) -> dict[str, str]`

Парсит все поддерживаемые документы в директории. Возвращает `{filename: text}`. Пропускает файлы с ошибками парсинга.

```python
docs = parse_directory(Path("./examples/"))
# {"chapter1.txt": "...", "chapter2.docx": "..."}
```

---

### `writer_agent.analysis.style` — Анализатор стиля

```python
from writer_agent.analysis.style import StyleAnalyzer
```

#### `StyleAnalyzer`

Извлекает 8 стилистических метрик из текста.

##### `analyze(text: str) -> dict`

Полный анализ текста. Возвращает словарь:

| Ключ | Тип | Описание |
|------|-----|----------|
| `avg_sentence_length` | `float` | Средняя длина предложения в словах |
| `total_words` | `int` | Общее количество слов |
| `frequent_words` | `list[str]` | Топ-30 частых слов (без русских стоп-слов, >2 символов) |
| `sentence_patterns` | `dict` | `{questions_ratio, exclamations_ratio, statements_ratio}` |
| `paragraph_lengths` | `list[int]` | Длины параграфов в словах |
| `dialogue_ratio` | `float` | Доля текста в диалогах (em-dash, guillemets, кавычки) |
| `sample_passages` | `list[str]` | 5 самых длинных параграфов |
| `pov_style` | `str` | `"first_person"` или `"third_person"` |

```python
analyzer = StyleAnalyzer()
result = analyzer.analyze("Она вошла. Тёмные волосы. Он смотрел.")
# result["total_words"] == 6
# result["pov_style"] == "third_person"
```

---

### `writer_agent.engine.brainstorm` — Brainstorm Engine

```python
from writer_agent.engine.brainstorm import BrainstormEngine
```

#### `BrainstormEngine`

Управляет brainstorm-сессиями: создаёт проекты, ведёт диалог, сохраняет идеи.

##### `BrainstormEngine(db: Database, llm_client)`

##### `start_session(title: str) -> int`

Создаёт проект и brainstorm-сессию. Возвращает `session_id`.

##### `chat(session_id: int, user_message: str) -> str`

Отправляет сообщение и получает ответ LLM. Сохраняет ход диалога в БД. Системный промпт — `SYSTEM_BRAINSTORM`.

##### `get_history(session_id: int) -> list[dict]`

Возвращает полную историю сообщений сессии: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`.

##### `save_character(session_id: int, **kwargs) -> int`

Сохраняет персонажа из brainstorm. kwargs: `name`, `description`, `personality`, `full_name`, `background`, `arc`.

##### `save_plot_thread(session_id: int, **kwargs) -> int`

Сохраняет сюжетную нить. kwargs: `name`, `description`, `status`, `importance`.

##### `save_world_element(session_id: int, **kwargs) -> int`

Сохраняет элемент мира. kwargs: `name`, `category`, `description`, `metadata`.

##### `finalize_session(session_id: int) -> int`

Переводит проект в статус `outlined`. Возвращает `project_id`.

---

### `writer_agent.engine.context` — Контекст-билдер

```python
from writer_agent.engine.context import ContextBuilder
```

#### `ContextBuilder`

Собирает релевантный контекст из БД для генерации главы. Приоритетная система с токен-бюджетом.

##### `ContextBuilder(db: Database, max_tokens: int = 6000)`

##### `build(project_id: int, current_chapter: int) -> dict`

Собирает блоки контекста по приоритетам и обрезает по бюджету.

**Возвращает:** `{"blocks": list[str], "total_tokens": int}`

**Приоритеты контекста:**

| Приоритет | Блок | Описание |
|-----------|------|----------|
| 1 | `overview` | Название, жанр, описание проекта |
| 2 | `characters` | Все персонажи проекта |
| 3 | `chapter_history` / `prev_summary` | При `current_chapter > 5`: сжатые summary последних 5 глав. Иначе: summary предыдущей главы |
| 4 | `plot_threads` | Активные сюжетные нити |
| 5 | `world` | Элементы мира (до 10) |
| 6 | `prev_passage` | Последние 1500 символов предыдущей главы |
| 7 | `relationships` | Отношения между персонажами |

Элементы с **низшим приоритетом отбрасываются первыми** при превышении бюджета.

##### `_estimate_tokens(text: str) -> int`

Оценка токенов: кириллица ~2 символа/токен, латиница ~4 символа/токен.

---

### `writer_agent.engine.generator` — Генератор глав

```python
from writer_agent.engine.generator import ChapterGenerator
```

#### `ChapterGenerator`

Оркестрирует генерацию глав: контекст + стиль + LLM + автосохранение.

##### `ChapterGenerator(db: Database, llm_client, context_builder: ContextBuilder)`

##### `generate_chapter(project_id: int, chapter_number: int, outline: str = "", target_words: int = 3000, style_instructions: str = "", temperature: float = 0.85) -> dict`

Генерирует главу. Pipeline:

1. Собирает контекст через `ContextBuilder`
2. Загружает профиль стиля из БД (если `style_instructions` не указан)
3. Формирует system prompt (SYSTEM_WRITER + стиль)
4. Формирует user prompt (задание + план + объём)
5. Вызывает LLM с context_blocks
6. Генерирует summary через LLM (fallback на обрезку)
7. Сохраняет главу в БД

**Возвращает:**
```python
{
    "chapter_id": int,
    "full_text": str,
    "word_count": int,
}
```

##### `revise_chapter(chapter_id: int, instructions: str) -> dict`

Перерабатывает существующую главу. Текущий текст главы + инструкции отправляются LLM. Обновляет текст в БД.

**Возвращает:** `{"chapter_id": int, "full_text": str}`

##### `_generate_summary(text: str) -> str`

Генерирует summary с fallback: сначала пытается через LLM (2-3 предложения), при ошибке — обрезка первых 300 символов.

##### `_load_style_prompt() -> str`

Загружает последний профиль стиля из БД и конвертирует в текстовую инструкцию:

```
[Стиль автора]
- Средняя длина предложения: 14 слов
- POV: third_person
- Доля диалогов: 35%
- Частые слова: тьма, взгляд, кожа, шёпот, холод
```

---

### `writer_agent.engine.consistency` — Проверка консистентности

```python
from writer_agent.engine.consistency import ConsistencyChecker
```

#### `ConsistencyChecker`

Проверяет план главы на соответствие текущему состоянию проекта.

##### `ConsistencyChecker(db: Database)`

##### `check(project_id: int, outline: str) -> list[str]`

Возвращает список предупреждений (пустой = всё в порядке).

**Проверки:**
- Мёртвые персонажи (`status == "dead"`) не должны появляться как активные
- Разрешённые сюжетные нити (`status == "resolved"`) не должны упоминаться как активные

```python
checker = ConsistencyChecker(db)
warnings = checker.check(project_id=1, outline="Viktor enters the room.")
# ["Персонаж 'Viktor' мёртв, но упомянут в плане как активный."]
```

---

### `writer_agent.export.exporter` — Экспорт

```python
from writer_agent.export.exporter import Exporter
```

#### `Exporter`

##### `Exporter(chapter_repo: ChapterRepo)`

##### `to_markdown(project_id: int, output_path: Path, title: str = "")`

Экспорт в Markdown. Главы как `## Заголовок`, разделитель `---`.

##### `to_txt(project_id: int, output_path: Path, title: str = "")`

Экспорт в plain text. Заголовок с `=`, разделитель `-`.

##### `to_docx(project_id: int, output_path: Path, title: str = "")`

Экспорт в Word (.docx). Заголовок уровня 0, главы — уровень 1, параграфы через `\n\n`.

---

## Схема базы данных

**9 таблиц:**

```
projects              — Романы (name, genre, tropes JSON, status, target_words)
  │
  ├── characters      — Персонажи (name, description, personality, arc, status)
  ├── chapters        — Главы (chapter_number, title, summary, full_text, word_count)
  ├── plot_threads    — Сюжетные нити (name, status, importance, introduced/resolved)
  ├── relationships   — Отношения (char_a, char_b, type, evolution)
  ├── world_elements  — Элементы мира (category, name, description, metadata JSON)
  ├── brainstorm_sessions — Brainstorm (messages JSON, notes)
  └── timeline_events — Таймлайн (event_order, description, characters/threads JSON)

style_profiles        — Профили стиля (независимые от проектов)
```

---

## Тестирование

```bash
# Запуск всех тестов
pytest tests/ -v

# Запуск конкретного модуля
pytest tests/test_generator.py -v

# С количеством тестов: 38
```

---

## Структура проекта

```
WriterAgent/
├── pyproject.toml
├── README.md
├── src/writer_agent/
│   ├── __init__.py
│   ├── cli.py                      # CLI-команды (Typer)
│   ├── config.py                   # Конфигурация
│   ├── db/
│   │   ├── database.py             # SQLite-оболочка + схема
│   │   └── repositories.py         # 9 CRUD-репозиториев
│   ├── llm/
│   │   ├── client.py               # LM Studio клиент
│   │   └── prompts.py              # Системные промпты
│   ├── analysis/
│   │   ├── parser.py               # Парсеры txt/md/docx/pdf
│   │   └── style.py                # Анализатор стиля
│   ├── engine/
│   │   ├── brainstorm.py           # Brainstorm engine
│   │   ├── context.py              # Контекст-билдер
│   │   ├── generator.py            # Генератор глав
│   │   └── consistency.py          # Проверка консистентности
│   └── export/
│       └── exporter.py             # Экспорт md/txt/docx
└── tests/
    ├── test_config.py
    ├── test_database.py
    ├── test_llm_client.py
    ├── test_parser.py
    ├── test_style.py
    ├── test_brainstorm.py
    ├── test_context.py
    ├── test_generator.py
    ├── test_consistency.py
    └── test_cli.py
```

---

## Workflow

```
1. writer-agent analyze-style ./examples/    → Анализ стиля автора
2. writer-agent new "Мой роман"              → Создание проекта
3. writer-agent brainstorm "Мой роман"       → Brainstorm (персонажи, сюжет, мир)
4. writer-agent write "Мой роман"            → Генерация глав (повторять)
5. writer-agent revise "Мой роман" 3 "..."   → Переработка глав
6. writer-agent export "Мой роман" --fmt docx → Экспорт
```

---

## Лицензия

MIT
