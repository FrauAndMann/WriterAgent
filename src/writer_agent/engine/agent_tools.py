"""Tool registry for the interactive agent — wraps existing repos into callable tools."""

from __future__ import annotations

from typing import Any, Callable


# ── Tool definition ──────────────────────────────────────────────────────────


class ToolDef:
    """A single tool the agent can call."""

    def __init__(self, name: str, description: str, params: list[dict], fn: Callable):
        self.name = name
        self.description = description
        self.params = params  # [{"name": str, "type": str, "required": bool, "desc": str}]
        self.fn = fn

    def to_prompt_text(self) -> str:
        """Format tool description for the system prompt."""
        param_lines = []
        for p in self.params:
            req = "required" if p.get("required") else "optional"
            param_lines.append(f"    - {p['name']} ({p['type']}, {req}): {p.get('desc', '')}")
        params_str = "\n".join(param_lines) if param_lines else "    (no params)"
        return f"### {self.name}\n{self.description}\nParameters:\n{params_str}"


# ── Tool functions ────────────────────────────────────────────────────────────


def _create_character(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import CharacterRepo
    repo = CharacterRepo(db)
    cid = repo.create(
        project_id=project_id,
        name=kwargs.get("name", "Безымянный"),
        description=kwargs.get("description", ""),
        personality=kwargs.get("personality", ""),
        full_name=kwargs.get("full_name", ""),
        background=kwargs.get("background", ""),
        arc=kwargs.get("arc", ""),
    )
    return {"success": True, "id": cid, "name": kwargs.get("name")}


def _create_plot_thread(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import PlotThreadRepo
    repo = PlotThreadRepo(db)
    tid = repo.create(
        project_id=project_id,
        name=kwargs.get("name", ""),
        description=kwargs.get("description", ""),
        importance=kwargs.get("importance", 5),
    )
    return {"success": True, "id": tid, "name": kwargs.get("name")}


def _create_world_element(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import WorldElementRepo
    repo = WorldElementRepo(db)
    eid = repo.create(
        project_id=project_id,
        name=kwargs.get("name", ""),
        category=kwargs.get("category", ""),
        description=kwargs.get("description", ""),
    )
    return {"success": True, "id": eid, "name": kwargs.get("name")}


def _create_relationship(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import RelationshipRepo
    repo = RelationshipRepo(db)
    rid = repo.create(
        project_id=project_id,
        char_a=kwargs.get("char_a", ""),
        char_b=kwargs.get("char_b", ""),
        type=kwargs.get("type", ""),
        description=kwargs.get("description", ""),
    )
    return {"success": True, "id": rid}


def _list_characters(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import CharacterRepo
    chars = CharacterRepo(db).list_by_project(project_id)
    return {"characters": [
        {"name": c["name"], "description": c.get("description", ""),
         "personality": c.get("personality", "")}
        for c in chars
    ]}


def _list_plot_threads(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import PlotThreadRepo
    threads = PlotThreadRepo(db).list_by_project(project_id)
    return {"plot_threads": [
        {"name": t["name"], "description": t.get("description", ""),
         "status": t.get("status", ""), "importance": t.get("importance", 0)}
        for t in threads
    ]}


def _show_chapter(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import ChapterRepo
    repo = ChapterRepo(db)
    num = kwargs.get("chapter_number")
    if num:
        ch = repo.get_by_number(project_id, int(num))
        if not ch:
            return {"error": f"Chapter {num} not found"}
        return {
            "chapter_number": ch["chapter_number"],
            "title": ch.get("title", ""),
            "word_count": ch.get("word_count", 0),
            "summary": ch.get("summary", ""),
            "text_preview": ch.get("full_text", "")[:500],
        }
    # List all
    chapters = repo.list_by_project(project_id)
    return {"chapters": [
        {"number": c["chapter_number"], "title": c.get("title", ""),
         "words": c.get("word_count", 0),
         "arc": c.get("arc_summary", "")}
        for c in chapters
    ]}


def _show_project_status(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo, CharacterRepo, PlotThreadRepo
    proj = ProjectRepo(db).get(project_id)
    chapters = ChapterRepo(db).list_by_project(project_id)
    chars = CharacterRepo(db).list_by_project(project_id)
    threads = PlotThreadRepo(db).list_by_project(project_id)
    total_words = sum(c.get("word_count", 0) for c in chapters)
    return {
        "name": proj["name"],
        "genre": proj.get("genre", ""),
        "status": proj.get("status", ""),
        "chapters": len(chapters),
        "total_words": total_words,
        "characters": len(chars),
        "plot_threads": len(threads),
    }


def _show_plot_state(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import PlotStateRepo
    import json
    latest = PlotStateRepo(db).get_latest(project_id)
    if not latest:
        return {"message": "No plot state yet. Generate a chapter first."}
    return json.loads(latest["state"])


def _write_chapter(db, project_id: int, llm_client=None, context_builder=None, **kwargs) -> dict:
    from writer_agent.engine.generator import ChapterGenerator
    from writer_agent.db.repositories import ChapterRepo
    if not llm_client or not context_builder:
        return {"error": "LLM client not available"}
    gen = ChapterGenerator(db=db, llm_client=llm_client, context_builder=context_builder)
    latest = ChapterRepo(db).get_latest(project_id)
    next_ch = (latest["chapter_number"] + 1) if latest else 1
    result = gen.generate_chapter(
        project_id=project_id,
        chapter_number=next_ch,
        outline=kwargs.get("outline", ""),
        target_words=kwargs.get("target_words", 3000),
        temperature=kwargs.get("temperature", 0.85),
    )
    return {
        "success": True,
        "chapter_number": next_ch,
        "word_count": result["word_count"],
        "summary": result.get("summaries", {}).get("arc", ""),
    }


def _revise_chapter(db, project_id: int, llm_client=None, context_builder=None, **kwargs) -> dict:
    from writer_agent.engine.generator import ChapterGenerator
    from writer_agent.db.repositories import ChapterRepo
    if not llm_client or not context_builder:
        return {"error": "LLM client not available"}
    chapter_number = int(kwargs.get("chapter_number", 1))
    instructions = kwargs.get("instructions", "")
    ch = ChapterRepo(db).get_by_number(project_id, chapter_number)
    if not ch:
        return {"error": f"Chapter {chapter_number} not found"}
    gen = ChapterGenerator(db=db, llm_client=llm_client, context_builder=context_builder)
    result = gen.revise_chapter(ch["id"], instructions)
    return {"success": True, "chapter_number": chapter_number}


def _export_novel(db, project_id: int, **kwargs) -> dict:
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo
    from writer_agent.export.exporter import Exporter
    from pathlib import Path
    proj = ProjectRepo(db).get(project_id)
    title = proj["name"]
    chapters = ChapterRepo(db).list_by_project(project_id)
    if not chapters:
        return {"error": "No chapters to export"}
    fmt = kwargs.get("format", "md")
    output_dir = Path("data/novels")
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = title.replace(" ", "_").replace("/", "_")
    ext = {"md": ".md", "txt": ".txt", "docx": ".docx"}.get(fmt, ".md")
    path = output_dir / f"{safe}{ext}"
    exporter = Exporter(ChapterRepo(db))
    if fmt == "txt":
        exporter.to_txt(project_id, path, title=title)
    elif fmt == "docx":
        exporter.to_docx(project_id, path, title=title)
    else:
        exporter.to_markdown(project_id, path, title=title)
    return {"success": True, "path": str(path)}


def _save_note(db, project_id: int, **kwargs) -> dict:
    """Save a freeform note attached to the project."""
    from writer_agent.db.repositories import WorldElementRepo
    repo = WorldElementRepo(db)
    nid = repo.create(
        project_id=project_id,
        name=kwargs.get("title", "Заметка"),
        category="note",
        description=kwargs.get("content", ""),
    )
    return {"success": True, "id": nid}


# ── Registry ─────────────────────────────────────────────────────────────────


def build_tool_registry() -> dict[str, ToolDef]:
    """Build the complete tool registry."""
    tools = [
        ToolDef(
            name="create_character",
            description="Create a new character in the project.",
            params=[
                {"name": "name", "type": "string", "required": True, "desc": "Character name"},
                {"name": "description", "type": "string", "required": False, "desc": "Physical description"},
                {"name": "personality", "type": "string", "required": False, "desc": "Personality traits"},
                {"name": "background", "type": "string", "required": False, "desc": "Backstory"},
                {"name": "arc", "type": "string", "required": False, "desc": "Character arc description"},
            ],
            fn=_create_character,
        ),
        ToolDef(
            name="create_plot_thread",
            description="Create a new plot thread / storyline.",
            params=[
                {"name": "name", "type": "string", "required": True, "desc": "Thread name"},
                {"name": "description", "type": "string", "required": False, "desc": "What this thread is about"},
                {"name": "importance", "type": "integer", "required": False, "desc": "1-10, default 5"},
            ],
            fn=_create_plot_thread,
        ),
        ToolDef(
            name="create_world_element",
            description="Create a world-building element (location, artifact, rule, etc).",
            params=[
                {"name": "name", "type": "string", "required": True, "desc": "Element name"},
                {"name": "category", "type": "string", "required": False, "desc": "e.g. location, artifact, faction, magic_system"},
                {"name": "description", "type": "string", "required": False, "desc": "Description"},
            ],
            fn=_create_world_element,
        ),
        ToolDef(
            name="create_relationship",
            description="Define a relationship between two characters.",
            params=[
                {"name": "char_a", "type": "string", "required": True, "desc": "First character name"},
                {"name": "char_b", "type": "string", "required": True, "desc": "Second character name"},
                {"name": "type", "type": "string", "required": False, "desc": "e.g. enemies, lovers, allies"},
                {"name": "description", "type": "string", "required": False, "desc": "Relationship details"},
            ],
            fn=_create_relationship,
        ),
        ToolDef(
            name="list_characters",
            description="List all characters in the project.",
            params=[],
            fn=_list_characters,
        ),
        ToolDef(
            name="list_plot_threads",
            description="List all plot threads / storylines.",
            params=[],
            fn=_list_plot_threads,
        ),
        ToolDef(
            name="show_chapter",
            description="Show chapter content or list all chapters.",
            params=[
                {"name": "chapter_number", "type": "integer", "required": False, "desc": "Chapter number, omit to list all"},
            ],
            fn=_show_chapter,
        ),
        ToolDef(
            name="show_project_status",
            description="Show project overview: chapters, word count, characters.",
            params=[],
            fn=_show_project_status,
        ),
        ToolDef(
            name="show_plot_state",
            description="Show the current plot state machine (conflicts, arcs, tone).",
            params=[],
            fn=_show_plot_state,
        ),
        ToolDef(
            name="write_chapter",
            description="Generate the next chapter. Uses scene classifier, style injector, hierarchical summaries, plot state.",
            params=[
                {"name": "outline", "type": "string", "required": False, "desc": "Chapter outline/plan"},
                {"name": "target_words", "type": "integer", "required": False, "desc": "Target word count, default 3000"},
                {"name": "temperature", "type": "float", "required": False, "desc": "Creativity 0.0-2.0, default 0.85"},
            ],
            fn=_write_chapter,
        ),
        ToolDef(
            name="revise_chapter",
            description="Revise an existing chapter based on instructions.",
            params=[
                {"name": "chapter_number", "type": "integer", "required": True, "desc": "Chapter to revise"},
                {"name": "instructions", "type": "string", "required": True, "desc": "What to change"},
            ],
            fn=_revise_chapter,
        ),
        ToolDef(
            name="export_novel",
            description="Export the novel to a file.",
            params=[
                {"name": "format", "type": "string", "required": False, "desc": "md, txt, or docx (default md)"},
            ],
            fn=_export_novel,
        ),
        ToolDef(
            name="save_note",
            description="Save a freeform note or idea.",
            params=[
                {"name": "title", "type": "string", "required": False, "desc": "Note title"},
                {"name": "content", "type": "string", "required": True, "desc": "Note content"},
            ],
            fn=_save_note,
        ),
    ]
    return {t.name: t for t in tools}
