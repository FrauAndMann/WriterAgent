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
