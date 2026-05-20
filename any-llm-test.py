import os
import sys
from typing import List, Dict
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.text import Text


load_dotenv()


PROVIDERS = {
    provider.strip().lower(): {"label": provider.strip().capitalize(), "models": []}
    for provider in os.getenv("PROVIDERS", "").split(",") if provider.strip()
}


state: Dict[str, object] = {
    "provider": "",
    "model": "",
    "history": [],
}


console = Console()


class NicePrompt(Prompt):
    prompt_suffix = ">>> "


class NiceIntPrompt(IntPrompt):
    prompt_suffix = " ? "


def print_with_margins(something):
    console.print()
    console.print(something)
    console.print()


def show_status() -> None:
    prov = PROVIDERS[state["provider"]]["label"]
    model = state["model"]
    turns = len(state["history"]) // 2
    table = Table(title="État courant", show_header=False, box=None)
    table.add_column(style="bold")
    table.add_column(style="cyan")
    table.add_row("Fournisseur", f"{prov}")
    table.add_row("Modèle", f"{model}")
    table.add_row("Messages", f"{turns} échanges en mémoire")
    print_with_margins(Panel(table, expand=False))


def show_help() -> None:
    table = Table(title="Commandes", show_header=False, box=None)
    table.add_column(style="bold")
    table.add_column(style="cyan")
    table.add_row("chat", "Démarrer ou reprendre une conversation")
    table.add_row("model", "Changer de fournisseur ou de modèle")
    table.add_row("status", "Afficher la configuration actuelle")
    table.add_row("reset", "Effacer l'historique de conversation")
    table.add_row("help", "Afficher ce message")
    table.add_row("exit", "Quitter le programme")
    print_with_margins(Panel(table, expand=False))


def select_provider() -> str | None:
    provider_keys = list(PROVIDERS.keys())
    table = Table(title="[not italic]:office_building:[/not italic] Fournisseurs disponibles", header_style="bold", box=None)
    table.add_column("#", style="bold")
    table.add_column("Fournisseur")
    table.add_column("Actuel")

    for i, key in enumerate(provider_keys, 1):
        info = PROVIDERS[key]
        current = ":white_check_mark:" if key == state["provider"] else ""
        table.add_row(str(i), info["label"], current)

    table.add_row("0", "Annuler", "", "")
    print_with_margins(Panel(table, expand=False))

    try:
        choice = NiceIntPrompt.ask("Fournisseur", default=0)
    except (EOFError, KeyboardInterrupt):
        console.print()
        return None

    if choice == 0:
        return None

    idx = choice - 1
    if not (0 <= idx < len(provider_keys)):
        console.print("[red]Choix invalide.[/red]")
        return None

    return provider_keys[idx]


def select_model(chosen_provider: str) -> str | None:
    models = PROVIDERS[chosen_provider]["models"]
    table = Table(title=f"[not italic]:brain:[/not italic] Modèles disponibles", header_style="bold", box=None)
    table.add_column("#", style="bold")
    table.add_column("Modèle")
    table.add_column("Actuel")

    for i, model in enumerate(models, 1):
        current = ":white_check_mark:" if model == state["model"] and chosen_provider == state["provider"] else ""
        table.add_row(str(i), model, current)

    table.add_row("0", "Annuler", "")
    print_with_margins(Panel(table, expand=False))

    try:
        choice = NiceIntPrompt.ask("Modèle", default=0)
    except (EOFError, KeyboardInterrupt):
        console.print()
        return None

    if choice == 0:
        return None

    idx = choice - 1
    if not (0 <= idx < len(models)):
        console.print("[red]Choix invalide.[/red]")
        return None

    return models[idx]


def change_model() -> None:
    chosen_provider = select_provider()
    if not chosen_provider:
        return

    chosen_model = select_model(chosen_provider)
    if not chosen_model:
        return

    state["provider"] = chosen_provider
    state["model"] = chosen_model
    state["history"].clear()

    prov_label = PROVIDERS[chosen_provider]["label"]
    print_with_margins(Panel(
        f":brain: [bold green]Modèle sélectionné[/bold green]\n{prov_label} / {state['model']}\n[dim]Historique de conversation réinitialisé[/dim]",
        border_style="green", expand=False
    ))


def load_models():
    from any_llm import AnyLLM
    providers = list(PROVIDERS.keys())
    for provider in providers:
        try:
            llm = AnyLLM.create(provider)
            models = llm.list_models()
            console.print(f"\n[green]Modèles disponibles pour '{provider}':[/green]")
            modelIds = [model.id for model in models]
            PROVIDERS[provider]['models'] = modelIds
            for model in modelIds:
                console.print(f"  - [green]{model}[/green]")
        except Exception as e:
            console.print(f":rotating_light: [red]Erreur lors du chargement des modèles de '{provider}' : {e}[/red]")


def main() -> None:
    console.print("\n[cyan]Bonjour ![/cyan]\n")

    with console.status("Chargement des modèles disponibles en cours...") as status:
        load_models()

    while True:
        try:
            cmd = NicePrompt.ask("\n", default="", show_default=False).strip().lower()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

        if not cmd:
            continue

        if cmd == "chat":
            mode_chat()
        elif cmd == "model":
            change_model()
        elif cmd == "status":
            show_status()
        elif cmd == "reset":
            state["history"].clear()
            console.print("[yellow]Historique effacé.[/yellow]")
        elif cmd == "help":
            show_help()
        elif cmd == "exit" or cmd == "quit" or cmd == "q" or cmd == "bye":
            sys.exit(0)
        else:
            console.print(f"[red]Commande inconnue : '{cmd}'[/red]")
            show_help()


if __name__ == "__main__":
    main()