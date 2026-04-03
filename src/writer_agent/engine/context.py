from writer_agent.db.database import Database
from writer_agent.db.repositories import (
    ProjectRepo, CharacterRepo, ChapterRepo,
    PlotThreadRepo, WorldElementRepo, RelationshipRepo,
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

        # Priority 3: Chapter history — multi-chapter compression when deep into the novel
        prev_chapter = self.chapters.get_by_number(project_id, current_chapter - 1)
        if current_chapter > self._multi_chapter_threshold:
            history_lines = []
            start = max(1, current_chapter - self._history_chapters)
            for ch_num in range(start, current_chapter):
                ch = self.chapters.get_by_number(project_id, ch_num)
                if ch:
                    history_lines.append(
                        f"  Гл.{ch['chapter_number']}: {ch.get('summary', '')}"
                    )
            if history_lines:
                history_block = "[История последних глав]\n" + "\n".join(history_lines)
                blocks.append(("chapter_history", history_block))
        elif prev_chapter:
            summary_block = f"[Предыдущая глава ({prev_chapter['chapter_number']}: {prev_chapter.get('title', '')})]\n{prev_chapter['summary']}"
            blocks.append(("prev_summary", summary_block))

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
        if prev_chapter and prev_chapter.get("full_text"):
            text = prev_chapter["full_text"]
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
