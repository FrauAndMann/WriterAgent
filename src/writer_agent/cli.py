import typer
from rich.console import Console

app = typer.Typer(
    name="writer-agent",
    help="CLI agent for writing dark romance novels with LM Studio",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version():
    """Show version."""
    from writer_agent import __version__

    console.print(f"WriterAgent v{__version__}")
