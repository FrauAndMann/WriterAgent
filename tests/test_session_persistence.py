"""Tests for Session Persistence + State Machine — Milestone 5."""

import json
import pytest
from unittest.mock import MagicMock

from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, AgentSessionRepo
from writer_agent.engine.agent import AgentEngine
from writer_agent.engine.session_state import SessionState


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


# ── SessionState Enum ─────────────────────────────────────────────────────────


class TestSessionState:
    def test_all_states_defined(self):
        assert SessionState.SPAWNING.value == "spawning"
        assert SessionState.READY.value == "ready"
        assert SessionState.RUNNING.value == "running"
        assert SessionState.WAITING.value == "waiting"
        assert SessionState.PAUSED.value == "paused"
        assert SessionState.COMPLETED.value == "completed"

    def test_completed_is_terminal(self):
        assert SessionState.COMPLETED.is_terminal() is True
        assert SessionState.SPAWNING.is_terminal() is False

    def test_valid_transitions_from_spawning(self):
        assert SessionState.SPAWNING.can_transition(SessionState.READY) is True
        assert SessionState.SPAWNING.can_transition(SessionState.RUNNING) is False

    def test_valid_transitions_from_ready(self):
        assert SessionState.READY.can_transition(SessionState.RUNNING) is True
        assert SessionState.READY.can_transition(SessionState.PAUSED) is True
        assert SessionState.READY.can_transition(SessionState.WAITING) is False

    def test_valid_transitions_from_running(self):
        assert SessionState.RUNNING.can_transition(SessionState.WAITING) is True
        assert SessionState.RUNNING.can_transition(SessionState.PAUSED) is True
        assert SessionState.RUNNING.can_transition(SessionState.READY) is False

    def test_valid_transitions_from_waiting(self):
        assert SessionState.WAITING.can_transition(SessionState.RUNNING) is True
        assert SessionState.WAITING.can_transition(SessionState.PAUSED) is True
        assert SessionState.WAITING.can_transition(SessionState.COMPLETED) is True

    def test_valid_transitions_from_paused(self):
        assert SessionState.PAUSED.can_transition(SessionState.READY) is True
        assert SessionState.PAUSED.can_transition(SessionState.RUNNING) is False

    def test_completed_is_dead_end(self):
        assert SessionState.COMPLETED.can_transition(SessionState.READY) is False
        assert SessionState.COMPLETED.can_transition(SessionState.RUNNING) is False

    def test_full_lifecycle(self):
        """spawning → ready → running → waiting → paused → ready → running → waiting → completed"""
        states = [
            SessionState.SPAWNING,
            SessionState.READY,
            SessionState.RUNNING,
            SessionState.WAITING,
            SessionState.PAUSED,
            SessionState.READY,
            SessionState.RUNNING,
            SessionState.WAITING,
            SessionState.COMPLETED,
        ]
        for i in range(len(states) - 1):
            assert states[i].can_transition(states[i + 1]), \
                f"{states[i].value} -> {states[i+1].value} should be valid"


# ── AgentSessionRepo CRUD ────────────────────────────────────────────────────


class TestAgentSessionRepo:
    def test_create_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        assert sid is not None
        assert isinstance(sid, int)

    def test_create_session_has_spawning_status(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session = session_repo.get(sid)
        assert session["status"] == "spawning"

    def test_get_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session = session_repo.get(sid)
        assert session is not None
        assert session["id"] == sid
        assert session["project_id"] == project_id
        assert session["input_tokens"] == 0

    def test_get_active_returns_resumable(self, session_repo, project_id):
        """get_active finds sessions in ready, waiting, or paused states."""
        sid1 = session_repo.create(project_id)
        session_repo.set_state(sid1, "ready")
        sid2 = session_repo.create(project_id)
        session_repo.set_state(sid2, "waiting")
        active = session_repo.get_active(project_id)
        assert active["id"] == sid2  # most recent

    def test_get_active_skips_completed(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.set_state(sid, "completed")
        assert session_repo.get_active(project_id) is None

    def test_get_active_skips_spawning(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        # spawning is NOT resumable
        assert session_repo.get_active(project_id) is None

    def test_set_state(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.set_state(sid, "ready")
        session = session_repo.get(sid)
        assert session["status"] == "ready"

    def test_add_message(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.add_message(sid, "user", "Привет")
        session_repo.add_message(sid, "assistant", "Привет!")
        messages = session_repo.get_messages(sid)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Привет"

    def test_update_tokens_accumulates(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.update_tokens(sid, input_tokens=100, output_tokens=50)
        session = session_repo.get(sid)
        assert session["input_tokens"] == 100
        assert session["output_tokens"] == 50
        session_repo.update_tokens(sid, input_tokens=30, output_tokens=20)
        session = session_repo.get(sid)
        assert session["input_tokens"] == 130
        assert session["output_tokens"] == 70

    def test_pause_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.pause(sid)
        assert session_repo.get(sid)["status"] == "paused"

    def test_complete_session(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.complete(sid)
        assert session_repo.get(sid)["status"] == "completed"

    def test_list_by_project(self, session_repo, project_id):
        session_repo.create(project_id)
        session_repo.create(project_id)
        sessions = session_repo.list_by_project(project_id)
        assert len(sessions) == 2

    def test_get_nonexistent_session(self, session_repo):
        assert session_repo.get(999) is None

    def test_messages_persist_russian_text(self, session_repo, project_id):
        sid = session_repo.create(project_id)
        session_repo.add_message(sid, "user", "Текст на русском")
        session_repo.add_message(sid, "assistant", "Ответ")
        session = session_repo.get(sid)
        raw_messages = json.loads(session["messages"])
        assert raw_messages[0]["content"] == "Текст на русском"


# ── AgentEngine State Machine Integration ─────────────────────────────────────


class TestAgentEngineStateMachine:
    def test_engine_starts_in_ready(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        assert engine.state == SessionState.READY
        repo = AgentSessionRepo(db)
        session = repo.get(engine.session_id)
        assert session["status"] == "ready"

    def test_engine_chat_transitions(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        assert engine.state == SessionState.READY
        engine.chat("Привет")
        assert engine.state == SessionState.WAITING

    def test_engine_pause_transitions(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.pause_session()
        assert engine.state == SessionState.PAUSED
        repo = AgentSessionRepo(db)
        assert repo.get(engine.session_id)["status"] == "paused"

    def test_engine_complete_transitions(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.complete_session()
        assert engine.state == SessionState.COMPLETED

    def test_engine_restores_session(self, db, llm, project_id):
        repo = AgentSessionRepo(db)
        sid = repo.create(project_id)
        repo.add_message(sid, "user", "Первое сообщение")
        repo.add_message(sid, "assistant", "Первый ответ")
        repo.set_state(sid, "paused")

        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id, session_id=sid)
        assert engine.state == SessionState.READY
        assert len(engine.history) == 2

    def test_engine_chat_saves_to_db(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.chat("Привет")
        repo = AgentSessionRepo(db)
        messages = repo.get_messages(engine.session_id)
        assert len(messages) >= 2
        assert messages[0]["role"] == "user"

    def test_engine_get_session_stats(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.chat("Тест")
        stats = engine.get_session_stats()
        assert stats["messages"] >= 2
        assert stats["input_tokens"] > 0
        assert stats["state"] == "waiting"

    def test_resume_and_continue(self, db, project_id):
        llm1 = MagicMock()
        llm1.chat.return_value = "Первый ответ"
        engine1 = AgentEngine(db=db, llm_client=llm1, project_id=project_id)
        engine1.chat("Сообщение 1")
        sid = engine1.session_id
        engine1.pause_session()

        # Resume
        llm2 = MagicMock()
        llm2.chat.return_value = "Второй ответ"
        engine2 = AgentEngine(db=db, llm_client=llm2, project_id=project_id, session_id=sid)
        assert engine2.state == SessionState.READY
        engine2.chat("Сообщение 2")
        assert engine2.state == SessionState.WAITING

        repo = AgentSessionRepo(db)
        messages = repo.get_messages(sid)
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) >= 2

    def test_tool_call_saves_results(self, db, project_id):
        llm = MagicMock()
        llm.chat.side_effect = [
            'Создаю.\n```tool\n{"name": "create_character", "args": {"name": "Елена"}}\n```\n',
            "Готово!",
        ]
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.chat("Создай персонажа")

        repo = AgentSessionRepo(db)
        messages = repo.get_messages(engine.session_id)
        assert len(messages) >= 3
        assert any("create_character" in m["content"] for m in messages)
        assert engine.state == SessionState.WAITING

    def test_invalid_transition_raises(self, db, llm, project_id):
        engine = AgentEngine(db=db, llm_client=llm, project_id=project_id)
        engine.complete_session()
        with pytest.raises(ValueError, match="Invalid state transition"):
            engine._transition(SessionState.RUNNING)

    def test_multiple_sessions_same_project(self, db, llm, project_id):
        repo = AgentSessionRepo(db)
        s1 = repo.create(project_id)
        repo.set_state(s1, "ready")
        repo.pause(s1)

        s2 = repo.create(project_id)
        repo.set_state(s2, "waiting")

        s3 = repo.create(project_id)
        repo.set_state(s3, "ready")

        active = repo.get_active(project_id)
        assert active["id"] == s3  # most recent resumable

        sessions = repo.list_by_project(project_id)
        assert len(sessions) == 3
