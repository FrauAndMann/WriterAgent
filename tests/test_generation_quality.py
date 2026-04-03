"""Tests for Milestone 3: Generation Quality components."""

import json
import pytest
from unittest.mock import MagicMock

from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, ChapterRepo, PlotStateRepo, StyleProfileRepo,
)
from writer_agent.engine.context import ContextBuilder
from writer_agent.engine.generator import ChapterGenerator
from writer_agent.engine.prompt_assembler import PromptAssembler
from writer_agent.engine.plot_state import PlotState, empty_plot_state
from writer_agent.llm.scene_prompts import (
    get_scene_prompt, classify_scenes, SCENE_PROMPTS, SCENE_TYPES,
)
from writer_agent.analysis.style_injector import build_style_injection


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    return database


@pytest.fixture
def project_id(db):
    return ProjectRepo(db).create(name="Test Novel", genre="dark romance")


@pytest.fixture
def llm():
    return MagicMock()


@pytest.fixture
def assembler():
    return PromptAssembler()


# ── Scene Prompts ─────────────────────────────────────────────────────────────


class TestScenePrompts:
    def test_all_scene_types_have_prompts(self):
        for stype in SCENE_TYPES:
            assert get_scene_prompt(stype), f"Missing prompt for {stype}"

    def test_unknown_type_returns_empty(self):
        assert get_scene_prompt("nonexistent") == ""

    def test_scene_prompts_are_strings(self):
        for stype, prompt in SCENE_PROMPTS.items():
            assert isinstance(prompt, str)
            assert len(prompt) > 20

    def test_classify_scenes_parses_response(self, llm):
        llm.generate.return_value = (
            "1. [opening] — Елена входит в клуб (Елена)\n"
            "2. [dialogue] — Разговор с барменом (Елена, Бармен)\n"
            "3. [erotic] — Взгляд Данте (Елена, Данте)\n"
        )
        scenes = classify_scenes(llm, "Елена входит в тёмный клуб")
        assert len(scenes) >= 2
        assert scenes[0]["type"] in SCENE_TYPES

    def test_classify_scenes_handles_empty_response(self, llm):
        llm.generate.return_value = ""
        scenes = classify_scenes(llm, "empty outline")
        assert scenes == []


# ── Style Injector ────────────────────────────────────────────────────────────


class TestStyleInjector:
    def test_builds_rhythm_instruction_long(self):
        result = build_style_injection({"avg_sentence_length": 25})
        assert "длинные" in result.lower() or "плавные" in result.lower()

    def test_builds_rhythm_instruction_medium(self):
        result = build_style_injection({"avg_sentence_length": 15})
        assert "средние" in result.lower()

    def test_builds_rhythm_instruction_short(self):
        result = build_style_injection({"avg_sentence_length": 8})
        assert "короткие" in result.lower() or "рубленые" in result.lower()

    def test_builds_pov_first_person(self):
        result = build_style_injection({"pov_style": "first_person"})
        assert "первое лицо" in result

    def test_builds_pov_third_person(self):
        result = build_style_injection({"pov_style": "third_person"})
        assert "третье лицо" in result

    def test_builds_dialogue_ratio(self):
        result = build_style_injection({"dialogue_ratio": 0.4})
        assert "40%" in result

    def test_builds_vocabulary_signature(self):
        result = build_style_injection({
            "frequent_words": ["тьма", "взгляд", "кожа", "кровь"],
        })
        assert "тьма" in result
        assert "кровь" in result

    def test_includes_sample_passages(self):
        passages = ["Длинный текст первого пассажа для тестирования стиля " * 5]
        result = build_style_injection({}, sample_passages=passages)
        assert "Образцы стиля" in result

    def test_empty_analysis_produces_header(self):
        result = build_style_injection({})
        assert "Стиль автора" in result


# ── Hierarchical Summaries ────────────────────────────────────────────────────


class TestHierarchicalSummaries:
    def test_chapter_repo_stores_compact_and_arc(self, db, project_id):
        ch_id = ChapterRepo(db).create(
            project_id=project_id,
            chapter_number=1,
            title="Ch1",
            summary="Detailed summary here.",
            compact_summary="Elena meets Dante.",
            arc_summary="First encounter — spark and danger.",
            full_text="Full chapter text...",
        )
        ch = ChapterRepo(db).get(ch_id)
        assert ch["compact_summary"] == "Elena meets Dante."
        assert ch["arc_summary"] == "First encounter — spark and danger."

    def test_chapter_repo_update_summaries(self, db, project_id):
        ch_id = ChapterRepo(db).create(
            project_id=project_id, chapter_number=1, full_text="text"
        )
        ChapterRepo(db).update_summaries(
            ch_id,
            summary="Detail",
            compact_summary="Compact",
            arc_summary="Arc",
        )
        ch = ChapterRepo(db).get(ch_id)
        assert ch["summary"] == "Detail"
        assert ch["compact_summary"] == "Compact"
        assert ch["arc_summary"] == "Arc"

    def test_generator_generates_three_level_summaries(self, db, project_id, llm):
        # Mock LLM to return different things per call
        llm.generate.side_effect = [
            "Chapter text generated.",  # main chapter generation
            "Detailed summary of chapter.",  # detail summary
            "Compact summary.",  # compact summary
            "Arc function.",  # arc summary
            '{"conflicts":[]}',  # plot state update (may not be called)
        ]
        ctx = ContextBuilder(db, max_tokens=2000)
        gen = ChapterGenerator(db=db, llm_client=llm, context_builder=ctx)
        result = gen.generate_chapter(project_id=project_id, chapter_number=1)
        assert "summaries" in result
        assert "detail" in result["summaries"]
        assert "compact" in result["summaries"]
        assert "arc" in result["summaries"]

    def test_hierarchical_summaries_fallback(self, db, project_id, llm):
        llm.generate.side_effect = Exception("LLM down")
        ctx = ContextBuilder(db, max_tokens=2000)
        gen = ChapterGenerator(db=db, llm_client=llm, context_builder=ctx)
        text = "Текст главы для тестирования fallback " * 100
        summaries = gen._generate_hierarchical_summaries(text)
        assert len(summaries["detail"]) > 0
        assert len(summaries["compact"]) > 0
        assert len(summaries["arc"]) > 0


# ── Plot State Machine ────────────────────────────────────────────────────────


class TestPlotState:
    def test_plot_state_dataclass(self):
        state = PlotState(
            conflicts=[{"name": "Vendetta", "intensity": 8}],
            tone="rising_tension",
        )
        assert state.tone == "rising_tension"
        assert len(state.conflicts) == 1

    def test_plot_state_serialization(self):
        state = empty_plot_state()
        d = state.to_dict()
        restored = PlotState.from_dict(d)
        assert restored.tone == state.tone
        assert restored.conflicts == state.conflicts

    def test_plot_state_repo_create_and_get(self, db, project_id):
        repo = PlotStateRepo(db)
        state = {"conflicts": [{"name": "Revenge"}], "tone": "climax"}
        repo.create(project_id, chapter_number=1, state=state)

        latest = repo.get_latest(project_id)
        assert latest is not None
        loaded = json.loads(latest["state"])
        assert loaded["conflicts"][0]["name"] == "Revenge"

    def test_plot_state_repo_latest_returns_highest_chapter(self, db, project_id):
        repo = PlotStateRepo(db)
        repo.create(project_id, 1, {"tone": "rising"})
        repo.create(project_id, 5, {"tone": "climax"})

        latest = repo.get_latest(project_id)
        loaded = json.loads(latest["state"])
        assert loaded["tone"] == "climax"

    def test_plot_state_repo_list_by_project(self, db, project_id):
        repo = PlotStateRepo(db)
        repo.create(project_id, 1, {"tone": "a"})
        repo.create(project_id, 2, {"tone": "b"})
        states = repo.list_by_project(project_id)
        assert len(states) == 2


# ── Prompt Assembler ──────────────────────────────────────────────────────────


class TestPromptAssembler:
    def test_assembles_basic_prompt(self, assembler):
        result = assembler.assemble(outline="Elena enters club", chapter_number=3)
        assert "Напиши главу 3" in result["user"]
        assert "Elena enters club" in result["user"]

    def test_includes_scene_prompts(self, assembler):
        result = assembler.assemble(scene_types=["dialogue", "erotic"])
        assert "Диалог-сцена" in result["system"]
        assert "Откровенная" in result["system"] or "эрот" in result["system"].lower()

    def test_includes_style_instructions(self, assembler):
        style = "Пиши короткими фразами. Много метафор."
        result = assembler.assembler(style_instructions=style) if False else \
            assembler.assemble(style_instructions=style)
        assert style in result["system"]

    def test_includes_plot_state_block(self, assembler):
        plot_block = "[Состояние сюжета]\nКонфликты: Вендетта (инт. 8)"
        result = assembler.assemble(plot_state_block=plot_block)
        assert "Вендетта" in result["system"]

    def test_target_words_in_user_prompt(self, assembler):
        result = assembler.assemble(target_words=5000)
        assert "5000" in result["user"]


# ── Context Builder Integration ───────────────────────────────────────────────


class TestContextBuilderIntegration:
    def test_includes_plot_state_block(self, db, project_id):
        # Create plot state
        PlotStateRepo(db).create(project_id, 1, {
            "conflicts": [{"name": "Vendetta", "parties": "Elena vs Dante",
                           "intensity": 8, "status": "active"}],
            "character_arcs": [{"character": "Elena", "current_state": "angry"}],
            "tone": "rising_tension",
        })
        builder = ContextBuilder(db, max_tokens=4000)
        context = builder.build(project_id=project_id, current_chapter=2)
        full = "\n".join(context["blocks"])
        assert "Vendetta" in full
        assert "Elena" in full

    def test_arc_summaries_for_all_chapters(self, db, project_id):
        for i in range(1, 11):
            ChapterRepo(db).create(
                project_id=project_id, chapter_number=i,
                title=f"Ch{i}",
                summary=f"Detail of chapter {i}.",
                compact_summary=f"Compact of ch{i}.",
                arc_summary=f"Arc ch{i}.",
                full_text=f"Text {i}...",
            )
        builder = ContextBuilder(db, max_tokens=6000)
        context = builder.build(project_id=project_id, current_chapter=11)
        full = "\n".join(context["blocks"])
        assert "Арка романа" in full
        # Should have multiple arc summaries
        assert "Arc ch1" in full

    def test_compact_summaries_for_recent_chapters(self, db, project_id):
        for i in range(1, 8):
            ChapterRepo(db).create(
                project_id=project_id, chapter_number=i,
                compact_summary=f"Compact of ch{i}.",
                full_text=f"Text {i}...",
            )
        builder = ContextBuilder(db, max_tokens=4000)
        context = builder.build(project_id=project_id, current_chapter=8)
        full = "\n".join(context["blocks"])
        assert "Последние главы" in full


# ── DB Migration ──────────────────────────────────────────────────────────────


class TestMigration:
    def test_migration_adds_columns_to_existing_db(self, tmp_path):
        db = Database(tmp_path / "test.db")
        # Initialize with schema (simulates existing DB)
        db.initialize()
        # Run migration — should not fail
        db.migrate()
        # Verify columns exist by inserting
        proj_id = ProjectRepo(db).create(name="Test")
        ch_id = ChapterRepo(db).create(
            project_id=proj_id, chapter_number=1,
            compact_summary="test compact",
            arc_summary="test arc",
        )
        ch = ChapterRepo(db).get(ch_id)
        assert ch["compact_summary"] == "test compact"
        assert ch["arc_summary"] == "test arc"
