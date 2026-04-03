from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="writer-agent",
    help="CLI agent for writing dark romance novels with LM Studio",
    no_args_is_help=True,
)
console = Console()


def _get_db(path: Path | None = None):
    from writer_agent.config import Config
    from writer_agent.db.database import Database

    config = Config.from_env()
    db_path = path or config.db_path
    db = Database(db_path)
    db.initialize()
    return db


# ── version ──────────────────────────────────────────────────────────────────


@app.command()
def version():
    """Show version."""
    from writer_agent import __version__

    console.print(f"WriterAgent v{__version__}")


# ── new ──────────────────────────────────────────────────────────────────────


@app.command()
def new(title: str):
    """Create a new project."""
    db = _get_db()
    from writer_agent.db.repositories import ProjectRepo

    repo = ProjectRepo(db)
    project_id = repo.create(name=title, genre="dark romance")
    console.print(f"[green]Created project:[/green] {title} (id={project_id})")


# ── list ─────────────────────────────────────────────────────────────────────


@app.command(name="list")
def list_projects():
    """List all projects."""
    db = _get_db()
    from writer_agent.db.repositories import ProjectRepo

    projects = ProjectRepo(db).list()
    if not projects:
        console.print("[dim]No projects yet.[/dim]")
        return

    table = Table(title="Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Genre", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")

    for p in projects:
        table.add_row(
            str(p["id"]),
            p["name"],
            p.get("genre", ""),
            p.get("status", ""),
            p.get("created_at", ""),
        )
    console.print(table)


# ── status ───────────────────────────────────────────────────────────────────


@app.command()
def status(title: str):
    """Show project status, word count, characters."""
    db = _get_db()
    from writer_agent.db.repositories import ProjectRepo, CharacterRepo, ChapterRepo

    project = ProjectRepo(db).get_by_name(title)
    if not project:
        console.print(f"[red]Project not found:[/red] {title}")
        raise typer.Exit(1)

    pid = project["id"]
    chapters = ChapterRepo(db).list_by_project(pid)
    chars = CharacterRepo(db).list_by_project(pid)
    total_words = sum(ch.get("word_count", 0) for ch in chapters)

    console.print(f"\n[bold]{project['name']}[/bold] — {project['status']}")
    console.print(f"Genre: {project.get('genre', '')}")
    console.print(f"Chapters: {len(chapters)} | Words: {total_words:,} | Characters: {len(chars)}")

    if chars:
        console.print("\n[bold]Characters:[/bold]")
        for c in chars:
            console.print(f"  - {c['name']}: {c.get('description', '')}")


# ── brainstorm ───────────────────────────────────────────────────────────────


@app.command()
def brainstorm(title: str):
    """Enter brainstorm mode for a project."""
    db = _get_db()
    from writer_agent.config import Config
    from writer_agent.llm.client import LLMClient
    from writer_agent.engine.brainstorm import BrainstormEngine

    config = Config.from_env()
    llm = LLMClient(config)
    engine = BrainstormEngine(db=db, llm_client=llm)

    # Find or create project
    from writer_agent.db.repositories import ProjectRepo, BrainstormSessionRepo

    project = ProjectRepo(db).get_by_name(title)
    if project:
        session_id = BrainstormSessionRepo(db).create(project_id=project["id"], notes="")
    else:
        session_id = engine.start_session(title=title)

    console.print(f"\n[bold]Brainstorm: {title}[/bold]")
    console.print("[dim]Commands: /help, /save char|plot|world, /characters, /plots, /done, /quit[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]You>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input == "/quit":
            console.print("[dim]Session saved. Goodbye.[/dim]")
            break
        if user_input == "/done":
            engine.finalize_session(session_id)
            console.print("[green]Project finalized and ready for writing![/green]")
            break
        if user_input == "/help":
            console.print(Panel(
                "[bold]Brainstorm Commands:[/bold]\n"
                "/save char <name> <desc>  — Save character\n"
                "/save plot <name> <desc>  — Save plot thread\n"
                "/save world <name> <desc> — Save world element\n"
                "/characters               — List saved characters\n"
                "/plots                    — List saved plot threads\n"
                "/done                     — Finalize & move to writing\n"
                "/quit                     — Exit brainstorm",
                title="Help",
            ))
            continue
        if user_input == "/characters":
            from writer_agent.db.repositories import CharacterRepo
            chars = CharacterRepo(db).list_by_project(project["id"] if project else ProjectRepo(db).get_by_name(title)["id"])
            if not chars:
                console.print("[dim]No characters saved yet.[/dim]")
            else:
                for c in chars:
                    console.print(Panel(
                        f"{c.get('description', '')}\n[i]{c.get('personality', '')}[/i]",
                        title=f"[bold]{c['name']}[/bold]",
                    ))
            continue
        if user_input == "/plots":
            from writer_agent.db.repositories import PlotThreadRepo
            pid = project["id"] if project else ProjectRepo(db).get_by_name(title)["id"]
            threads = PlotThreadRepo(db).list_by_project(pid)
            if not threads:
                console.print("[dim]No plot threads saved yet.[/dim]")
            else:
                for t in threads:
                    console.print(f"  [bold]{t['name']}[/bold] ({t['status']}): {t['description']}")
            continue
        if user_input.startswith("/save char "):
            parts = user_input[len("/save char "):].split(" ", 1)
            name = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            engine.save_character(session_id, name=name, description=desc)
            console.print(f"[green]Saved character:[/green] {name}")
            continue
        if user_input.startswith("/save plot "):
            parts = user_input[len("/save plot "):].split(" ", 1)
            name = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            engine.save_plot_thread(session_id, name=name, description=desc)
            console.print(f"[green]Saved plot thread:[/green] {name}")
            continue
        if user_input.startswith("/save world "):
            parts = user_input[len("/save world "):].split(" ", 1)
            name = parts[0]
            desc = parts[1] if len(parts) > 1 else ""
            engine.save_world_element(session_id, name=name, description=desc)
            console.print(f"[green]Saved world element:[/green] {name}")
            continue

        response = engine.chat(session_id, user_input)
        console.print(Panel(Markdown(response), title="[bold magenta]Agent[/bold magenta]"))


# ── write ────────────────────────────────────────────────────────────────────


@app.command()
def write(title: str):
    """Generate the next chapter."""
    db = _get_db()
    from writer_agent.config import Config
    from writer_agent.llm.client import LLMClient
    from writer_agent.engine.context import ContextBuilder
    from writer_agent.engine.generator import ChapterGenerator
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo

    config = Config.from_env()
    llm = LLMClient(config)
    project = ProjectRepo(db).get_by_name(title)
    if not project:
        console.print(f"[red]Project not found:[/red] {title}")
        raise typer.Exit(1)

    pid = project["id"]
    latest = ChapterRepo(db).get_latest(pid)
    next_ch = (latest["chapter_number"] + 1) if latest else 1

    ctx = ContextBuilder(db, max_tokens=config.max_context_tokens)
    gen = ChapterGenerator(db=db, llm_client=llm, context_builder=ctx)

    console.print(f"\n[bold]Writing chapter {next_ch}[/bold] for {title}...")

    result = gen.generate_chapter(
        project_id=pid,
        chapter_number=next_ch,
    )
    console.print(f"[green]Done![/green] {result['word_count']} words written.")


# ── revise ───────────────────────────────────────────────────────────────────


@app.command()
def revise(title: str, chapter: int, instructions: str = ""):
    """Revise a chapter."""
    db = _get_db()
    from writer_agent.config import Config
    from writer_agent.llm.client import LLMClient
    from writer_agent.engine.context import ContextBuilder
    from writer_agent.engine.generator import ChapterGenerator
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo

    config = Config.from_env()
    llm = LLMClient(config)
    project = ProjectRepo(db).get_by_name(title)
    if not project:
        console.print(f"[red]Project not found:[/red] {title}")
        raise typer.Exit(1)

    ch = ChapterRepo(db).get_by_number(project["id"], chapter)
    if not ch:
        console.print(f"[red]Chapter {chapter} not found.[/red]")
        raise typer.Exit(1)

    if not instructions:
        instructions = typer.prompt("Revision instructions")

    ctx = ContextBuilder(db, max_tokens=config.max_context_tokens)
    gen = ChapterGenerator(db=db, llm_client=llm, context_builder=ctx)
    result = gen.revise_chapter(ch["id"], instructions)
    console.print(f"[green]Chapter {chapter} revised.[/green]")


# ── analyze-style ────────────────────────────────────────────────────────────


@app.command(name="analyze-style")
def analyze_style(directory: str):
    """Analyze writing style from example documents."""
    from writer_agent.analysis.parser import parse_directory
    from writer_agent.analysis.style import StyleAnalyzer

    dir_path = Path(directory)
    if not dir_path.exists():
        console.print(f"[red]Directory not found:[/red] {directory}")
        raise typer.Exit(1)

    docs = parse_directory(dir_path)
    if not docs:
        console.print("[red]No documents found.[/red]")
        raise typer.Exit(1)

    analyzer = StyleAnalyzer()
    all_text = "\n\n".join(docs.values())
    result = analyzer.analyze(all_text)

    console.print(f"\n[bold]Style Analysis[/bold] ({len(docs)} documents, {result['total_words']} words)")
    console.print(f"Avg sentence length: {result['avg_sentence_length']:.1f} words")
    console.print(f"Dialogue ratio: {result['dialogue_ratio']:.1%}")
    console.print(f"POV style: {result['pov_style']}")

    if result["frequent_words"]:
        console.print(f"\n[bold]Frequent words:[/bold] {', '.join(result['frequent_words'][:15])}")

    # Save to DB
    db = _get_db()
    from writer_agent.db.repositories import StyleProfileRepo

    StyleProfileRepo(db).create(
        name=f"style_{dir_path.name}",
        source_files=list(docs.keys()),
        analysis=result,
        sample_passages=result["sample_passages"],
    )
    console.print("\n[green]Style profile saved.[/green]")


# ── export ───────────────────────────────────────────────────────────────────


@app.command()
def export(title: str, fmt: str = "md"):
    """Export novel to file (md, txt, or docx)."""
    db = _get_db()
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo
    from writer_agent.export.exporter import Exporter

    project = ProjectRepo(db).get_by_name(title)
    if not project:
        console.print(f"[red]Project not found:[/red] {title}")
        raise typer.Exit(1)

    pid = project["id"]
    chapters = ChapterRepo(db).list_by_project(pid)
    if not chapters:
        console.print("[red]No chapters to export.[/red]")
        raise typer.Exit(1)

    from writer_agent.config import Config

    config = Config.from_env()
    config.output_dir.mkdir(parents=True, exist_ok=True)

    ext = {"md": ".md", "txt": ".txt", "docx": ".docx"}.get(fmt, ".md")
    output_path = config.output_dir / f"{title}{ext}"

    exporter = Exporter(ChapterRepo(db))
    if fmt == "txt":
        exporter.to_txt(pid, output_path, title=title)
    elif fmt == "docx":
        exporter.to_docx(pid, output_path, title=title)
    else:
        exporter.to_markdown(pid, output_path, title=title)

    console.print(f"[green]Exported to:[/green] {output_path}")
