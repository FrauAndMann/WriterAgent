import json

from writer_agent.db.database import Database
from writer_agent.db.repositories import ChapterRepo, ProjectRepo, StyleProfileRepo, PlotStateRepo
from writer_agent.engine.context import ContextBuilder
from writer_agent.engine.prompt_assembler import PromptAssembler
from writer_agent.llm.prompts import SYSTEM_WRITER


class ChapterGenerator:
    def __init__(self, db: Database, llm_client, context_builder: ContextBuilder):
        self.db = db
        self.llm = llm_client
        self.ctx = context_builder
        self.chapter_repo = ChapterRepo(db)
        self.project_repo = ProjectRepo(db)
        self.style_repo = StyleProfileRepo(db)
        self.plot_state_repo = PlotStateRepo(db)
        self.assembler = PromptAssembler(llm_client=llm_client, style_repo=self.style_repo)

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

        # Load plot state for prompt assembly
        plot_state_block = ""
        latest_state = self.plot_state_repo.get_latest(project_id)
        if latest_state:
            state = json.loads(latest_state["state"])
            plot_state_block = self.ctx._format_plot_state(state)

        # Assemble prompts via PromptAssembler
        prompts = self.assembler.assemble(
            outline=outline,
            chapter_number=chapter_number,
            style_instructions=style_instructions,
            plot_state_block=plot_state_block,
            target_words=target_words,
        )

        # Generate
        full_text = self.llm.generate(
            system_prompt=prompts["system"],
            user_prompt=prompts["user"],
            context_blocks=context["blocks"],
            max_tokens=min(target_words * 2, 8000),
            temperature=temperature,
        )

        # Generate hierarchical summaries
        summaries = self._generate_hierarchical_summaries(full_text)

        # Update plot state
        plot_state = self._update_plot_state(project_id, chapter_number, summaries["detail"])

        # Save to DB
        word_count = len(full_text.split())
        chapter_id = self.chapter_repo.create(
            project_id=project_id,
            chapter_number=chapter_number,
            title=f"Глава {chapter_number}",
            summary=summaries["detail"],
            compact_summary=summaries["compact"],
            arc_summary=summaries["arc"],
            full_text=full_text,
        )

        # Save plot state
        if plot_state:
            self.plot_state_repo.create(project_id, chapter_number, plot_state)

        return {
            "chapter_id": chapter_id,
            "full_text": full_text,
            "word_count": word_count,
            "summaries": summaries,
        }

    def _generate_hierarchical_summaries(self, text: str) -> dict[str, str]:
        """Generate all three summary levels: detail, compact, arc."""
        result = {}
        try:
            result["detail"] = self._call_summary_llm(text, "detail")
        except Exception:
            result["detail"] = text[:300] + "..." if len(text) > 300 else text

        try:
            result["compact"] = self._call_summary_llm(result["detail"], "compact")
        except Exception:
            result["compact"] = result["detail"][:100]

        try:
            result["arc"] = self._call_summary_llm(result["detail"], "arc")
        except Exception:
            result["arc"] = result["detail"][:60]

        return result

    def _call_summary_llm(self, text: str, level: str) -> str:
        """Ask LLM to generate a summary at the specified level."""
        prompts = {
            "detail": (
                "Создай подробное содержание главы в 200-300 слов. "
                "Включи: ключевые события, диалоги, эмоции, решения персонажей."
            ),
            "compact": (
                "Сожми содержание главы в 1-2 предложения (до 50 слов). "
                "Только суть: что произошло и что изменилось."
            ),
            "arc": (
                "Опиши функцию этой главы в общей арке романа одним предложением (до 20 слов). "
                "Формат: '[Персонажи] [действие] — [последствие]'."
            ),
        }
        summary = self.llm.generate(
            system_prompt=prompts[level],
            user_prompt=f"[Текст]\n{text[:4000]}",
            max_tokens=400 if level == "detail" else 150,
            temperature=0.3,
        )
        return summary.strip()

    def _update_plot_state(self, project_id: int, chapter_number: int,
                           chapter_summary: str) -> dict | None:
        """Update plot state via LLM after chapter generation."""
        try:
            prev = self.plot_state_repo.get_latest(project_id)
            current_state = json.loads(prev["state"]) if prev else _empty_plot_state()

            prompt = (
                "Ты аналитик сюжета. Обнови состояние романа на основе новой главы.\n\n"
                f"Текущее состояние:\n{json.dumps(current_state, ensure_ascii=False, indent=2)}\n\n"
                f"Новая глава (summary):\n{chapter_summary}\n\n"
                "Обнови:\n"
                "1. conflicts — новые/изменившиеся конфликты с intensity (1-10)\n"
                "2. character_arcs — текущее эмоциональное состояние каждого персонажа\n"
                "3. mysteries — нерешённые загадки, что уже раскрыто читателю\n"
                "4. relationships — эволюция отношений с intensity и direction\n"
                "5. tone — текущий тон арки\n"
                "6. hooks — посаженные крючки (обещания читателю)\n\n"
                "Ответ: строго JSON."
            )
            response = self.llm.generate(
                system_prompt=prompt,
                user_prompt="Верни обновлённый JSON.",
                max_tokens=1500,
                temperature=0.2,
            )
            return self._extract_json(response)
        except Exception:
            return None

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON object from LLM response."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    return None
            return None

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


def _empty_plot_state() -> dict:
    return {
        "conflicts": [],
        "character_arcs": [],
        "mysteries": [],
        "relationships": [],
        "tone": "rising_tension",
        "hooks": [],
    }
