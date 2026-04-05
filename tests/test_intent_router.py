"""Tests for the token-based intent router."""

import pytest

from writer_agent.engine.agent_tools import ToolDef, build_tool_registry
from writer_agent.engine.intent_router import IntentRouter, RouteMatch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tools():
    return build_tool_registry()


@pytest.fixture
def router(tools):
    return IntentRouter(tools)


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_simple_split(self):
        tokens = IntentRouter._tokenize("покажи персонажей")
        assert "покажи" in tokens
        assert "персонажей" in tokens

    def test_compound_tokens(self):
        tokens = IntentRouter._tokenize("покажи персонажей")
        assert "покажи персонажей" in tokens

    def test_punctuation_stripped(self):
        tokens = IntentRouter._tokenize("покажи, персонажей!")
        assert "покажи" in tokens
        assert "персонажей" in tokens

    def test_empty_string(self):
        assert IntentRouter._tokenize("") == []

    def test_english_tokens(self):
        tokens = IntentRouter._tokenize("show characters list")
        assert "show" in tokens
        assert "characters" in tokens


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

class TestRoute:
    def test_list_characters_russian(self, router):
        matches = router.route("покажи персонажей")
        assert len(matches) > 0
        assert matches[0].tool_name == "list_characters"

    def test_list_characters_english(self, router):
        matches = router.route("list all characters")
        assert len(matches) > 0
        assert matches[0].tool_name == "list_characters"

    def test_write_chapter_russian(self, router):
        matches = router.route("написать новую главу")
        assert len(matches) > 0
        assert matches[0].tool_name == "write_chapter"

    def test_export_novel(self, router):
        matches = router.route("экспорт в docx")
        assert len(matches) > 0
        assert matches[0].tool_name == "export_novel"

    def test_show_project_status(self, router):
        matches = router.route("статус проекта")
        assert len(matches) > 0
        assert matches[0].tool_name == "show_project_status"

    def test_gibberish_returns_empty(self, router):
        matches = router.route("xyzzy foo bar baz")
        assert len(matches) == 0

    def test_limit_works(self, router):
        matches = router.route("покажи персонажей", limit=1)
        assert len(matches) <= 1

    def test_empty_prompt_returns_empty(self, router):
        assert router.route("") == []


# ---------------------------------------------------------------------------
# best_match
# ---------------------------------------------------------------------------

class TestBestMatch:
    def test_confident_match(self, router):
        match = router.best_match("покажи персонажей")
        assert match is not None
        assert match.tool_name == "list_characters"
        assert match.score >= 2

    def test_too_low_score(self, router):
        # Single generic word unlikely to match anything well
        match = router.best_match("хочу")
        assert match is None

    def test_no_match(self, router):
        match = router.best_match("расскажи сказку про дракона")
        # "расскажи" doesn't match any tool keywords well enough
        assert match is None or match.score < 2

    def test_min_score_threshold(self, router):
        # "покажи список персонажей" should strongly match list_characters
        match = router.best_match("покажи список персонажей", min_score=1)
        assert match is not None
        assert match.tool_name == "list_characters"

    def test_higher_threshold(self, router):
        match = router.best_match("персонаж", min_score=5)
        assert match is None


# ---------------------------------------------------------------------------
# RouteMatch dataclass
# ---------------------------------------------------------------------------

class TestRouteMatch:
    def test_fields(self):
        rm = RouteMatch(tool_name="test", score=3, matched_tokens=["a", "b"])
        assert rm.tool_name == "test"
        assert rm.score == 3
        assert rm.matched_tokens == ["a", "b"]

    def test_default_matched_tokens(self):
        rm = RouteMatch(tool_name="test", score=1)
        assert rm.matched_tokens == []


# ---------------------------------------------------------------------------
# Integration with tool registry
# ---------------------------------------------------------------------------

class TestRouterWithRegistry:
    def test_all_tools_have_keywords(self, tools):
        """Every registered tool should have keyword entries."""
        for name in tools:
            assert name in IntentRouter.TOOL_KEYWORDS, (
                f"Tool '{name}' missing from TOOL_KEYWORDS"
            )

    def test_all_tools_are_routable(self, router):
        """Each tool should match its own name tokens."""
        for name in router.tools:
            matches = router.route(name.replace("_", " "))
            names = [m.tool_name for m in matches]
            assert name in names, f"Tool '{name}' not self-routable"

    def test_revise_edit_match(self, router):
        matches = router.route("исправить главу")
        names = [m.tool_name for m in matches]
        assert "revise_chapter" in names

    def test_save_note_match(self, router):
        matches = router.route("запиши идею")
        names = [m.tool_name for m in matches]
        assert "save_note" in names

    def test_show_chapter_match(self, router):
        matches = router.route("покажи главу 3")
        names = [m.tool_name for m in matches]
        assert "show_chapter" in names

    def test_create_character_match(self, router):
        matches = router.route("создать нового персонажа")
        names = [m.tool_name for m in matches]
        assert "create_character" in names

    def test_create_plot_thread_match(self, router):
        matches = router.route("новая сюжетная линия")
        names = [m.tool_name for m in matches]
        assert "create_plot_thread" in names

    def test_create_world_element_match(self, router):
        matches = router.route("добавить локацию в мир")
        names = [m.tool_name for m in matches]
        assert "create_world_element" in names

    def test_create_relationship_match(self, router):
        matches = router.route("определи отношения между героями")
        names = [m.tool_name for m in matches]
        assert "create_relationship" in names

    def test_show_plot_state_match(self, router):
        matches = router.route("покажи состояние сюжета")
        names = [m.tool_name for m in matches]
        assert "show_plot_state" in names
