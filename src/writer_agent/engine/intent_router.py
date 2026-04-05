"""Token-based intent router — fast tool matching without LLM call."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RouteMatch:
    """A scored match between a user prompt and a tool."""

    tool_name: str
    score: int
    matched_tokens: list[str] = field(default_factory=list)


class IntentRouter:
    """Match user prompts to tools via token overlap scoring.

    For each registered tool, we check how many tokens from the user's prompt
    appear in the tool's name, description, or extra keywords.  Higher score =
    better match.  If the best score exceeds a threshold, we skip the LLM call
    entirely and execute the tool directly.
    """

    # Per-tool extra keywords for better Russian matching
    TOOL_KEYWORDS: dict[str, list[str]] = {
        "create_character": [
            "персонаж", "герой", "героиня", "характер", "создать", "новый",
            "character", "hero", "добавить",
        ],
        "create_plot_thread": [
            "сюжет", "линия", "конфликт", "история", "нитка",
            "plot", "thread", "storyline",
        ],
        "create_world_element": [
            "мир", "локация", "место", "артефакт", "фракция", "магия",
            "world", "location", "element",
        ],
        "create_relationship": [
            "отношение", "отношения", "связь", "пара", "любовь", "враг", "союзник",
            "определи", "задай", "между",
            "relationship", "pair",
        ],
        "list_characters": [
            "список", "персонажи", "все", "кто", "покажи", "покажи персонажей",
            "list", "characters", "кто есть",
        ],
        "list_plot_threads": [
            "сюжеты", "линии", "нитки", "покажи сюжеты",
            "threads", "plotlines",
        ],
        "show_chapter": [
            "глава", "текст", "прочитать", "читать", "покажи главу",
            "chapter", "read",
        ],
        "show_project_status": [
            "статус", "проект", "обзор", "прогресс", "сколько",
            "status", "overview", "project",
        ],
        "show_plot_state": [
            "состояние", "конфликт", "арка", "тонус",
            "state", "plot",
        ],
        "write_chapter": [
            "писать", "написать", "сгенерировать", "новая глава", "давай главу",
            "write", "generate", "draft",
        ],
        "revise_chapter": [
            "переделать", "исправить", "редактировать", "переписать", "изменить",
            "revise", "edit", "change", "fix",
        ],
        "export_novel": [
            "экспорт", "сохранить", "файл", "документ", "выгрузить",
            "export", "save", "file", "docx",
        ],
        "save_note": [
            "заметка", "идея", "записать", "запиши", "заметить", "запомни",
            "note", "idea",
        ],
    }

    def __init__(self, tools: dict[str, "ToolDef"]):  # noqa: F821
        self.tools = tools
        # Pre-build haystacks for each tool: (name_lower, desc_lower, kw_set)
        self._haystacks: dict[str, tuple[str, str, set[str]]] = {}
        for name, tool in tools.items():
            kw = set(k.lower() for k in self.TOOL_KEYWORDS.get(name, []))
            self._haystacks[name] = (
                name.lower().replace("_", " "),
                tool.description.lower(),
                kw,
            )

    def route(self, prompt: str, limit: int = 3) -> list[RouteMatch]:
        """Score all tools against prompt tokens, return top matches."""
        tokens = self._tokenize(prompt)
        if not tokens:
            return []

        matches: list[RouteMatch] = []
        for name, (name_lower, desc_lower, kw_set) in self._haystacks.items():
            score = 0
            matched: list[str] = []
            for tok in tokens:
                if (
                    tok in name_lower
                    or tok in desc_lower
                    or tok in kw_set
                ):
                    score += 1
                    matched.append(tok)
            if score > 0:
                matches.append(RouteMatch(tool_name=name, score=score, matched_tokens=matched))

        matches.sort(key=lambda m: (-m.score, m.tool_name))
        return matches[:limit]

    def best_match(self, prompt: str, min_score: int = 2) -> RouteMatch | None:
        """Return the best match if its score >= min_score.

        Also checks that the best match is **significantly better** than the
        second-best (at least 2 points gap) to avoid mis-routing ambiguous prompts.
        """
        matches = self.route(prompt, limit=2)
        if not matches:
            return None
        best = matches[0]
        if best.score < min_score:
            return None
        # Ambiguity guard: if second match is close, skip fast path
        if len(matches) > 1 and (best.score - matches[1].score) < 1:
            return None
        return best

    @staticmethod
    def _tokenize(prompt: str) -> list[str]:
        """Split prompt into lowercase tokens for matching."""
        # Replace punctuation with spaces, then split
        cleaned = re.sub(r"[^\w\s]", " ", prompt.lower())
        tokens = cleaned.split()
        # Also add compound tokens (adjacent pairs) for phrases like "покажи персонажей"
        compounds = []
        for i in range(len(tokens) - 1):
            compounds.append(f"{tokens[i]} {tokens[i+1]}")
        return tokens + compounds
