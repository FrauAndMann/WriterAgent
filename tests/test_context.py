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
                           compact_summary="Elena and Dante meet.",
                           arc_summary="First encounter.",
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
    assert "They met" in full_context  # detail summary from ch1


def test_build_context_truncates_when_needed(populated_db):
    db, proj_id = populated_db
    builder = ContextBuilder(db, max_tokens=100)  # very small
    context = builder.build(project_id=proj_id, current_chapter=2)
    assert context["total_tokens"] <= 100 + 50  # small margin


def test_build_context_hierarchical_summaries(populated_db):
    db, proj_id = populated_db
    # Add chapters with hierarchical summaries
    for i in range(2, 7):
        ChapterRepo(db).create(
            project_id=proj_id, chapter_number=i,
            title=f"Ch{i}", summary=f"Detail summary of chapter {i}.",
            compact_summary=f"Compact of chapter {i}.",
            arc_summary=f"Arc function of chapter {i}.",
            full_text=f"Full text of chapter {i}...",
        )
    builder = ContextBuilder(db, max_tokens=4000)
    context = builder.build(project_id=proj_id, current_chapter=7)
    full_context = "\n".join(context["blocks"])
    # Should include arc summaries block
    assert "Арка романа" in full_context
    # Should include compact summaries block
    assert "Последние главы" in full_context
    assert "Compact of chapter" in full_context
    # Detail summary of previous chapter
    assert "Detail summary of chapter 6" in full_context
