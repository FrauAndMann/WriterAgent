"""Tests for Milestone 4: Interactive Agent."""

import json
import pytest
from unittest.mock import MagicMock

from writer_agent.db.database import Database
from writer_agent.db.repositories import ProjectRepo, CharacterRepo, ChapterRepo, PlotStateRepo
from writer_agent.engine.agent import AgentEngine
from writer_agent.engine.agent_tools import build_tool_registry, ToolDef
from writer_agent.llm.prompts import build_system_agent


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
def agent(db, llm, project_id):
    return AgentEngine(db=db, llm_client=llm, project_id=project_id)


# ── Tool Registry ────────────────────────────────────────────────────────────


class TestToolRegistry:
    def test_registry_has_all_tools(self):
        registry = build_tool_registry()
        expected = {
            "create_character", "create_plot_thread", "create_world_element",
            "create_relationship", "list_characters", "list_plot_threads",
            "show_chapter", "show_project_status", "show_plot_state",
            "write_chapter", "revise_chapter", "export_novel", "save_note",
        }
        assert set(registry.keys()) == expected

    def test_tool_has_prompt_text(self):
        registry = build_tool_registry()
        for name, tool in registry.items():
            text = tool.to_prompt_text()
            assert name in text
            assert isinstance(text, str)

    def test_tool_def_structure(self):
        registry = build_tool_registry()
        for name, tool in registry.items():
            assert isinstance(tool, ToolDef)
            assert tool.name == name
            assert isinstance(tool.description, str)
            assert callable(tool.fn)


# ── Tool Execution ───────────────────────────────────────────────────────────


class TestToolExecution:
    def test_create_character(self, db, project_id):
        registry = build_tool_registry()
        result = registry["create_character"].fn(
            db=db, project_id=project_id,
            name="Елена", description="Тёмные волосы, бледная кожа",
            personality="Холодная, расчётливая",
        )
        assert result["success"] is True
        assert result["name"] == "Елена"
        # Verify in DB
        chars = CharacterRepo(db).list_by_project(project_id)
        assert len(chars) == 1
        assert chars[0]["name"] == "Елена"

    def test_create_plot_thread(self, db, project_id):
        registry = build_tool_registry()
        result = registry["create_plot_thread"].fn(
            db=db, project_id=project_id,
            name="Vendetta", description="Кровная месть",
            importance=8,
        )
        assert result["success"] is True

    def test_create_world_element(self, db, project_id):
        registry = build_tool_registry()
        result = registry["create_world_element"].fn(
            db=db, project_id=project_id,
            name="Клуб Валентини", category="location",
            description="Подземный клуб для вампиров",
        )
        assert result["success"] is True

    def test_create_relationship(self, db, project_id):
        CharacterRepo(db).create(project_id=project_id, name="Елена")
        CharacterRepo(db).create(project_id=project_id, name="Данте")
        registry = build_tool_registry()
        result = registry["create_relationship"].fn(
            db=db, project_id=project_id,
            char_a="Елена", char_b="Данте",
            type="enemies-to-lovers",
        )
        assert result["success"] is True

    def test_list_characters(self, db, project_id):
        CharacterRepo(db).create(project_id=project_id, name="Елена", description="Бледная")
        CharacterRepo(db).create(project_id=project_id, name="Данте", description="Мафия")
        registry = build_tool_registry()
        result = registry["list_characters"].fn(db=db, project_id=project_id)
        assert len(result["characters"]) == 2
        assert result["characters"][0]["name"] == "Елена"

    def test_show_project_status(self, db, project_id):
        CharacterRepo(db).create(project_id=project_id, name="Елена")
        ChapterRepo(db).create(project_id=project_id, chapter_number=1, full_text="Слова " * 100)
        registry = build_tool_registry()
        result = registry["show_project_status"].fn(db=db, project_id=project_id)
        assert result["chapters"] == 1
        assert result["characters"] == 1

    def test_save_note(self, db, project_id):
        registry = build_tool_registry()
        result = registry["save_note"].fn(
            db=db, project_id=project_id,
            title="Идея для финала",
            content="Данте жертвует собой ради Елены",
        )
        assert result["success"] is True


# ── Agent Engine ──────────────────────────────────────────────────────────────


class TestAgentEngine:
    def test_agent_parses_tool_calls(self, agent):
        response = 'Сейчас создам персонажа.\n```tool\n{"name": "create_character", "args": {"name": "Елена"}}\n```\nГотово!'
        calls = agent._parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0]["name"] == "create_character"
        assert calls[0]["args"]["name"] == "Елена"

    def test_agent_parses_multiple_tool_calls(self, agent):
        response = (
            '```tool\n{"name": "create_character", "args": {"name": "Елена"}}\n```\n'
            'И второго:\n'
            '```tool\n{"name": "create_character", "args": {"name": "Данте"}}\n```\n'
        )
        calls = agent._parse_tool_calls(response)
        assert len(calls) == 2

    def test_agent_parses_no_tool_calls(self, agent):
        response = "Привет! Чем могу помочь?"
        calls = agent._parse_tool_calls(response)
        assert calls == []

    def test_agent_executes_tool(self, agent):
        result = agent._execute_tool("create_character", {"name": "Маркус", "description": "Вампир"})
        assert result["success"] is True

    def test_agent_unknown_tool_returns_error(self, agent):
        result = agent._execute_tool("nonexistent_tool", {})
        assert "error" in result

    def test_agent_chat_text_only(self, agent, llm):
        llm.chat.return_value = "Привет! Давай создадим твой роман."
        response = agent.chat("Привет")
        assert "Привет" in response

    def test_agent_chat_with_tool(self, agent, llm):
        # First LLM response: calls tool
        llm.chat.return_value = (
            'Создаю персонажа.\n```tool\n{"name": "create_character", "args": {"name": "Елена"}}\n```\n'
        )
        # This triggers tool execution, then feeds result back
        # The agent sends another message to LLM
        # We need chat to be called twice
        llm.chat.side_effect = [
            'Создаю персонажа.\n```tool\n{"name": "create_character", "args": {"name": "Елена"}}\n```\n',
            'Персонаж Елена создан! Отличное имя для тёмной героини.',
        ]
        response = agent.chat("Создай персонажа Елена")
        assert "Елена" in response

    def test_agent_history_trimming(self, agent, llm):
        llm.chat.return_value = "ok"
        # Add many messages to test trimming
        for i in range(25):
            agent.chat(f"Message {i}")
        assert len(agent.history) <= AgentEngine.MAX_HISTORY * 2 + 5

    def test_agent_clean_response(self, agent):
        response = "Some text\n```tool\n{\"name\": \"test\"}\n```\nMore text\n```result\n{\"ok\": true}\n```\n"
        cleaned = agent._clean_response(response)
        assert "Some text" in cleaned
        assert "More text" in cleaned
        assert "```tool" not in cleaned
        assert "```result" not in cleaned


# ── System Prompt ────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_builds_agent_prompt(self):
        tools_prompt = "### create_character\nCreate a character"
        prompt = build_system_agent(tools_prompt)
        assert "create_character" in prompt
        assert "tool" in prompt.lower()
        assert len(prompt) > 200

    def test_prompt_includes_all_tools(self):
        registry = build_tool_registry()
        tools_text = "\n\n".join(t.to_prompt_text() for t in registry.values())
        prompt = build_system_agent(tools_text)
        for name in registry:
            assert name in prompt
