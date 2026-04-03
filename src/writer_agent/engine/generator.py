from writer_agent.db.database import Database
from writer_agent.db.repositories import ChapterRepo, ProjectRepo, StyleProfileRepo
from writer_agent.engine.context import ContextBuilder
from writer_agent.llm.prompts import SYSTEM_WRITER


class ChapterGenerator:
    def __init__(self, db: Database, llm_client, context_builder: ContextBuilder):
        self.db = db
        self.llm = llm_client
        self.ctx = context_builder
        self.chapter_repo = ChapterRepo(db)
        self.project_repo = ProjectRepo(db)
        self.style_repo = StyleProfileRepo(db)

    def generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        outline: str = "",
        target_words: int = 3000,
        style_instructions: str = "",
        temperature: float = 0.85,
    ) -> dict:
        # Build context from memory
        context = self.ctx.build(project_id=project_id, current_chapter=chapter_number)

        # Assemble prompts
        system = SYSTEM_WRITER
        if not style_instructions:
            style_instructions = self._load_style_prompt()
        if style_instructions:
            system += f"\n\n[Стилевые инструкции автора]\n{style_instructions}"

        user = f"[Задание]\nНапиши главу {chapter_number}."
        if outline:
            user += f"\n\n[План главы]\n{outline}"
        user += f"\n\nЦелевой объём: ~{target_words} слов."

        # Generate
        full_text = self.llm.generate(
            system_prompt=system,
            user_prompt=user,
            context_blocks=context["blocks"],
            max_tokens=min(target_words * 2, 8000),
            temperature=temperature,
        )

        # Save to DB
        word_count = len(full_text.split())
        chapter_id = self.chapter_repo.create(
            project_id=project_id,
            chapter_number=chapter_number,
            title=f"Глава {chapter_number}",
            summary=self._generate_summary(full_text),
            full_text=full_text,
        )

        return {
            "chapter_id": chapter_id,
            "full_text": full_text,
            "word_count": word_count,
        }

    def _generate_summary(self, text: str) -> str:
        """Generate summary with LLM fallback to truncation."""
        try:
            return self._generate_summary_llm(text)
        except Exception:
            if len(text) <= 300:
                return text
            return text[:300] + "..."

    def _generate_summary_llm(self, text: str) -> str:
        """Ask LLM to compress a chapter into 2-3 sentences."""
        summary = self.llm.generate(
            system_prompt="Ты сжимаешь текст главы романа в краткое содержание. 2-3 предложения. Только ключевые события и персонажи.",
            user_prompt=f"[Текст главы]\n{text[:4000]}",
            max_tokens=300,
            temperature=0.3,
        )
        return summary.strip()

    def revise_chapter(self, chapter_id: int, instructions: str) -> dict:
        chapter = self.chapter_repo.get(chapter_id)
        system = SYSTEM_WRITER + "\n\nТы перерабатываешь существующую главу по указаниям автора."
        user = f"[Текущий текст главы]\n{chapter['full_text']}\n\n[Указания для переработки]\n{instructions}"

        new_text = self.llm.generate(
            system_prompt=system,
            user_prompt=user,
            max_tokens=8000,
        )

        self.chapter_repo.update_text(chapter_id, new_text)
        return {"chapter_id": chapter_id, "full_text": new_text}

    def _load_style_prompt(self) -> str:
        """Load the latest style profile and convert to instructions."""
        profiles = self.style_repo.list()
        if not profiles:
            return ""
        analysis = profiles[0].get("analysis", {})
        if isinstance(analysis, str):
            import json
            analysis = json.loads(analysis)
        if not analysis:
            return ""

        lines = ["[Стиль автора]"]
        if analysis.get("avg_sentence_length"):
            lines.append(f"- Средняя длина предложения: {analysis['avg_sentence_length']:.0f} слов")
        if analysis.get("pov_style"):
            lines.append(f"- POV: {analysis['pov_style']}")
        if analysis.get("dialogue_ratio"):
            lines.append(f"- Доля диалогов: {analysis['dialogue_ratio']:.0%}")
        if analysis.get("frequent_words"):
            top_words = analysis["frequent_words"][:10]
            lines.append(f"- Частые слова: {', '.join(top_words)}")
        return "\n".join(lines)
