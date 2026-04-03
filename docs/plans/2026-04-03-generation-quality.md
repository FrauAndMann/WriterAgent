# Generation Quality Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## Goal

Решить три проблемы генерации дарк-романтических романов:
1. **Стиль** — текст generic, без атмосферы, чувственности, напряжения
2. **Контекст** — к главе 5-10 модель забывает что было, противоречит себе
3. **Сюжет** — главы не связаны, нет развития, нет арки

## Architecture Overview

```
                    ┌─────────────────────┐
                    │   Chapter Outline    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Scene Classifier  │ ← определяет тип сцены
                    │  (intro/dialogue/    │
                    │   action/climax/     │
                    │   reflection/erotic) │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Prompt Assembler   │
                    │  scene prompt +      │
                    │  style injector +    │
                    │  plot state +        │
                    │  context blocks      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   LLM Generation     │
                    └──────────┬──────────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
    ┌──────────▼─────┐ ┌──────▼───────┐ ┌─────▼──────────┐
    │  Hierarchical   │ │  Plot State  │ │  Consistency   │
    │  Summaries      │ │  Machine     │ │  Check         │
    │  (3 levels)     │ │  (update)    │ │  (validate)    │
    └────────────────┘ └──────────────┘ └────────────────┘
```

---

## Component 1: Scene Classifier + Scene Prompts

### Scene Types

| Type | Description | Prompt focus |
|------|-------------|-------------|
| `opening` | Первая сцена главы, вступление | Атмосфера, мир, тон |
| `dialogue` | Диалог-доминантная сцена | Реплики, подтекст, химия |
| `action` | Экшен, конфронтация, насилие | Темп, короткие фразы, кинематографичность |
| `climax` | Кульминация главы или арки | Максимальное напряжение, чувства |
| `reflection` | Внутренний мир, мысли, flashback | Лиричность, глубина, интроспекция |
| `erotic` | Сенсуальные/сексуальные сцены | Чувственность, тело, метафоры, pace |
| `transition` | Связующие сцены, перемещения | Краткость, движение, тизер следующего |

### Classification

LLM классифицирует outline главы на типы сцен:

```python
CLASSIFICATION_PROMPT = """Проанализируй план главы и определи типы сцен.
Для каждой сцены укажи: тип, краткое описание, вовлечённые персонажи.

Типы: opening, dialogue, action, climax, reflection, erotic, transition

Ответ в формате:
1. [type] — описание (персонажи)
2. [type] — описание (персонажи)
"""
```

### Scene Prompts

Каждый тип сцены имеет свой доп. промпт, который **дополняет** (не заменяет) SYSTEM_WRITER:

```python
SCENE_PROMPTS = {
    "opening": """Сцена-вступление. Создай плотную атмосферу с первых строк.
Используй synesthetic details (запах + звук + цвет). Читатель должен почувствовать мир кожей.
Начинай in media res — без долгих описаний, сразу в действие/эмоцию.""",

    "dialogue": """Диалог-сцена. Каждая реплика — это битва или танец.
Подтекст важнее текста: персонажи говорят одно, значат другое.
Используй action beats между репликами (взгляды, жесты, дыхание).
Диалог должен обнажать отношения и power dynamics.""",

    "action": """Экшен-сцена. Короткие, резкие предложения. Глаголы-действия.
Ощущение скорости и опасности. Кинематографичные ракурсы.
Перемежай экшен с моментами тишины — контраст усиливает напряжение.
Тело персонажа — усталость, боль, адреналин — всё физически.""",

    "climax": """Кульминация. Максимальное эмоциональное напряжение.
Каждое слово — на вес золота. Внутренний конфликт обнажается.
Используй contrast: тихий момент перед взрывом, нежность в жестокости.
Читатель должен забыть дышать.""",

    "reflection": """Сцена рефлексии. Внутренний мир персонажа.
Длинные, плавные предложения. Поток сознания, обрывки воспоминаний.
Метафоры и образы из подсознания. Прошлое вторгается в настоящее.
Не объясняй — покажи через ощущения и ассоциации.""",

    "erotic": """Сенсуальная сцена. Не porn — erotics.
Пять чувств: кожа, запах, вкус, звук, зрение. Метафоры природы (огонь, вода, гроза).
Power dynamics и vulnerability одновременно. Контроль и потеря контроля.
Pace: медленное нарастание, чередование нежности и интенсивности.
Тело говорит языком, который слова не знают.""",

    "transition": """Связующая сцена. Краткая, функциональная, но не скучная.
Один яркий образ, одна деталь, которая запомнится.
Подразни читателя тем, что будет дальше. Тизер, крючок.""",
}
```

### File

`src/writer_agent/llm/scene_prompts.py` (new)

---

## Component 2: Style Injector

### Concept

`StyleAnalyzer` уже извлекает 8 метрик. Style Injector превращает их в **детальный стилевой промпт** — не просто «частые слова», а полную стилистическую деконструкцию.

### Analysis → Prompt Pipeline

```python
def build_style_injection(analysis: dict, sample_passages: list[str]) -> str:
    """Convert style analysis into detailed writing instructions."""
    lines = ["[Стиль автора — точная имитация]"]

    # Rhythm
    avg_sent = analysis.get("avg_sentence_length", 12)
    if avg_sent > 20:
        lines.append("- Ритм: длинные, плавные предложения с придаточными и перечислениями. Пушкинский период.")
    elif avg_sent > 12:
        lines.append("- Ритм: средние предложения, баланс длинных и коротких. Чередуй.")
    else:
        lines.append("- Ритм: короткие, рубленые фразы. Хемингуэевская лаконичность. Каждое слово — удар.")

    # POV
    pov = analysis.get("pov_style", "third_person")
    if pov == "first_person":
        lines.append("- POV: первое лицо. Интимность, субъективность. Мир через призму «я».")
    else:
        lines.append("- POV: третье лицо. Ограниченный фокус — мир через восприятие одного персонажа в сцене.")

    # Dialogue
    dial = analysis.get("dialogue_ratio", 0)
    if dial > 0.3:
        lines.append(f"- Доля диалогов: {dial:.0%}. Диалоги — основной инструмент. Минимум narration между репликами.")
    elif dial > 0.1:
        lines.append(f"- Доля диалогов: {dial:.0%}. Диалоги для ключевых моментов. Баланс с описаниями.")
    else:
        lines.append("- Мало диалогов. Основной инструмент — описание, рефлексия, атмосфера.")

    # Vocabulary signature
    words = analysis.get("frequent_words", [])[:12]
    if words:
        lines.append(f"- Лексическая сигнатура: {', '.join(words)}. Используй эти слова как якоря стиля.")

    # Sentence patterns
    patterns = analysis.get("sentence_patterns", {})
    if patterns.get("questions_ratio", 0) > 0.1:
        lines.append("- Часто использует риторические вопросы как приём.")
    if patterns.get("exclamations_ratio", 0) > 0.05:
        lines.append("- Восклицания для эмоциональных пиков.")

    # Sample passages as few-shot
    if sample_passages:
        lines.append("\n[Образцы стиля — пиши так же]")
        for i, p in enumerate(sample_passages[:3], 1):
            snippet = p[:300].strip()
            if len(snippet) > 50:
                lines.append(f"  {i}. «{snippet}…»")

    return "\n".join(lines)
```

### File

`src/writer_agent/analysis/style_injector.py` (new)

---

## Component 3: Hierarchical Summaries

### Three Levels

| Level | Size | Purpose | Stored in |
|-------|------|---------|-----------|
| `detail` | ~300 words | Полное содержание главы: кто, что, где, ключевые реплики | `chapters.summary` |
| `compact` | ~50 words | Суть главы в абзаце | `chapters.compact_summary` (new column) |
| `arc` | ~20 words | Одно предложение: арочная функция главы | `chapters.arc_summary` (new column) |

### Example

```
Arc:      "Елена и Данте встречаются впервые — искра и опасность."
Compact:  "Елена входит в клуб Валентини, расследуя исчезновение сестры.
          Данте замечает её. Между ними — мгновенная химия и скрытая угроза.
          Она не знает что он вампир. Он не знает что она следователь."
Detail:   "Глава начинается с описания клуба Валентини... [300 слов]"
```

### Context Assembly (updated)

```
Priority 3: Chapter history
  - Arc summaries: ALL chapters (если compact — 20 слов, влезет всё)
  - Compact summaries: last history_chapters (5 × 50 = 250 слов)
  - Detail summary: previous chapter only (300 слов)
```

Для романа в 200 глав: 200 × 20 = 4000 слов arc summaries — влезает в контекст.

### Generation Pipeline

После генерации главы → 3 LLM-вызова для саммари:

```python
SUMMARY_PROMPTS = {
    "detail": "Создай подробное содержание главы в 200-300 слов. Включи: ключевые события, диалоги, эмоции, решения персонажей.",
    "compact": "Сожми содержание главы в 1-2 предложения (до 50 слов). Только суть: что произошло и что изменилось.",
    "arc": "Опиши функцию этой главы в общей арке романа одним предложением (до 20 слов). Формат: '[Персонажи] [действие] — [последствие]'.",
}
```

### DB Migration

Add columns to `chapters` table:
```sql
ALTER TABLE chapters ADD COLUMN compact_summary TEXT DEFAULT '';
ALTER TABLE chapters ADD COLUMN arc_summary TEXT DEFAULT '';
```

### File

`src/writer_agent/engine/generator.py` (modify: add `_generate_hierarchical_summaries`)

---

## Component 4: Plot State Machine

### Concept

После каждой главы LLM обновляет структурированное состояние сюжета. Хранится в БД, читается ContextBuilder'ом.

### State Structure

```python
@dataclass
class PlotState:
    # Active conflicts
    conflicts: list[dict]       # [{name, parties, status, intensity: 1-10, since_chapter}]
    # Character arcs
    character_arcs: list[dict]   # [{character, current_state, trajectory, last_chapter}]
    # Unresolved mysteries
    mysteries: list[dict]        # [{name, clues_given, reader_knows, resolution_chapter}]
    # Relationship evolution
    relationships: list[dict]    # [{pair, type, intensity: 1-10, direction, since_chapter}]
    # Tone arc
    tone: str                    # "rising_tension", "plateau", "climax", "falling", "resolution"
    # Reader expectations (hooks planted)
    hooks: list[dict]            # [{description, planted_chapter, expected_payoff_chapter}]
```

### DB Storage

New table `plot_states`:
```sql
CREATE TABLE IF NOT EXISTS plot_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    chapter_number INTEGER NOT NULL,
    state TEXT NOT NULL,           -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### Update Pipeline

После генерации главы + саммари → LLM обновляет state:

```python
UPDATE_STATE_PROMPT = """Ты аналитик сюжета. Обнови состояние романа на основе новой главы.

Текущее состояние:
{current_state}

Новая глава (summary):
{chapter_summary}

Обнови:
1. conflicts — новые/изменившиеся конфликты с intensity (1-10)
2. character_arcs — текущее эмоциональное состояние каждого персонажа
3. mysteries — нерешённые загадки, что уже раскрыто читателю
4. relationships — эволюция отношений с intensity и direction (warming/cooling/complicated)
5. tone — текущий тон арки
6. hooks — посаженные крючки (обещания читателю)

Ответ: строго JSON."""
```

### ContextBuilder Integration

Plot state читается как Priority 2.5 (после персонажей, до саммари глав):

```python
# Priority 2.5: Plot state
latest_state = PlotStateRepo(db).get_latest(project_id)
if latest_state:
    state = json.loads(latest_state["state"])
    state_block = format_plot_state(state)
    blocks.append(("plot_state", state_block))
```

### Files

- `src/writer_agent/engine/plot_state.py` (new: PlotState dataclass, update logic)
- `src/writer_agent/db/database.py` (modify: add plot_states table)
- `src/writer_agent/db/repositories.py` (modify: add PlotStateRepo)

---

## Implementation Plan

### Task 1: Scene Classifier + Scene Prompts
- Create `src/writer_agent/llm/scene_prompts.py`
- Implement `classify_scenes(llm_client, outline)` → list of scene types
- Implement `get_scene_prompt(scene_type)` → prompt fragment
- Test: classify various outlines

### Task 2: Style Injector
- Create `src/writer_agent/analysis/style_injector.py`
- Implement `build_style_injection(analysis, sample_passages)` → style prompt
- Integrate with `ChapterGenerator`: load style profile → inject
- Test: verify output prompt structure

### Task 3: Hierarchical Summaries
- DB migration: add `compact_summary`, `arc_summary` columns to chapters
- Implement `_generate_hierarchical_summaries(text)` in generator
- Update `ContextBuilder` to use arc/compact/detail hierarchy
- Test: verify 3-level summaries generated and stored

### Task 4: Plot State Machine
- DB: add `plot_states` table
- Create `src/writer_agent/engine/plot_state.py`
- Create `PlotStateRepo` in repositories
- Implement `_update_plot_state()` in generator (post-generation step)
- Update `ContextBuilder` to include plot state
- Test: verify state updates and retrieval

### Task 5: Integration — Prompt Assembler
- Create `src/writer_agent/engine/prompt_assembler.py`
- Orchestrates: scene prompt + style injection + plot state + context blocks
- Update `ChapterGenerator` to use PromptAssembler instead of inline assembly
- Full integration test

### Task 6: Tests + Verification
- Test all new components
- Run full suite
- Verify no regressions

---

## Data Flow Summary

```
1. User: writer-agent write "Роман" --outline "Елена входит в клуб"
2. classify_scenes(outline) → [{type: "opening", desc: "..."}, ...]
3. PromptAssembler:
   a. SYSTEM_WRITER
   b. + scene_prompt("opening")
   c. + style_injection(из профиля стиля)
   d. + plot_state(последнее состояние)
   e. + context_blocks(персонажи, арочные саммари, compact summaries)
4. LLM.generate(system, user, context)
5. Post-generation:
   a. _generate_hierarchical_summaries(text) → detail + compact + arc
   b. _update_plot_state(summary, previous_state) → new state
   c. Save: chapter + summaries + plot_state to DB
6. Output: "Глава 3 сгенерирована. 2400 слов."
```
