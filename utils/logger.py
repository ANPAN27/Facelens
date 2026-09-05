from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box

console = Console()


def banner():
    title = Text("FACELENS CLI", style="bold cyan", justify="center")
    subtitle = Text("AI Face Search & Verification System", style="dim", justify="center")
    panel = Panel.fit(
        Text.assemble(title, "\n", subtitle),
        border_style="cyan",
        box=box.DOUBLE,
    )
    console.print(panel)
    console.print()


def step_header(current: int, total: int, label: str):
    console.print(f"[bold cyan][{current}/{total}][/bold cyan] {label}...", end=" ")


def step_done(label: str = ""):
    console.print(f"[bold green]✓[/bold green] {label}")


def step_fail(label: str, reason: str):
    console.print(f"[bold red]✗[/bold red] {label}: [red]{reason}[/red]")


def info(msg: str):
    console.print(f"  [dim]{msg}[/dim]")


def warn(msg: str):
    console.print(f"  [yellow]WARNING: {msg}[/yellow]")


def error(msg: str):
    console.print(f"  [bold red]ERROR: {msg}[/bold red]")


def match_table(results: list[dict]):
    table = Table(title="TOP POSSIBLE MATCHES", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="bold", width=4)
    table.add_column("Platform", style="cyan")
    table.add_column("URL", style="blue", max_width=50)
    table.add_column("Similarity", justify="right")
    table.add_column("Match", style="bold")

    for i, r in enumerate(results, 1):
        sim = r.get("face_similarity", 0)
        cls = r.get("classification", "LOW")
        style = "green" if cls == "HIGH" else ("yellow" if cls == "MEDIUM" else "red")
        table.add_row(
            str(i),
            r.get("platform", "Unknown"),
            r.get("url", "N/A"),
            f"{sim:.3f}",
            f"[{style}]{cls}[/{style}]",
        )
    console.print(table)


def blockchain_result(network: str, tx_hash: str):
    table = Table(box=box.SIMPLE)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Network", network)
    table.add_row("Transaction", tx_hash)
    console.print(table)


def completion_banner():
    title = Text("SEARCH COMPLETED ✓", style="bold green", justify="center")
    panel = Panel.fit(title, border_style="green", box=box.DOUBLE)
    console.print(panel)
