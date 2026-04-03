import json

from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, ChapterRepo,
    PlotThreadRepo, WorldElementRepo, RelationshipRepo, PlotStateRepo,
)


class ContextBuilder:
    def __init__(self, db: Database, max_tokens: int | None = None, settings=None):
        self.db = db
        self.projects = ProjectRepo(db)
        self.characters = CharacterRepo(db)
        self.chapters = ChapterRepo(db)
        self.plots = PlotThreadRepo(db)
        self.world = WorldElementRepo(db)
        self.relationships = RelationshipRepo(db)
        self.plot_states = PlotStateRepo(db)

        if settings:
            self.max_tokens = max_tokens or settings.context.budget_tokens
            self._history_chapters = settings.context.history_chapters
            self._multi_chapter_threshold = settings.context.multi_chapter_threshold
            self._passage_tail_chars = settings.context.passage_tail_chars
        else:
            self.max_tokens = max_tokens or 6000
            self._history_chapters = 5
            self._multi_chapter_threshold = 5
            self._passage_tail_chars = 2000

    def build(self, project_id: int, current_chapter: int) -> dict:
        blocks = []

        # Priority 1: Project overview
        project = self.projects.get(project_id)
        overview = f"[Проект: {project['name']}]\nЖанр: {project.get('genre', '')}\nСтатус: {project.get('description', '')}"
        blocks.append(("overview", overview))

        # Priority 2: Characters
        chars = self.characters.list_by_project(project_id)
        char_block = "[Персонажи]\n" + "\n".join(
            f"- {c['name']}: {c.get('description', '')} ({c.get('personality', '')})"
            for c in chars
        )
        blocks.append(("characters", char_block))

        # Priority 2.5: Plot state (structured plot tracking)
        latest_state = self.plot_states.get_latest(project_id)
        if latest_state:
            state = json.loads(latest_state["state"])
            state_block = self._format_plot_state(state)
            if state_block:
                blocks.append(("plot_state", state_block))

        # Priority 3: Chapter history — hierarchical summaries
        all_chapters = self.chapters.list_by_project(project_id)
        prev_chapters = [ch for ch in all_chapters if ch["chapter_number"] < current_chapter]

        if prev_chapters:
            # Arc summaries: ALL chapters (~20 words each)
            arc_lines = []
            for ch in prev_chapters:
                arc = ch.get("arc_summary", "") or ""
                if arc:
                    arc_lines.append(f"  Гл.{ch['chapter_number']}: {arc}")
            if arc_lines:
                arc_block = "[Арка романа — все главы]\n" + "\n".join(arc_lines)
                blocks.append(("arc_summaries", arc_block))

            # Compact summaries: last N chapters (~50 words each)
            recent = prev_chapters[-self._history_chapters:]
            compact_lines = []
            for ch in recent:
                compact = ch.get("compact_summary", "") or ""
                if compact:
                    compact_lines.append(f"  Гл.{ch['chapter_number']}: {compact}")
            if compact_lines:
                compact_block = "[Последние главы — суть]\n" + "\n".join(compact_lines)
                blocks.append(("compact_summaries", compact_block))

            # Detail summary: previous chapter only (~300 words)
            prev_ch = prev_chapters[-1]
            detail = prev_ch.get("summary", "") or ""
            if detail:
                detail_block = f"[Предыдущая глава ({prev_ch['chapter_number']}: {prev_ch.get('title', '')})]\n{detail}"
                blocks.append(("prev_detail", detail_block))

        # Priority 4: Plot threads
        threads = self.plots.list_by_project(project_id, status="active")
        if threads:
            thread_block = "[Активные сюжетные нити]\n" + "\n".join(
                f"- {t['name']}: {t['description']}" for t in threads
            )
            blocks.append(("plot_threads", thread_block))

        # Priority 5: World elements
        elements = self.world.list_by_project(project_id)
        if elements:
            world_block = "[Мир]\n" + "\n".join(
                f"- {e['name']} ({e['category']}): {e['description']}" for e in elements[:10]
            )
            blocks.append(("world", world_block))

        # Priority 6: Last passage from previous chapter
        if prev_chapters:
            prev_ch = prev_chapters[-1]
            if prev_ch.get("full_text"):
                text = prev_ch["full_text"]
                passage = text[-self._passage_tail_chars:] if len(text) > self._passage_tail_chars else text
                blocks.append(("prev_passage", f"[Конец предыдущей главы]\n{passage}"))

        # Priority 7: Relationships
        rels = self.relationships.list_by_project(project_id)
        if rels:
            rel_block = "[Отношения]\n" + "\n".join(
                f"- {r['char_a']} ↔ {r['char_b']}: {r['type']} — {r.get('description', '')}"
                for r in rels
            )
            blocks.append(("relationships", rel_block))

        return self._fit_budget(blocks, self.max_tokens)

    def _format_plot_state(self, state: dict) -> str:
        """Format plot state into a readable context block."""
        lines = ["[Состояние сюжета]"]

        conflicts = state.get("conflicts", [])
        if conflicts:
            lines.append("Конфликты:")
            for c in conflicts[:5]:
                lines.append(f"  - {c.get('name', '?')} ({c.get('parties', '')}): "
                             f"инт. {c.get('intensity', '?')}, {c.get('status', '')}")

        arcs = state.get("character_arcs", [])
        if arcs:
            lines.append("Арки персонажей:")
            for a in arcs[:5]:
                lines.append(f"  - {a.get('character', '?')}: {a.get('current_state', '')} "
                             f"({a.get('trajectory', '')})")

        relationships = state.get("relationships", [])
        if relationships:
            lines.append("Отношения:")
            for r in relationships[:5]:
                lines.append(f"  - {r.get('pair', '?')}: {r.get('type', '')}, "
                             f"инт. {r.get('intensity', '?')}, {r.get('direction', '')}")

        mysteries = state.get("mysteries", [])
        if mysteries:
            lines.append("Загадки:")
            for m in mysteries[:3]:
                lines.append(f"  - {m.get('name', '?')}: подсказок {m.get('clues_given', 0)}")

        tone = state.get("tone", "")
        if tone:
            lines.append(f"Тон арки: {tone}")

        hooks = state.get("hooks", [])
        if hooks:
            lines.append("Крючки:")
            for h in hooks[:3]:
                lines.append(f"  - {h.get('description', '?')} (гл.{h.get('planted_chapter', '?')})")

        # Only return if there's real content beyond the header
        if len(lines) <= 1:
            return ""
        return "\n".join(lines)

    def _fit_budget(self, blocks: list, budget: int) -> dict:
        result_blocks = []
        total = 0
        for name, text in blocks:
            tokens = self._estimate_tokens(text)
            if total + tokens <= budget:
                result_blocks.append(text)
                total += tokens
        return {"blocks": result_blocks, "total_tokens": total}

    def _estimate_tokens(self, text: str) -> int:
        cyrillic = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        other = len(text) - cyrillic
        return int(cyrillic / 2 + other / 4)
