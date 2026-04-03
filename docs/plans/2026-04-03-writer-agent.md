# WriterAgent — Dark Romance Novel CLI Agent

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** CLI-агент для профессионального написания развратных дарк-романтических романов эпического масштаба (до 600K слов) с интерактивным brainstorm, анализом стиля автора и глубокой памятью сюжета.

**Architecture:** Python CLI на Typer + Rich. LM Studio как LLM-провайдер через OpenAI-совместимый API (localhost:1234). SQLite для хранения всего состояния: персонажи, отношения, сюжетные нити, мировой лор, главы с саммари. Система контекста собирает релевантную память перед каждой генерацией, чтобы вписываться в окно контекста любой модели. Brainstorm — многоходовый диалог с агентом.

**Tech Stack:** Python 3.11+, Typer, Rich, OpenAI Python client, SQLite, python-docx, pdfplumber, Jinja2, pytest

---

## Phase 1: Foundation

### Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/writer_agent/__init__.py`
- Create: `src/writer_agent/cli.py`
- Create: `tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "writer-agent"
version = "0.1.0"
description = "CLI agent for writing dark romance novels with LM Studio"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "openai>=1.30",
    "python-docx>=1.1",
    "pdfplumber>=0.11",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-mock>=3.14",
]

[project.scripts]
writer-agent = "writer_agent.cli:app"

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.backends._legacy:_Backend"
```

**Step 2: Create package init**

`src/writer_agent/__init__.py`:
```python
"""WriterAgent — CLI agent for dark romance novel writing."""
```

**Step 3: Create minimal CLI entry point**

`src/writer_agent/cli.py`:
```python
import typer

app = typer.Typer(
    name="writer-agent",
    help="CLI agent for writing dark romance novels with LM Studio",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version."""
    from writer_agent import __version__
    rich_print(f"WriterAgent v{__version__}")
```

Update `__init__.py` to add `__version__ = "0.1.0"`.

**Step 4: Install and verify**

Run: `cd D:/newquant/WriterAgent && pip install -e ".[dev]"`
Run: `writer-agent version`
Expected: `WriterAgent v0.1.0`

**Step 5: Commit**

```bash
git init
git add pyproject.toml src/ tests/
git commit -m "feat: project skeleton with typer CLI"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `src/writer_agent/config.py`
- Test: `tests/test_config.py`

**Step 1: Write failing test for config loading**

```python
# tests/test_config.py
import pytest
from writer_agent.config import Config


def test_default_config():
    config = Config()
    assert config.lm_studio_url == "http://localhost:1234/v1"
    assert config.model_name == ""  # auto-detect from LM Studio
    assert config.max_context_tokens == 8192
    assert config.db_path.name == "writer_agent.db"


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("WRITER_LM_STUDIO_URL", "http://custom:9999/v1")
    monkeypatch.setenv("WRITER_MODEL_NAME", "my-model")
    monkeypatch.setenv("WRITER_MAX_CONTEXT_TOKENS", "32768")
    config = Config.from_env()
    assert config.lm_studio_url == "http://custom:9999/v1"
    assert config.model_name == "my-model"
    assert config.max_context_tokens == 32768
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — module not found

**Step 3: Implement Config**

```python
# src/writer_agent/config.py
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/config.py tests/test_config.py
git commit -m "feat: configuration module with env overrides"
```

---

### Task 3: Database Layer — Schema & Connection

**Files:**
- Create: `src/writer_agent/db/__init__.py`
- Create: `src/writer_agent/db/database.py`
- Create: `src/writer_agent/db/models.py`
- Create: `src/writer_agent/db/repositories.py`
- Test: `tests/test_database.py`

**Step 1: Write failing test for database creation**

```python
# tests/test_database.py
import pytest
from pathlib import Path
from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, CharacterRepo, ChapterRepo


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database = Database(db_path)
    database.initialize()
    return database


def test_database_creates_tables(db):
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {row[0] for row in tables}
    assert "projects" in table_names
    assert "characters" in table_names
    assert "chapters" in table_names
    assert "plot_threads" in table_names
    assert "relationships" in table_names
    assert "world_elements" in table_names
    assert "style_profiles" in table_names
    assert "brainstorm_sessions" in table_names
    assert "timeline_events" in table_names


def test_project_crud(db):
    repo = ProjectRepo(db)
    project_id = repo.create(name="Test Novel", genre="dark romance")
    project = repo.get(project_id)
    assert project["name"] == "Test Novel"
    assert project["genre"] == "dark romance"
    assert project["status"] == "brainstorming"


def test_character_crud(db):
    repo = CharacterRepo(db)
    project_id = ProjectRepo(db).create(name="Test")
    char_id = repo.create(
        project_id=project_id,
        name="Elena",
        description="Dark-haired femme fatale",
        personality="cold exterior, passionate interior",
    )
    char = repo.get(char_id)
    assert char["name"] == "Elena"
    assert char["status"] == "active"


def test_chapter_crud(db):
    repo = ChapterRepo(db)
    project_id = ProjectRepo(db).create(name="Test")
    chapter_id = repo.create(
        project_id=project_id,
        chapter_number=1,
        title="The Beginning",
        summary="They meet in a dark alley.",
        full_text="Full chapter text here...",
    )
    chapter = repo.get(chapter_id)
    assert chapter["chapter_number"] == 1
    assert chapter["word_count"] > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py -v`
Expected: FAIL — module not found

**Step 3: Implement database layer**

`src/writer_agent/db/__init__.py`:
```python
"""Database layer for WriterAgent."""
```

`src/writer_agent/db/database.py` — full schema with all tables:
- `projects` — novels (name, description, genre, tropes JSON, status, target_words)
- `characters` — (project_id, name, full_name, description, personality, background, arc, status, metadata JSON)
- `relationships` — (project_id, char_a, char_b, type, description, evolution)
- `plot_threads` — (project_id, name, description, status, importance, introduced_chapter, resolved_chapter)
- `world_elements` — (project_id, category, name, description, metadata JSON)
- `chapters` — (project_id, chapter_number, title, summary, full_text, word_count, status)
- `style_profiles` — (name, source_files JSON, analysis JSON, sample_passages JSON)
- `brainstorm_sessions` — (project_id, messages JSON, notes, created_at)
- `timeline_events` — (project_id, chapter_id, event_order, description, characters_involved JSON, plot_threads JSON)

All tables with proper foreign keys, timestamps, and indexes on project_id.

Implement `Database` class with:
- `__init__(self, path: Path)` — connection
- `initialize(self)` — create tables if not exist
- `execute(self, sql, params=())` — helper

`src/writer_agent/db/repositories.py` — CRUD repos for each table:
- `ProjectRepo` — create, get, list, update_status
- `CharacterRepo` — create, get, list_by_project, update, get_relationships
- `ChapterRepo` — create, get, list_by_project, get_latest, update_text
- `PlotThreadRepo` — create, get, list_by_project, resolve
- `RelationshipRepo` — create, get, list_by_project
- `WorldElementRepo` — create, get, list_by_project
- `StyleProfileRepo` — create, get, list
- `BrainstormSessionRepo` — create, add_message, get_history
- `TimelineEventRepo` — create, get_by_chapter, get_by_project

Each repo method returns dicts (row_factory = sqlite3.Row).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add src/writer_agent/db/ tests/test_database.py
git commit -m "feat: database layer with SQLite schema and CRUD repositories"
```

---

### Task 4: LM Studio Client

**Files:**
- Create: `src/writer_agent/llm/__init__.py`
- Create: `src/writer_agent/llm/client.py`
- Create: `src/writer_agent/llm/prompts.py`
- Test: `tests/test_llm_client.py`

**Step 1: Write failing test for LLM client**

```python
# tests/test_llm_client.py
import pytest
from unittest.mock import MagicMock, patch
from writer_agent.llm.client import LLMClient
from writer_agent.config import Config


def test_client_uses_openai_compatible_api():
    config = Config(lm_studio_url="http://localhost:1234/v1", model_name="test-model")
    client = LLMClient(config)
    assert client.base_url == "http://localhost:1234/v1"
    assert client.model == "test-model"


def test_generate_sends_correct_params(mocker):
    config = Config()
    client = LLMClient(config)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Generated text"
    mocker.patch.object(client, "_client")
    client._client.chat.completions.create.return_value = mock_response

    result = client.generate(
        system_prompt="You are a writer.",
        user_prompt="Write something dark.",
        max_tokens=2000,
    )
    assert result == "Generated text"
    client._client.chat.completions.create.assert_called_once()


def test_generate_with_context_assembles_messages(mocker):
    config = Config()
    client = LLMClient(config)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Dark prose"
    mocker.patch.object(client, "_client")
    client._client.chat.completions.create.return_value = mock_response

    result = client.generate(
        system_prompt="System",
        user_prompt="Write chapter 1",
        context_blocks=["Previous summary...", "Character: Elena is cold"],
        max_tokens=4000,
    )
    assert result == "Dark prose"
    call_args = client._client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    # context blocks should be injected between system and user messages
    assert len(messages) >= 3  # system + context + user


def test_auto_detect_model(mocker):
    config = Config(model_name="")
    mock_models = MagicMock()
    mock_models.data = [MagicMock(id="local-model-q4_k_m")]
    mocker.patch.object(client := LLMClient(config), "_client")
    client._client.models.list.return_value = mock_models
    model = client.get_available_model()
    assert model == "local-model-q4_k_m"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL

**Step 3: Implement LLM client**

`src/writer_agent/llm/client.py`:
```python
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
```

`src/writer_agent/llm/prompts.py` — system prompt templates:
```python
SYSTEM_WRITER = """You are a professional dark romance novelist. Your writing is:
- Atmospheric and sensual, with rich descriptions
- morally grey characters who are compelling despite (or because of) their flaws
- Complex relationships with power dynamics, tension, and slow-burn chemistry
- Dark themes handled with sophistication — violence, obsession, forbidden love
- Plot twists that recontextualize earlier events
- Multiple POV when needed to show different perspectives

Write in Russian. Maintain consistent tone and style."""

SYSTEM_BRAINSTORM = """You are a creative consultant for dark romance novels. You help develop:
- Unique premises that subvert tropes
- Morally complex characters with interconnected fates
- Multi-layered plots with suspense and reveals
- World-building that enhances the dark atmosphere
- Tropes: enemies-to-lovers, forbidden love, mafia/crime, supernatural, psychological thriller

You suggest bold, unexpected ideas while respecting the author's vision.
Respond in Russian."""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/llm/ tests/test_llm_client.py
git commit -m "feat: LM Studio client with OpenAI-compatible API"
```

---

## Phase 2: Style Analysis

### Task 5: Document Parsers

**Files:**
- Create: `src/writer_agent/analysis/__init__.py`
- Create: `src/writer_agent/analysis/parser.py`
- Test: `tests/test_parser.py`

**Step 1: Write failing test**

```python
# tests/test_parser.py
import pytest
from pathlib import Path
from writer_agent.analysis.parser import parse_document


def test_parse_txt(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("Dark text here.", encoding="utf-8")
    result = parse_document(f)
    assert result == "Dark text here."


def test_parse_md(tmp_path):
    f = tmp_path / "sample.md"
    f.write_text("# Chapter 1\n\nDark **text** here.", encoding="utf-8")
    result = parse_document(f)
    assert "Chapter 1" in result
    assert "text" in result


def test_parse_docx(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("Dark paragraph one.")
    doc.add_paragraph("Dark paragraph two.")
    f = tmp_path / "sample.docx"
    doc.save(str(f))
    result = parse_document(f)
    assert "Dark paragraph one." in result
    assert "Dark paragraph two." in result


def test_parse_pdf(tmp_path):
    # pdfplumber-based parsing — test with a real fixture or mock
    # For now, test the path routing
    f = tmp_path / "sample.unsupported"
    f.write_text("stuff", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported format"):
        parse_document(f)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser.py -v`
Expected: FAIL

**Step 3: Implement parser**

```python
# src/writer_agent/analysis/parser.py
from pathlib import Path
import pdfplumber


def parse_document(path: Path) -> str:
    """Parse document and return plain text."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".text"):
        return path.read_text(encoding="utf-8")
    elif suffix == ".md":
        return path.read_text(encoding="utf-8")  # raw markdown is fine
    elif suffix == ".docx":
        return _parse_docx(path)
    elif suffix == ".pdf":
        return _parse_pdf(path)
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def _parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_pdf(path: Path) -> str:
    with pdfplumber.open(str(path)) as pdf:
        pages = [page.extract_text() for page in pdf.pages if page.extract_text()]
    return "\n\n".join(pages)


def parse_directory(dir_path: Path) -> dict[str, str]:
    """Parse all supported documents in directory. Returns {filename: text}."""
    results = {}
    for path in Path(dir_path).iterdir():
        if path.suffix.lower() in (".txt", ".md", ".docx", ".pdf"):
            try:
                results[path.name] = parse_document(path)
            except Exception as e:
                print(f"Warning: failed to parse {path.name}: {e}")
    return results
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/analysis/ tests/test_parser.py
git commit -m "feat: document parsers for txt, md, docx, pdf"
```

---

### Task 6: Style Analyzer

**Files:**
- Create: `src/writer_agent/analysis/style.py`
- Test: `tests/test_style.py`

**Step 1: Write failing test**

```python
# tests/test_style.py
import pytest
from writer_agent.analysis.style import StyleAnalyzer


def test_analyze_extracts_basic_metrics():
    analyzer = StyleAnalyzer()
    sample = "Она вошла в комнату. Тёмные волосы падали на плечи. Он смотрел не отрываясь."
    result = analyzer.analyze(sample)
    assert "avg_sentence_length" in result
    assert "total_words" in result
    assert result["total_words"] > 0


def test_analyze_extracts_vocabulary_patterns():
    analyzer = StyleAnalyzer()
    sample = "Тьма обволакивала её. Тёмные глаза сверкали. Тьма снова наступала."
    result = analyzer.analyze(sample)
    assert "frequent_words" in result
    assert any("тьм" in w.lower() for w in result["frequent_words"])


def test_analyze_extracts_sample_passages():
    analyzer = StyleAnalyzer()
    text = "Параграф один. Достаточно длинный. Для анализа.\n\nПараграф второй. Тоже текст. Для проверки."
    result = analyzer.analyze(text)
    assert "sample_passages" in result
    assert len(result["sample_passages"]) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_style.py -v`
Expected: FAIL

**Step 3: Implement StyleAnalyzer**

The analyzer extracts:
- `avg_sentence_length` — средняя длина предложения в словах
- `total_words` — общее количество слов
- `frequent_words` — частые значимые слова (без стоп-слов)
- `sentence_patterns` — типы предложений (вопросительные, восклицательные, повествовательные)
- `paragraph_lengths` — распределение длин параграфов
- `dialogue_ratio` — доля диалогов в тексте
- `sample_passages` — 3-5 характерных отрывков
- `pov_style` — особенности POV (1st/3rd person, tense)

```python
# src/writer_agent/analysis/style.py
import re
from collections import Counter
from dataclasses import dataclass, field


# Minimal Russian stop words
STOP_WORDS = {
    "и", "в", "на", "с", "что", "это", "как", "не", "он", "она", "они",
    "но", "а", "к", "у", "по", "из", "за", "от", "о", "для", "это",
    "был", "была", "было", "быть", "есть", "будет", "я", "ты", "мы", "вы",
    "его", "её", "их", "мой", "твой", "свой", "наш", "ваш", "тот", "этот",
    "же", "ли", "уже", "ещё", "даже", "тоже", "так", "вот", "тут", "где",
    "когда", "только", "ни", "бы", "до", "если", "при", "чем", "или",
}


@dataclass
class StyleProfile:
    avg_sentence_length: float = 0.0
    total_words: int = 0
    frequent_words: list[str] = field(default_factory=list)
    sentence_patterns: dict = field(default_factory=dict)
    paragraph_lengths: list[int] = field(default_factory=list)
    dialogue_ratio: float = 0.0
    sample_passages: list[str] = field(default_factory=list)
    pov_style: str = ""


class StyleAnalyzer:
    def analyze(self, text: str) -> dict:
        sentences = self._split_sentences(text)
        words = self._tokenize(text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        return {
            "avg_sentence_length": self._avg_sentence_len(sentences, words),
            "total_words": len(words),
            "frequent_words": self._frequent_words(words, top=30),
            "sentence_patterns": self._sentence_patterns(sentences),
            "paragraph_lengths": [self._count_words(p) for p in paragraphs],
            "dialogue_ratio": self._dialogue_ratio(text),
            "sample_passages": self._extract_passages(paragraphs, count=5),
            "pov_style": self._detect_pov(text),
        }

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'[а-яА-ЯёЁa-zA-Z]+', text)

    def _count_words(self, text: str) -> int:
        return len(self._tokenize(text))

    def _avg_sentence_len(self, sentences: list[str], words: list[str]) -> float:
        if not sentences:
            return 0.0
        return len(words) / len(sentences)

    def _frequent_words(self, words: list[str], top: int = 30) -> list[str]:
        filtered = [w.lower() for w in words if w.lower() not in STOP_WORDS and len(w) > 2]
        counter = Counter(filtered)
        return [w for w, _ in counter.most_common(top)]

    def _sentence_patterns(self, sentences: list[str]) -> dict:
        total = len(sentences)
        if total == 0:
            return {}
        questions = sum(1 for s in sentences if s.endswith("?"))
        exclamations = sum(1 for s in sentences if s.endswith("!"))
        return {
            "questions_ratio": questions / total,
            "exclamations_ratio": exclamations / total,
            "statements_ratio": 1 - (questions + exclamations) / total,
        }

    def _dialogue_ratio(self, text: str) -> float:
        dialogue_chars = sum(len(m) for m in re.findall(r'—[^—]+—|«[^»]+»|"[^"]+"', text))
        total = len(text)
        return dialogue_chars / total if total > 0 else 0.0

    def _extract_passages(self, paragraphs: list[str], count: int = 5) -> list[str]:
        scored = sorted(paragraphs, key=lambda p: len(p), reverse=True)
        return scored[:count]

    def _detect_pov(self, text: str) -> str:
        first_person = len(re.findall(r'\bя\b', text, re.IGNORECASE))
        third_person = len(re.findall(r'\bон\b|\bона\b|\bони\b', text, re.IGNORECASE))
        if first_person > third_person * 2:
            return "first_person"
        return "third_person"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_style.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/analysis/style.py tests/test_style.py
git commit -m "feat: style analyzer for vocabulary, patterns, POV detection"
```

---

## Phase 3: Brainstorm Engine

### Task 7: Brainstorm Session Manager

**Files:**
- Create: `src/writer_agent/engine/__init__.py`
- Create: `src/writer_agent/engine/brainstorm.py`
- Test: `tests/test_brainstorm.py`

**Step 1: Write failing test**

```python
# tests/test_brainstorm.py
import pytest
from unittest.mock import MagicMock
from writer_agent.engine.brainstorm import BrainstormEngine
from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, CharacterRepo


@pytest.fixture
def engine(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    llm = MagicMock()
    return BrainstormEngine(db=db, llm_client=llm)


def test_start_session_creates_project(engine):
    session_id = engine.start_session(title="Dark Love")
    assert session_id is not None
    project = ProjectRepo(engine.db).get_by_name("Dark Love")
    assert project is not None


def test_chat_sends_message_and_gets_response(engine):
    engine.llm_client.chat.return_value = "Как насчёт истории о вампире-мафиози?"
    session_id = engine.start_session(title="Test")
    response = engine.chat(session_id, "Предложи интересную концепцию")
    assert "вампире" in response
    engine.llm_client.chat.assert_called_once()


def test_save_character_from_brainstorm(engine):
    engine.llm_client.chat.return_value = "Character concept here"
    session_id = engine.start_session(title="Test")
    engine.save_character(
        session_id=session_id,
        name="Dante",
        description="Mafia boss with a dark secret",
        personality="ruthless, possessive, secretly vulnerable",
    )
    project = ProjectRepo(engine.db).get_by_name("Test")
    chars = CharacterRepo(engine.db).list_by_project(project["id"])
    assert len(chars) == 1
    assert chars[0]["name"] == "Dante"


def test_get_session_history(engine):
    engine.llm_client.chat.return_value = "Response"
    session_id = engine.start_session(title="Test")
    engine.chat(session_id, "Message 1")
    engine.chat(session_id, "Message 2")
    history = engine.get_history(session_id)
    assert len(history) == 4  # 2 user + 2 assistant
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_brainstorm.py -v`
Expected: FAIL

**Step 3: Implement BrainstormEngine**

```python
# src/writer_agent/engine/brainstorm.py
from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, BrainstormSessionRepo,
    PlotThreadRepo, WorldElementRepo,
)
from writer_agent.llm.prompts import SYSTEM_BRAINSTORM


class BrainstormEngine:
    def __init__(self, db: Database, llm_client):
        self.db = db
        self.llm_client = llm_client
        self.project_repo = ProjectRepo(db)
        self.char_repo = CharacterRepo(db)
        self.session_repo = BrainstormSessionRepo(db)
        self.plot_repo = PlotThreadRepo(db)
        self.world_repo = WorldElementRepo(db)

    def start_session(self, title: str) -> int:
        project_id = self.project_repo.create(name=title, genre="dark romance")
        session_id = self.session_repo.create(project_id=project_id, notes="")
        return session_id

    def chat(self, session_id: int, user_message: str) -> str:
        self.session_repo.add_message(session_id, role="user", content=user_message)
        history = self.session_repo.get_messages(session_id)
        messages = [{"role": "system", "content": SYSTEM_BRAINSTORM}] + history
        response = self.llm_client.chat(messages=messages, max_tokens=2000)
        self.session_repo.add_message(session_id, role="assistant", content=response)
        return response

    def get_history(self, session_id: int) -> list[dict]:
        return self.session_repo.get_messages(session_id)

    def save_character(self, session_id: int, **kwargs) -> int:
        session = self.session_repo.get(session_id)
        project_id = session["project_id"]
        return self.char_repo.create(project_id=project_id, **kwargs)

    def save_plot_thread(self, session_id: int, **kwargs) -> int:
        session = self.session_repo.get(session_id)
        project_id = session["project_id"]
        return self.plot_repo.create(project_id=project_id, **kwargs)

    def save_world_element(self, session_id: int, **kwargs) -> int:
        session = self.session_repo.get(session_id)
        project_id = session["project_id"]
        return self.world_repo.create(project_id=project_id, **kwargs)

    def finalize_session(self, session_id: int) -> int:
        """Mark project as ready for writing. Returns project_id."""
        session = self.session_repo.get(session_id)
        self.project_repo.update_status(session["project_id"], "outlined")
        return session["project_id"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_brainstorm.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/engine/ tests/test_brainstorm.py
git commit -m "feat: brainstorm engine with session management"
```

---

### Task 8: Context Builder

**Files:**
- Create: `src/writer_agent/engine/context.py`
- Test: `tests/test_context.py`

**Step 1: Write failing test**

```python
# tests/test_context.py
import pytest
from writer_agent.engine.context import ContextBuilder
from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, ChapterRepo,
    PlotThreadRepo, WorldElementRepo, RelationshipRepo,
)


@pytest.fixture
def populated_db(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    proj_id = ProjectRepo(db).create(name="Test", genre="dark romance")
    CharacterRepo(db).create(project_id=proj_id, name="Elena",
                             description="Dark-haired", personality="cold")
    CharacterRepo(db).create(project_id=proj_id, name="Dante",
                             description="Mafia boss", personality="ruthless")
    ChapterRepo(db).create(project_id=proj_id, chapter_number=1,
                           title="Ch1", summary="They met.",
                           full_text="Full text of chapter one...")
    PlotThreadRepo(db).create(project_id=proj_id, name="Revenge plot",
                              description="Elena seeks revenge", status="active")
    return db, proj_id


def test_build_context_within_token_limit(populated_db):
    db, proj_id = populated_db
    builder = ContextBuilder(db, max_tokens=2000)
    context = builder.build(project_id=proj_id, current_chapter=2)
    assert len(context["blocks"]) > 0
    assert context["total_tokens"] <= 2000
    # Should include: outline, characters, prev chapter summary, plot threads
    full_context = "\n".join(context["blocks"])
    assert "Elena" in full_context
    assert "Dante" in full_context


def test_build_context_includes_previous_chapter(populated_db):
    db, proj_id = populated_db
    builder = ContextBuilder(db, max_tokens=4000)
    context = builder.build(project_id=proj_id, current_chapter=2)
    full_context = "\n".join(context["blocks"])
    assert "They met" in full_context  # summary from ch1


def test_build_context_truncates_when_needed(populated_db):
    db, proj_id = populated_db
    builder = ContextBuilder(db, max_tokens=100)  # very small
    context = builder.build(project_id=proj_id, current_chapter=2)
    assert context["total_tokens"] <= 100 + 50  # small margin
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py -v`
Expected: FAIL

**Step 3: Implement ContextBuilder**

Strategy for assembling context within token budget:
1. **Priority 1 (always):** Project outline / arc summary (~200 tokens)
2. **Priority 2 (always):** Characters involved in current chapter (~300-500 tokens)
3. **Priority 3:** Previous chapter summary (~200 tokens)
4. **Priority 4:** Active plot threads (~200 tokens)
5. **Priority 5:** Relevant world elements (~200 tokens)
6. **Priority 6:** Recent passage from previous chapter for style continuity (~300 tokens)
7. **Priority 7:** Character relationships (~200 tokens)

Lower priority items are dropped first if context exceeds budget.

```python
# src/writer_agent/engine/context.py
from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, ChapterRepo,
    PlotThreadRepo, WorldElementRepo, RelationshipRepo,
)


class ContextBuilder:
    def __init__(self, db: Database, max_tokens: int = 6000):
        self.db = db
        self.max_tokens = max_tokens
        self.projects = ProjectRepo(db)
        self.characters = CharacterRepo(db)
        self.chapters = ChapterRepo(db)
        self.plots = PlotThreadRepo(db)
        self.world = WorldElementRepo(db)
        self.relationships = RelationshipRepo(db)

    def build(self, project_id: int, current_chapter: int) -> dict:
        budget = self.max_tokens
        blocks = []

        # Priority 1: Project overview
        project = self.projects.get(project_id)
        overview = f"[Проект: {project['name']}]\nЖанр: {project.get('genre', '')}\nСтатус: {project.get('description', '')}"
        blocks.append(("overview", overview))

        # Priority 2: Characters
        chars = self.characters.list_by_project(project_id)
        char_block = "[Персонажи]\n" + "\n".join(
            f"- {c['name']}: {c.get('description', '')} ({c.get('personality', '')})"
            for c in chars
        )
        blocks.append(("characters", char_block))

        # Priority 3: Previous chapter summary
        prev_chapter = self.chapters.get_by_number(project_id, current_chapter - 1)
        if prev_chapter:
            summary_block = f"[Предыдущая глава ({prev_chapter['chapter_number']}: {prev_chapter.get('title', '')})]\n{prev_chapter['summary']}"
            blocks.append(("prev_summary", summary_block))

        # Priority 4: Plot threads
        threads = self.plots.list_by_project(project_id, status="active")
        if threads:
            thread_block = "[Активные сюжетные нити]\n" + "\n".join(
                f"- {t['name']}: {t['description']}" for t in threads
            )
            blocks.append(("plot_threads", thread_block))

        # Priority 5: World elements
        elements = self.world.list_by_project(project_id)
        if elements:
            world_block = "[Мир]\n" + "\n".join(
                f"- {e['name']} ({e['category']}): {e['description']}" for e in elements[:10]
            )
            blocks.append(("world", world_block))

        # Priority 6: Last passage from previous chapter
        if prev_chapter and prev_chapter.get("full_text"):
            text = prev_chapter["full_text"]
            passage = text[-1500:] if len(text) > 1500 else text
            blocks.append(("prev_passage", f"[Конец предыдущей главы]\n{passage}"))

        # Priority 7: Relationships
        rels = self.relationships.list_by_project(project_id)
        if rels:
            rel_block = "[Отношения]\n" + "\n".join(
                f"- {r.get('char_a_name', '?')} ↔ {r.get('char_b_name', '?')}: {r['relationship_type']} — {r.get('description', '')}"
                for r in rels
            )
            blocks.append(("relationships", rel_block))

        # Truncate to fit budget (drop lowest priority first, from end)
        return self._fit_budget(blocks, budget)

    def _fit_budget(self, blocks: list, budget: int) -> dict:
        result_blocks = []
        total = 0
        for name, text in blocks:
            tokens = self._estimate_tokens(text)
            if total + tokens <= budget:
                result_blocks.append(text)
                total += tokens
            # else: skip — higher priority items are first
        return {"blocks": result_blocks, "total_tokens": total}

    def _estimate_tokens(self, text: str) -> int:
        cyrillic = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        other = len(text) - cyrillic
        return int(cyrillic / 2 + other / 4)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/engine/context.py tests/test_context.py
git commit -m "feat: context builder with priority-based token budget"
```

---

## Phase 4: Generation Pipeline

### Task 9: Chapter Generator

**Files:**
- Create: `src/writer_agent/engine/generator.py`
- Test: `tests/test_generator.py`

**Step 1: Write failing test**

```python
# tests/test_generator.py
import pytest
from unittest.mock import MagicMock
from writer_agent.engine.generator import ChapterGenerator
from writer_agent.engine.context import ContextBuilder
from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, CharacterRepo, ChapterRepo


@pytest.fixture
def setup(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    llm = MagicMock()
    ctx_builder = ContextBuilder(db, max_tokens=2000)
    gen = ChapterGenerator(db=db, llm_client=llm, context_builder=ctx_builder)
    proj_id = ProjectRepo(db).create(name="Test")
    CharacterRepo(db).create(project_id=proj_id, name="Elena",
                             description="Dark woman", personality="fierce")
    return gen, db, proj_id, llm


def test_generate_chapter_calls_llm_with_context(setup):
    gen, db, proj_id, llm = setup
    llm.generate.return_value = "Глава 1. Тёмная ночь..."

    result = gen.generate_chapter(
        project_id=proj_id,
        chapter_number=1,
        outline="Elena enters the club",
        target_words=2000,
    )
    assert "Тёмная ночь" in result["full_text"]
    assert llm.generate.called


def test_generate_chapter_saves_to_db(setup):
    gen, db, proj_id, llm = setup
    llm.generate.return_value = "Содержимое главы."

    result = gen.generate_chapter(project_id=proj_id, chapter_number=1)
    chapters = ChapterRepo(db).list_by_project(proj_id)
    assert len(chapters) == 1
    assert chapters[0]["full_text"] == "Содержимое главы."


def test_generate_with_style_profile(setup):
    gen, db, proj_id, llm = setup
    llm.generate.return_value = "Стильный текст."

    style_prompt = "Используй короткие резкие предложения. Много диалогов."
    result = gen.generate_chapter(
        project_id=proj_id,
        chapter_number=1,
        style_instructions=style_prompt,
    )
    call_args = llm.generate.call_args
    assert style_prompt in call_args.kwargs.get("system_prompt", "") or \
           style_prompt in str(call_args)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_generator.py -v`
Expected: FAIL

**Step 3: Implement ChapterGenerator**

```python
# src/writer_agent/engine/generator.py
from writer_agent.db.database import Database
from writer_agent.db.repositories import ChapterRepo, ProjectRepo
from writer_agent.engine.context import ContextBuilder
from writer_agent.llm.prompts import SYSTEM_WRITER


class ChapterGenerator:
    def __init__(self, db: Database, llm_client, context_builder: ContextBuilder):
        self.db = db
        self.llm = llm_client
        self.ctx = context_builder
        self.chapter_repo = ChapterRepo(db)
        self.project_repo = ProjectRepo(db)

    def generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        outline: str = "",
        target_words: int = 3000,
        style_instructions: str = "",
        temperature: float = 0.85,
    ) -> dict:
        # Build context from memory
        context = self.ctx.build(project_id=project_id, current_chapter=chapter_number)

        # Assemble prompts
        system = SYSTEM_WRITER
        if style_instructions:
            system += f"\n\n[Стилевые инструкции автора]\n{style_instructions}"

        user = f"[Задание]\nНапиши главу {chapter_number}."
        if outline:
            user += f"\n\n[План главы]\n{outline}"
        user += f"\n\nЦелевой объём: ~{target_words} слов."

        # Generate
        full_text = self.llm.generate(
            system_prompt=system,
            user_prompt=user,
            context_blocks=context["blocks"],
            max_tokens=min(target_words * 2, 8000),  # tokens, not words
            temperature=temperature,
        )

        # Save to DB
        word_count = len(full_text.split())
        chapter_id = self.chapter_repo.create(
            project_id=project_id,
            chapter_number=chapter_number,
            title=f"Глава {chapter_number}",
            summary=self._generate_summary(full_text),
            full_text=full_text,
        )

        return {
            "chapter_id": chapter_id,
            "full_text": full_text,
            "word_count": word_count,
        }

    def _generate_summary(self, text: str) -> str:
        """Quick summary — either from LLM or simple extraction."""
        # For efficiency, take first 200 chars as rough summary
        # TODO: can use LLM to generate proper summary
        if len(text) <= 300:
            return text
        return text[:300] + "..."

    def revise_chapter(self, chapter_id: int, instructions: str) -> dict:
        chapter = self.chapter_repo.get(chapter_id)
        system = SYSTEM_WRITER + "\n\nТы перерабатываешь существующую главу по указаниям автора."
        user = f"[Текущий текст главы]\n{chapter['full_text']}\n\n[Указания для переработки]\n{instructions}"

        new_text = self.llm.generate(
            system_prompt=system,
            user_prompt=user,
            max_tokens=8000,
        )

        self.chapter_repo.update_text(chapter_id, new_text)
        return {"chapter_id": chapter_id, "full_text": new_text}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_generator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/writer_agent/engine/generator.py tests/test_generator.py
git commit -m "feat: chapter generator with context-aware generation"
```

---

## Phase 5: CLI Integration

### Task 10: Full CLI Commands

**Files:**
- Modify: `src/writer_agent/cli.py`
- Create: `src/writer_agent/export/__init__.py`
- Create: `src/writer_agent/export/exporter.py`
- Test: `tests/test_cli.py`

**Step 1: Write failing test for CLI commands**

```python
# tests/test_cli.py
import pytest
from typer.testing import CliRunner
from writer_agent.cli import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_new_project_creates_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "Test Novel"])
    assert result.exit_code == 0
    assert (tmp_path / "data" / "writer_agent.db").exists()


def test_list_projects_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # First create db
    runner.invoke(app, ["new", "Test"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0


def test_analyze_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "sample.txt").write_text("Тёмный текст для анализа.", encoding="utf-8")
    result = runner.invoke(app, ["analyze-style", str(examples)])
    assert result.exit_code == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

**Step 3: Implement full CLI**

The CLI has these commands:

```
writer-agent new <title>          — Create new project, enter brainstorm mode
writer-agent list                 — List all projects
writer-agent open <title>         — Open project for writing
writer-agent brainstorm <title>   — Enter brainstorm mode
writer-agent write <title>        — Generate next chapter
writer-agent revise <title> <N>   — Revise chapter N
writer-agent analyze-style <dir>  — Analyze writing style from examples
writer-agent export <title>       — Export novel to file
writer-agent status <title>       — Show project status, word count, characters
writer-agent version              — Show version
```

**Brainstorm mode** — interactive REPL:
- User types freely, agent responds with creative ideas
- `/save char <name> <desc>` — save character idea
- `/save plot <name> <desc>` — save plot thread
- `/save world <name> <desc>` — save world element
- `/done` — finalize brainstorm, move to outlined status
- `/quit` — exit without saving

**Write mode** — chapter generation:
- Shows current progress (chapter X / target)
- User can specify outline for next chapter or let agent decide
- `/next` — generate next chapter with auto-outline
- `/revise <N> <instructions>` — revise chapter N
- `/status` — show characters, threads, word count
- `/quit` — exit

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Implement exporter**

```python
# src/writer_agent/export/exporter.py
from pathlib import Path
from writer_agent.db.repositories import ChapterRepo


class Exporter:
    def __init__(self, chapter_repo: ChapterRepo):
        self.repo = chapter_repo

    def to_markdown(self, project_id: int, output_path: Path, title: str = ""):
        chapters = self.repo.list_by_project(project_id)
        lines = [f"# {title}\n"] if title else []
        for ch in sorted(chapters, key=lambda c: c["chapter_number"]):
            lines.append(f"\n## {ch.get('title', f'Глава {ch[\"chapter_number\"]}')}\n")
            lines.append(ch["full_text"])
            lines.append("\n---\n")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def to_txt(self, project_id: int, output_path: Path, title: str = ""):
        chapters = self.repo.list_by_project(project_id)
        lines = [f"{title}\n{'=' * 40}\n"] if title else []
        for ch in sorted(chapters, key=lambda c: c["chapter_number"]):
            lines.append(f"\n{ch.get('title', f'Глава {ch[\"chapter_number\"]}')}\n")
            lines.append(ch["full_text"])
            lines.append("\n" + "-" * 40 + "\n")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def to_docx(self, project_id: int, output_path: Path, title: str = ""):
        from docx import Document
        doc = Document()
        if title:
            doc.add_heading(title, level=0)
        chapters = self.repo.list_by_project(project_id)
        for ch in sorted(chapters, key=lambda c: c["chapter_number"]):
            doc.add_heading(ch.get("title", f"Глава {ch['chapter_number']}"), level=1)
            for paragraph in ch["full_text"].split("\n\n"):
                if paragraph.strip():
                    doc.add_paragraph(paragraph.strip())
        doc.save(str(output_path))
```

**Step 6: Commit**

```bash
git add src/writer_agent/cli.py src/writer_agent/export/ tests/test_cli.py
git commit -m "feat: full CLI with brainstorm, write, and export commands"
```

---

## Phase 6: Advanced Features

### Task 11: Summary Generation & Long-Form Memory

For 600K words, each chapter needs a compressed summary that fits in context. After each chapter is generated, use LLM to create a concise summary.

**Files:**
- Modify: `src/writer_agent/engine/generator.py` — add proper LLM-based summary
- Modify: `src/writer_agent/engine/context.py` — add multi-chapter history compression

**Step 1: Write test for LLM-based summary**

```python
def test_generate_summary_with_llm(mocker):
    llm = MagicMock()
    llm.generate.return_value = "Елена встречает Данте в клубе. Возникает напряжение."
    gen = ChapterGenerator(db=MagicMock(), llm_client=llm, context_builder=MagicMock())
    summary = gen._generate_summary_llm("Длинный текст главы...")
    assert "Елена" in summary
```

**Step 2: Implement and verify**

Add `_generate_summary_llm` method that asks LLM to compress a chapter into 2-3 sentences. Called after each chapter generation. Falls back to truncation if LLM is unavailable.

**Step 3: Add multi-chapter context**

When `current_chapter > 5`, instead of just the previous chapter, include compressed summaries of the last 5 chapters to maintain plot coherence.

**Step 4: Commit**

```bash
git commit -m "feat: LLM-based chapter summaries and multi-chapter context"
```

---

### Task 12: Consistency Checker

Before writing a new chapter, check for potential inconsistencies (character mentions, timeline, relationship state).

**Files:**
- Create: `src/writer_agent/engine/consistency.py`
- Test: `tests/test_consistency.py`

Checks:
- Dead characters shouldn't appear alive
- Resolved plot threads shouldn't be referenced as active
- Relationship states should be consistent with last chapter
- Timeline events should be in order

**Step 1: Write tests**

```python
def test_detect_dead_character_inconsistency():
    """Flag if a dead character is planned to appear."""
    ...

def test_detect_resolved_thread_inconsistency():
    """Flag if a resolved thread is referenced as active."""
    ...
```

**Step 2: Implement ConsistencyChecker**

Uses LLM to review the outline against stored state before generation.

**Step 3: Commit**

```bash
git commit -m "feat: consistency checker for characters, plot threads, timeline"
```

---

### Task 13: Interactive Brainstorm REPL

Rich, interactive brainstorm mode with colored output, formatting, and keyboard shortcuts.

**Files:**
- Modify: `src/writer_agent/cli.py` — add brainstorm REPL
- Modify: `src/writer_agent/engine/brainstorm.py` — add structured idea extraction

**Features:**
- Rich-formatted output (markdown rendering in terminal)
- Slash commands: `/save`, `/done`, `/quit`, `/help`, `/characters`, `/plots`, `/ideas`
- Auto-extract character/plot ideas from brainstorm responses
- Style profile integration — inject style analysis into brainstorm

**Step 1: Test REPL commands**

```python
def test_brainstorm_save_character_command():
    ...
def test_brainstorm_done_finalizes_project():
    ...
```

**Step 2: Implement with Rich Console**

Use `rich.console.Console` for formatted output, `rich.markdown.Markdown` for rendering LLM responses, `rich.panel.Panel` for character/plot cards.

**Step 3: Commit**

```bash
git commit -m "feat: interactive brainstorm REPL with Rich formatting"
```

---

### Task 14: Style Profile Integration

Connect style analysis to generation pipeline so the agent writes in the user's style.

**Files:**
- Modify: `src/writer_agent/engine/generator.py` — inject style prompt
- Modify: `src/writer_agent/cli.py` — `analyze-style` saves to DB

When generating chapters, the style profile is:
1. Loaded from DB
2. Converted to a style instruction prompt
3. Appended to the system prompt

Example style instruction:
```
[Стиль автора]
- Средняя длина предложения: 14 слов
- POV: третье лицо
- Высокая доля диалогов (35%)
- Частые слова: тьма, взгляд, кожа, шёпот, холод
- Характерные приёмы: короткие резкие фразы, контраст тепла и холода
```

**Step 1: Test style integration**

```python
def test_style_instructions_in_generation():
    ...
```

**Step 2: Implement and commit**

```bash
git commit -m "feat: style profile integration in generation pipeline"
```

---

## Summary of Tasks

| # | Task | Phase | Dependencies |
|---|------|-------|-------------|
| 1 | Project Skeleton | Foundation | None |
| 2 | Configuration Module | Foundation | Task 1 |
| 3 | Database Layer | Foundation | Task 1 |
| 4 | LM Studio Client | Foundation | Task 2 |
| 5 | Document Parsers | Style Analysis | Task 1 |
| 6 | Style Analyzer | Style Analysis | Task 5 |
| 7 | Brainstorm Engine | Brainstorm | Task 3, 4 |
| 8 | Context Builder | Generation | Task 3 |
| 9 | Chapter Generator | Generation | Task 4, 8 |
| 10 | Full CLI Commands | CLI Integration | All above |
| 11 | Summary & Memory | Advanced | Task 9 |
| 12 | Consistency Checker | Advanced | Task 8, 9 |
| 13 | Brainstorm REPL | Advanced | Task 7, 10 |
| 14 | Style Integration | Advanced | Task 6, 9 |

**Total estimated tasks: 14 | ~60-80 bite-sized steps**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│                   CLI (Typer)               │
│  new │ brainstorm │ write │ analyze │ export │
└──────┬──────────┬──────────┬────────┬───────┘
       │          │          │        │
       ▼          ▼          ▼        ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Brain-   │ │ Chapter  │ │ Context  │ │ Exporter │
│ storm    │ │ Generator│ │ Builder  │ │          │
│ Engine   │ │          │ │          │ │          │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────┘
     │            │            │
     ▼            ▼            ▼
┌──────────────────────────────────────────────┐
│              LM Studio Client                │
│         (OpenAI-compatible API)              │
└──────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│             SQLite Database                  │
│  projects │ characters │ chapters │ plots    │
│  relationships │ world │ style │ timeline    │
└──────────────────────────────────────────────┘
```
