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
