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
    from writer_agent.settings import Settings
    from writer_agent.db.database import Database

    settings = Settings.load()
    db_path = path or settings.db_path
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
    from writer_agent.settings import Settings
    from writer_agent.llm.client import LLMClient
    from writer_agent.engine.brainstorm import BrainstormEngine

    config = Settings.load()
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
    from writer_agent.settings import Settings
    from writer_agent.llm.client import LLMClient
    from writer_agent.engine.context import ContextBuilder
    from writer_agent.engine.generator import ChapterGenerator
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo

    config = Settings.load()
    llm = LLMClient(config)
    project = ProjectRepo(db).get_by_name(title)
    if not project:
        console.print(f"[red]Project not found:[/red] {title}")
        raise typer.Exit(1)

    pid = project["id"]
    latest = ChapterRepo(db).get_latest(pid)
    next_ch = (latest["chapter_number"] + 1) if latest else 1

    ctx = ContextBuilder(db, settings=config)
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
    from writer_agent.settings import Settings
    from writer_agent.llm.client import LLMClient
    from writer_agent.engine.context import ContextBuilder
    from writer_agent.engine.generator import ChapterGenerator
    from writer_agent.db.repositories import ProjectRepo, ChapterRepo

    config = Settings.load()
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

    ctx = ContextBuilder(db, settings=config)
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

    from writer_agent.settings import Settings

    config = Config.from_env()
    config.output_dir_path.mkdir(parents=True, exist_ok=True)

    ext = {"md": ".md", "txt": ".txt", "docx": ".docx"}.get(fmt, ".md")
    output_path = config.output_dir_path / f"{title}{ext}"

    exporter = Exporter(ChapterRepo(db))
    if fmt == "txt":
        exporter.to_txt(pid, output_path, title=title)
    elif fmt == "docx":
        exporter.to_docx(pid, output_path, title=title)
    else:
        exporter.to_markdown(pid, output_path, title=title)

    console.print(f"[green]Exported to:[/green] {output_path}")


# ── config ───────────────────────────────────────────────────────────────────


config_app = typer.Typer(
    name="config",
    help="Manage settings (set, get, list, show, reset)",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


def _load_settings():
    from writer_agent.settings import Settings
    return Settings.load()


@config_app.command("set")
def config_set(key: str, value: str, scope: str = typer.Option("local", "--scope", "-s", help="global or local")):
    """Set a configuration value. Example: writer-agent config set generation.temperature 0.9"""
    settings = _load_settings()
    try:
        settings.set_value(key, value, scope=scope)
        settings.save(scope=scope)
        val, src = settings.get_value(key)
        console.print(f"[green]Set[/green] {key} = {val} (scope: {scope})")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@config_app.command("get")
def config_get(key: str):
    """Get a configuration value with its source."""
    settings = _load_settings()
    try:
        value, source = settings.get_value(key)
        source_style = {"default": "dim", "global": "blue", "local": "green", "env": "yellow", "api": "magenta"}.get(source, "white")
        console.print(f"{key} = {value}  [{source_style}]{source}[/]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@config_app.command("list")
def config_list(scope: str = typer.Option("", "--scope", "-s", help="Filter by source: global, local, env, api")):
    """List all configuration values with sources."""
    settings = _load_settings()
    rows = settings.all_keys()

    table = Table(title="WriterAgent Settings")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Source", style="green")

    for section, key, value, source in rows:
        if scope and source != scope:
            continue
        source_style = {"default": "dim", "global": "blue", "local": "green", "env": "yellow", "api": "magenta"}.get(source, "white")
        display_val = str(value) if value != 0 or key.endswith("_tokens") else "—"
        table.add_row(f"{section}.{key}", display_val, f"[{source_style}]{source}[/]")

    console.print(table)


@config_app.command("show")
def config_show():
    """Pretty-print all settings grouped by section with source colors."""
    settings = _load_settings()
    rows = settings.all_keys()

    source_legend = "[dim](df)[/dim]efault  [blue](glb)[/blue]al  [green](loc)[/green]al  [yellow](env)[/yellow]  [magenta](api)[/magenta]"

    current_section = None
    for section, key, value, source in rows:
        if section != current_section:
            console.print(f"\n[bold][{section}][/bold]")
            current_section = section
        source_tag = {"default": "dim", "global": "blue", "local": "green", "env": "yellow", "api": "magenta"}.get(source, "white")
        console.print(f"  {key:30s} {str(value):20s} [{source_tag}]({source[:3]})[/{source_tag}]")

    console.print(f"\nSources: {source_legend}")


@config_app.command("reset")
def config_reset(key: str, scope: str = typer.Option("local", "--scope", "-s")):
    """Reset a setting to its default (remove from TOML file)."""
    settings = _load_settings()
    try:
        settings.unset_key(key, scope=scope)
        # Reload to show the reverted value
        settings = _load_settings()
        value, source = settings.get_value(key)
        console.print(f"[green]Reset[/green] {key} → {value} (now from: {source})")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
