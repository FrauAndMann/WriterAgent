"""Tests for Session Persistence — Milestone 5."""

import json
import pytest
from unittest.mock import MagicMock

from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, AgentSessionRepo
from writer_agent.engine.agent import AgentEngine


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
    mock = MagicMock()
    mock.chat.return_value = "Привет!"
    return mock


@pytest.fixture
def session_repo(db):
    return AgentSessionRepo(db)


# ── AgentSessionRepo CRUD ────────────────────────────────────────────────────


class TestAgentSessionRepo:
    def test_create_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        assert sid is not None
        assert isinstance(sid, int)

    def test_get_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session = session_repo.get(sid)
        assert session is not None
        assert session["id"] == sid
        assert session["project_id"] == project_id
        assert session["status"] == "active"
        assert session["input_tokens"] == 0

    def test_get_active_returns_latest(self, session_repo, project_id):
        sid1 = session_repo.create(project_id)
        sid2 = session_repo.create(project_id)
        active = session_repo.get_active(project_id)
        assert active["id"] == sid2

    def test_get_active_returns_none_if_all_paused(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.pause(sid)
        assert session_repo.get_active(project_id) is None

    def test_add_message(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.add_message(sid, "user", "Привет")
        session_repo.add_message(sid, "assistant", "Привет!")
        messages = session_repo.get_messages(sid)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Привет"
        assert messages[1]["role"] == "assistant"

    def test_update_tokens(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.update_tokens(sid, input_tokens=100, output_tokens=50)
        session = session_repo.get(sid)
        assert session["input_tokens"] == 100
        assert session["output_tokens"] == 50
        # Accumulate
        session_repo.update_tokens(sid, input_tokens=30, output_tokens=20)
        session = session_repo.get(sid)
        assert session["input_tokens"] == 130
        assert session["output_tokens"] == 70

    def test_pause_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.pause(sid)
        session = session_repo.get(sid)
        assert session["status"] == "paused"

    def test_complete_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.complete(sid)
        session = session_repo.get(sid)
        assert session["status"] == "completed"

    def test_list_by_project(self, session_repo, project_id):
        session_repo.create(project_id)
        session_repo.create(project_id)
        sessions = session_repo.list_by_project(project_id)
        assert len(sessions) == 2

    def test_get_nonexistent_session(self, session_repo):
        assert session_repo.get(999) is None

    def test_messages_persist_as_json(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.add_message(sid, "user", "Текст на русском")
        session_repo.add_message(sid, "assistant", "Ответ")
        session = session_repo.get(sid)
        raw_messages = json.loads(session["messages"])
        assert len(raw_messages) == 2
        assert raw_messages[0]["content"] == "Текст на русском"


# ── AgentEngine Session Integration ──────────────────────────────────────────


class TestAgentEngineSession:
    def test_engine_creates_session(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        assert engine.session_id is not None
        repo = AgentSessionRepo(db)
        session = repo.get(engine.session_id)
        assert session is not None
        assert session["status"] == "active"

    def test_engine_restores_session(self, db, llm, project_id):
        # Create and populate session
        repo = AgentSessionRepo(db)
        sid = repo.create(project_id)
        repo.add_message(sid, "user", "Первое сообщение")
        repo.add_message(sid, "assistant", "Первый ответ")

        # Restore
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id, session_id=sid)
        assert len(engine.history) == 2
        assert engine.history[0]["content"] == "Первое сообщение"
        assert engine.session_id == sid

    def test_chat_saves_messages_to_db(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.chat("Привет")

        repo = AgentSessionRepo(db)
        messages = repo.get_messages(engine.session_id)
        assert len(messages) >= 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Привет"

    def test_pause_session(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.pause_session()
        repo = AgentSessionRepo(db)
        session = repo.get(engine.session_id)
        assert session["status"] == "paused"

    def test_complete_session(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.complete_session()
        repo = AgentSessionRepo(db)
        session = repo.get(engine.session_id)
        assert session["status"] == "completed"

    def test_get_session_stats(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.chat("Тест")

        stats = engine.get_session_stats()
        assert stats["messages"] >= 2
        assert stats["input_tokens"] > 0
        assert stats["output_tokens"] > 0
        assert stats["status"] == "active"

    def test_resume_and_continue(self, db, project_id):
        # Session 1: send message
        llm1 = MagicMock()
        llm1.chat.return_value = "Первый ответ"
        engine1 = AgentEngine(db=db, llm_client=llm1, project_id=project_id)
        engine1.chat("Сообщение 1")
        sid = engine1.session_id
        engine1.pause_session()

        # Session 2: resume
        llm2 = MagicMock()
        llm2.chat.return_value = "Второй ответ"
        engine2 = AgentEngine(db=db, llm_client=llm2, project_id=project_id, session_id=sid)
        assert len(engine2.history) >= 2
        engine2.chat("Сообщение 2")

        repo = AgentSessionRepo(db)
        messages = repo.get_messages(sid)
        # Should have: user1, assistant1, user2, assistant2
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) >= 2

    def test_tool_call_saves_results_to_db(self, db, project_id):
        llm = MagicMock()
        llm.chat.side_effect = [
            'Создаю.\n```tool\n{"name": "create_character", "args": {"name": "Елена"}}\n```\n',
            "Готово!",
        ]
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.chat("Создай персонажа")

        repo = AgentSessionRepo(db)
        messages = repo.get_messages(engine.session_id)
        # user + assistant(tool) + user(result) + assistant(final)
        assert len(messages) >= 3
        assert any("create_character" in m["content"] for m in messages)

    def test_multiple_sessions_same_project(self, db, llm, project_id):
        repo = AgentSessionRepo(db)
        # Create 3 sessions
        s1 = repo.create(project_id)
        repo.add_message(s1, "user", "S1 msg")
        repo.pause(s1)

        s2 = repo.create(project_id)
        repo.add_message(s2, "user", "S2 msg")

        s3 = repo.create(project_id)
        repo.add_message(s3, "user", "S3 msg")

        # get_active should return latest active (s3)
        active = repo.get_active(project_id)
        assert active["id"] == s3

        # list should return all
        sessions = repo.list_by_project(project_id)
        assert len(sessions) == 3
