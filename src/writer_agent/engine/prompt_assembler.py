"""Prompt Assembler — orchestrates scene + style + plot + context into final prompts."""

from __future__ import annotations

from writer_agent.llm.prompts import SYSTEM_WRITER
from writer_agent.llm.scene_prompts import classify_scenes, get_scene_prompt, SCENE_PROMPTS
from writer_agent.analysis.style_injector import build_style_injection


class PromptAssembler:
    """Assembles the full prompt from modular components."""

    def __init__(self, llm_client=None, style_repo=None):
        self.llm = llm_client
        self.style_repo = style_repo

    def assemble(
        self,
        outline: str = "",
        chapter_number: int = 1,
        context_blocks: list[str] | None = None,
        style_instructions: str = "",
        scene_types: list[str] | None = None,
        plot_state_block: str = "",
        target_words: int = 3000,
    ) -> dict[str, str]:
        """Assemble system and user prompts from components.

        Returns:
            {"system": str, "user": str}
        """
        # ── System prompt ──
        system_parts = [SYSTEM_WRITER]

        # Scene-specific instructions
        if scene_types:
            for stype in scene_types:
                prompt = get_scene_prompt(stype)
                if prompt:
                    system_parts.append(f"\n[Сцена: {stype}]\n{prompt}")
        elif outline and self.llm:
            # Auto-classify if LLM available and no explicit types
            try:
                scenes = classify_scenes(self.llm, outline)
                for scene in scenes:
                    prompt = get_scene_prompt(scene["type"])
                    if prompt:
                        system_parts.append(f"\n[Сцена: {scene['type']}]\n{prompt}")
            except Exception:
                pass

        # Style injection
        if not style_instructions and self.style_repo:
            style_instructions = self._load_style_from_repo()
        if style_instructions:
            system_parts.append(f"\n{style_instructions}")

        # Plot state block
        if plot_state_block:
            system_parts.append(f"\n{plot_state_block}")

        system = "\n".join(system_parts)

        # ── User prompt ──
        user = f"[Задание]\nНапиши главу {chapter_number}."
        if outline:
            user += f"\n\n[План главы]\n{outline}"
        user += f"\n\nЦелевой объём: ~{target_words} слов."

        return {"system": system, "user": user}

    def _load_style_from_repo(self) -> str:
        """Load and build style injection from DB profile."""
        if not self.style_repo:
            return ""
        profiles = self.style_repo.list()
        if not profiles:
            return ""

        profile = profiles[0]
        analysis = profile.get("analysis", {})
        if isinstance(analysis, str):
            import json
            analysis = json.loads(analysis)
        if not analysis:
            return ""

        sample_passages = profile.get("sample_passages", [])
        if isinstance(sample_passages, str):
            import json
            sample_passages = json.loads(sample_passages)

        return build_style_injection(analysis, sample_passages)
