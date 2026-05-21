"""
ui.py
Primitives d'affichage
"""

from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple, Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import FloatPrompt, IntPrompt, Prompt
from rich.table import Table
from rich import box as rich_box
from rich.console import Console, RenderableType


# --- Console (usage interne uniquement) --------------------------------------

_console = Console()


# --- Prompts -----------------------------------------------------------------

class _NicePrompt(Prompt):
    prompt_suffix = ">>> "


class _NiceIntPrompt(IntPrompt):
    prompt_suffix = " ? "


class _NiceFloatPrompt(FloatPrompt):
    prompt_suffix = " ? "


# --- Affichage divers --------------------------------------------------------

def print_error(message: str) -> None:
    _console.print(f":rotating_light: [red]{message}[/red]")


def print_info(message: str) -> None:
    _console.print(f"[dim]{message}[/dim]")


def print_message(label: str, content: str, label_style: str = "cyan") -> None:
    _console.print(f"[{label_style}]{label}[/{label_style}] : {content}")


def print_text_panel(content: str, border_style: str = "") -> None:
    _console.print()
    _console.print(Panel(content, expand=False, border_style=border_style or "default"))
    _console.print()


def print_key_value_panel(title: str, rows: List[Tuple[str, str]], border_style: str = "") -> None:
    table = Table(title=title, show_header=False, box=None)
    table.add_column(style="bold")
    table.add_column(style="cyan")
    for key, value in rows:
        table.add_row(key, value)
    _console.print()
    _console.print(Panel(table, expand=False, border_style=border_style or "default"))
    _console.print()


def print_compare_table(
    question: str,
    columns: List[Tuple[str, str]],
    results: Dict[Tuple[str, str], Dict[str, str]],
):
    title = f":mag: [italic]{question[:80]}{'…' if len(question) > 80 else ''}[/italic]"

    table = Table(
        title=title,
        box=rich_box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        expand=True,
    )

    table.add_column("Champ", style="bold", no_wrap=True)

    for provider, model in columns:
        table.add_column(
            f"{provider}\n[dim]{model}[/dim]",
            ratio=1,
            overflow="fold",
        )

    status_row = ["Statut"]
    elapsed_row = ["Temps"]
    tokens_row = ["Tokens"]
    reply_row = ["Réponse"]

    for key in columns:
        item = results.get(key, {})
        status_row.append(item.get("status", "En attente"))
        elapsed_row.append(item.get("elapsed", "-"))
        tokens_row.append(item.get("tokens", "-"))
        reply_row.append(item.get("reply", "..."))

    table.add_row(*status_row)
    table.add_row(*elapsed_row)
    table.add_row(*tokens_row)
    table.add_row(*reply_row)

    return table


# --- Saisie ------------------------------------------------------------------

def ask_text(prompt_label: str) -> Optional[str]:
    try:
        value = Prompt.ask(f"[bold green]{prompt_label}[/bold green]").strip()
        return value if value else None
    except (EOFError, KeyboardInterrupt):
        _console.print()
        return None


def ask_int(prompt_label: str, default: int) -> Optional[int]:
    try:
        return _NiceIntPrompt.ask(prompt_label, default=default)
    except (EOFError, KeyboardInterrupt):
        _console.print()
        return None


def ask_float(prompt_label: str, default: float) -> Optional[float]:
    try:
        return _NiceFloatPrompt.ask(prompt_label, default=default)
    except (EOFError, KeyboardInterrupt):
        _console.print()
        return None


def ask_command(prompt_label: str = "\n") -> Optional[str]:
    return _NicePrompt.ask(prompt_label, default="", show_default=False).strip().lower()


def select_from_list(title: str, items: List[str], current: str = "") -> Optional[int]:
    table = Table(title=title, header_style="bold", box=None)
    table.add_column("#", style="bold")
    table.add_column("Choix")
    table.add_column("")
    for i, item in enumerate(items, 1):
        marker = ":white_check_mark:" if item == current else ""
        table.add_row(str(i), item, marker)
    table.add_row("0", "Annuler", "")
    _console.print()
    _console.print(Panel(table, expand=False))
    _console.print()

    choice = ask_int("Choix", default=0)
    if choice is None or choice == 0:
        return None
    if not (1 <= choice <= len(items)):
        print_error("Choix invalide")
        return None
    return choice - 1


# --- Utilitaires -------------------------------------------------------------

@contextmanager
def spinner(message: str) -> Generator:
    with _console.status(message):
        yield