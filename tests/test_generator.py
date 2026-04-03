import pytest
from unittest.mock import MagicMock
from writer_agent.engine.generator import ChapterGenerator
from writer_agent.engine.context import ContextBuilder
from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, CharacterRepo, ChapterRepo, StyleProfileRepo


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
    # generate is called twice: summary + chapter. Check all calls for style_prompt.
    all_calls = str(llm.generate.call_args_list)
    assert style_prompt in all_calls


def test_generate_summary_with_llm(setup):
    gen, db, proj_id, llm = setup
    llm.generate.return_value = "Елена встречает Данте в клубе. Возникает напряжение."
    summary = gen._call_summary_llm("Длинный текст главы на тысячи слов...", "detail")
    assert "Елена" in summary


def test_generate_summary_fallback_on_llm_error(setup):
    gen, db, proj_id, llm = setup
    llm.generate.side_effect = Exception("LLM unavailable")
    text = "Короткий текст для fallback теста."
    summaries = gen._generate_hierarchical_summaries(text)
    assert len(summaries["detail"]) > 0  # should not crash
    assert "compact" in summaries
    assert "arc" in summaries


def test_style_profile_auto_loaded_from_db(setup):
    gen, db, proj_id, llm = setup
    # Save a style profile to DB
    StyleProfileRepo(db).create(
        name="test_style",
        analysis={
            "avg_sentence_length": 14.5,
            "pov_style": "third_person",
            "dialogue_ratio": 0.35,
            "frequent_words": ["тьма", "взгляд", "кожа"],
        },
    )
    llm.generate.return_value = "Стилизованный текст."

    # Generate WITHOUT explicit style_instructions — should auto-load from DB
    result = gen.generate_chapter(project_id=proj_id, chapter_number=1)
    all_calls = str(llm.generate.call_args_list)
    assert "Стиль автора" in all_calls
    assert "тьма" in all_calls
