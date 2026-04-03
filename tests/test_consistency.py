import pytest
from writer_agent.engine.consistency import ConsistencyChecker
from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, PlotThreadRepo, RelationshipRepo,
)


@pytest.fixture
def setup(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    proj_id = ProjectRepo(db).create(name="Test", genre="dark romance")
    return db, proj_id


def test_detect_dead_character_inconsistency(setup):
    db, proj_id = setup
    char_id = CharacterRepo(db).create(
        project_id=proj_id, name="Viktor",
        description="Dead villain", personality="evil",
    )
    CharacterRepo(db).update(char_id, status="dead")
    checker = ConsistencyChecker(db)
    warnings = checker.check(
        project_id=proj_id,
        outline="Viktor enters the room and threatens Elena.",
    )
    assert any("Viktor" in w and "мёртв" in w.lower() for w in warnings)


def test_detect_resolved_thread_inconsistency(setup):
    db, proj_id = setup
    PlotThreadRepo(db).create(
        project_id=proj_id, name="Murder mystery",
        description="Who killed the boss?", status="resolved",
    )
    checker = ConsistencyChecker(db)
    warnings = checker.check(
        project_id=proj_id,
        outline="The murder mystery deepens as new evidence appears.",
    )
    assert any("Murder mystery" in w for w in warnings)


def test_no_warnings_for_consistent_outline(setup):
    db, proj_id = setup
    CharacterRepo(db).create(
        project_id=proj_id, name="Elena",
        description="Heroine", personality="strong",
    )
    PlotThreadRepo(db).create(
        project_id=proj_id, name="Revenge",
        description="Elena gets revenge", status="active",
    )
    checker = ConsistencyChecker(db)
    warnings = checker.check(
        project_id=proj_id,
        outline="Elena plans her revenge against the mafia.",
    )
    assert len(warnings) == 0
