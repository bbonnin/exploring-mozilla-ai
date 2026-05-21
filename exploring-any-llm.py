"""
main.py
Point d'entrée et boucle REPL
"""

import sys
import time
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.live import Live
import ui
import ai


# --- Commandes ---------------------------------------------------------------

def show_help() -> None:
    ui.print_key_value_panel("Commandes", [
        ("chat",              "Démarrer ou reprendre une conversation (mono-modèle)"),
        ("compare",           "Comparer les réponses de plusieurs modèles"),
        ("setmodel",          "Changer de fournisseur ou de modèle actif"),
        ("settings",          "Configurer température, max_tokens"),
        ("loadmodels",        "Charger les modèles disponibles des fournisseurs"),
        ("status",            "Afficher la configuration actuelle"),
        ("reset",             "Effacer l'historique de conversation"),
        ("help",              "Afficher ce message"),
        ("exit / quit / bye", "Quitter le programme"),
    ])


def show_status() -> None:
    if not ai.is_model_configured():
        ui.print_error("Aucun fournisseur/modèle configuré, utilisez 'setmodel'")
        return
    ui.print_key_value_panel("État courant", [
        ("Fournisseur", ai.get_active_provider()),
        ("Modèle",      ai.state["model"]),
        ("Messages",    f"{len(ai.state['history']) // 2} échanges en mémoire"),
        ("Température", str(ai.state["temperature"])),
        ("Max tokens",  str(ai.state["max_tokens"])),
    ])


def configure_settings() -> None:
    ui.print_key_value_panel("Paramètres actuels", [
        ("Température", str(ai.state["temperature"])),
        ("Max tokens",  str(ai.state["max_tokens"])),
    ])
    ui.print_info("Appuyez sur Entrée pour conserver la valeur actuelle")

    new_temp = ui.ask_float(
        f"Température [dim](0.0 – 2.0, actuel : {ai.state['temperature']})[/dim]",
        default=ai.state["temperature"],
    )
    if new_temp is not None:
        ai.state["temperature"] = round(max(0.0, min(2.0, new_temp)), 2)

    new_max = ui.ask_int(
        f"Max tokens [dim](actuel : {ai.state['max_tokens']})[/dim]",
        default=ai.state["max_tokens"],
    )
    if new_max is not None:
        ai.state["max_tokens"] = max(1, new_max)

    ui.print_text_panel(
        f":wrench: [bold green]Paramètres mis à jour[/bold green]\n"
        f"Température : {ai.state['temperature']}\n"
        f"Max tokens  : {ai.state['max_tokens']}",
        border_style="green",
    )


def _select_provider(active: str = "") -> Optional[str]:
    providers = ai.get_providers()
    active_label = next((label for key, label in providers if key == active), "")
    idx = ui.select_from_list(
        "[not italic]:office_building:[/not italic] Fournisseurs disponibles",
        [label for _, label in providers],
        current=active_label,
    )
    return providers[idx][0] if idx is not None else None


def _select_model(provider_key: str, display_current: bool = True) -> Optional[str]:
    models = ai.get_models(provider_key)
    if not models:
        ui.print_error(f"Aucun modèle chargé pour '{provider_key}', lancez 'loadmodels' d'abord")
        return None
    current = (
        ai.state["model"]
        if display_current and provider_key == ai.state["provider"]
        else ""
    )
    idx = ui.select_from_list("[not italic]:brain:[/not italic] Modèles disponibles", models, current=current)
    return models[idx] if idx is not None else None


def change_model() -> None:
    chosen_provider = _select_provider(ai.state["provider"])
    if not chosen_provider:
        return
    chosen_model = _select_model(chosen_provider)
    if not chosen_model:
        return

    ai.set_active_model(chosen_provider, chosen_model)

    ui.print_text_panel(
        f":brain: [bold green]Modèle sélectionné[/bold green]\n"
        f"{ai.get_active_provider()} / {chosen_model}\n"
        f"[dim]Historique réinitialisé[/dim]",
        border_style="green",
    )


def load_models() -> None:
    with ui.spinner("Chargement des modèles en cours..."):
        for provider_key, provider_label in ai.get_providers():
            try:
                model_ids = ai.fetch_models(provider_key)
                ui.print_info(f":brain: {provider_label} — {len(model_ids)} modèles chargés")
                for mid in model_ids:
                    ui.print_info(f"  - {mid}")
            except Exception as e:
                ui.print_error(f"Erreur pour '{provider_label}' : {e}")


def clear_history() -> None:
    ai.state["history"].clear()
    ui.print_info("Historique effacé")


# --- Mode chat simple --------------------------------------------------------

def mode_chat() -> None:
    if not ai.is_model_configured():
        ui.print_error("Aucun modèle configuré, utilisez 'setmodel'")
        return
 
    ui.print_text_panel(
        f":speech_balloon: [bold cyan]Mode CHAT[/bold cyan]\n"
        f"[dim]{ai.get_active_provider()} / {ai.state['model']}  |  "
        f"temp={ai.state['temperature']}  max_tokens={ai.state['max_tokens']}[/dim]\n\n"
        f"Tapez votre message. Commandes : [bold]/reset[/bold]  [bold]/bye[/bold]",
        border_style="cyan",
    )
 
    while True:
        user_input = ui.ask_text("Vous")
        if user_input is None:
            break
 
        if user_input.lower() == "/bye":
            ui.print_info("Sortie du chat")
            break
 
        if user_input.lower() == "/reset":
            clear_history()
            continue
 
        ai.state["history"].append({"role": "user", "content": user_input})
        try:
            with ui.spinner("Réflexion en cours..."):
                reply = ai.complete(
                    ai.state["provider"],
                    ai.state["model"],
                    ai.state["history"],
                    ai.state["temperature"],
                    ai.state["max_tokens"],
                )
            ai.state["history"].append({"role": "assistant", "content": reply})
            ui.print_message("Réponse", reply)
        except Exception as e:
            ai.state["history"].pop()
            ui.print_error(f"Erreur lors de la complétion : {e}")
 

# --- Mode comparaison --------------------------------------------------------

def _select_models_for_compare() -> List[Tuple[str, str]]:
    selected: List[Tuple[str, str]] = []

    ui.print_text_panel(
        ":brain: [bold cyan]Sélection des modèles à comparer[/bold cyan]\n"
        "[dim]Ajoutez autant de modèles que souhaité. Entrez 0 pour terminer.[/dim]",
        border_style="cyan",
    )

    while True:
        if selected:
            providers_by_key = {prov: label for prov, label, *_ in ai.get_providers()}
            ui.print_key_value_panel(
                "Modèles sélectionnés",
                [
                    (f"{i}.", f"{providers_by_key[prov]} / {model}")
                    for i, (prov, model) in enumerate(selected, 1)
                ],
            )

        action = ui.ask_int(
            "[bold]Ajouter un modèle ?[/bold] [dim](1 = oui, 0 = terminer)[/dim]",
            default=1 if not selected else 0,
        )
        if action is None or action == 0:
            break

        provider_key = _select_provider()
        if not provider_key:
            continue

        model = _select_model(provider_key, False)
        if not model:
            continue

        pair = (provider_key, model)
        if pair in selected:
            ui.print_info("Ce modèle est déjà dans la liste.")
        else:
            selected.append(pair)
            providers = dict(ai.get_providers())
            ui.print_info(f"Ajouté : {providers[provider_key]} / {model}")

    return selected


def _query_model(
    provider_key: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
) -> Tuple[str, str, str]:
    start = time.perf_counter()

    try:
        result = ai.complete_with_metadata(provider_key, model, messages, temperature, max_tokens)
        elapsed = f"{time.perf_counter() - start:.2f} s"
        total_tokens = result.get("total_tokens")
        tokens = str(total_tokens) if total_tokens is not None else "—"

        return provider_key, model, {
            "status": "Terminé",
            "elapsed": elapsed,
            "tokens": tokens,
            "reply": result.get("reply", ""),
        }

    except Exception as e:
        elapsed = f"{time.perf_counter() - start:.2f} s"
        return provider_key, model, {
            "status": "Erreur",
            "elapsed": elapsed,
            "tokens": "—",
            "reply": f"Erreur : {e}",
        }


def mode_compare() -> None:
    from rich.live import Live

    selected = _select_models_for_compare()

    if len(selected) < 2:
        ui.print_error("Il faut au moins 2 modèles pour une comparaison.")
        return

    providers_map = dict(ai.get_providers())

    ui.print_text_panel(
        f":bar_chart: [bold cyan]Mode COMPARE[/bold cyan]\n"
        f"[dim]{len(selected)} modèles | "
        f"temp={ai.state['temperature']} max_tokens={ai.state['max_tokens']}[/dim]\n\n"
        f"Tapez votre question. Commande : [bold]/bye[/bold]",
        border_style="cyan",
    )

    while True:
        user_input = ui.ask_text("Question")
        if user_input is None:
            break

        if user_input.lower() == "/bye":
            ui.print_info("Sortie du mode comparaison")
            break

        messages = [{"role": "user", "content": user_input}]

        ordered_columns = [(providers_map[prov], model) for prov, model in selected]
        key_map = {
            (providers_map[prov], model): (prov, model)
            for prov, model in selected
        }

        results: Dict[Tuple[str, str], Dict[str, str]] = {
            (providers_map[prov], model): {
                "status": "En attente",
                "elapsed": "-",
                "tokens": "-",
                "reply": "...",
            }
            for prov, model in selected
        }

        with ThreadPoolExecutor(max_workers=len(selected)) as executor:
            futures = {
                executor.submit(
                    _query_model,
                    prov,
                    model,
                    messages,
                    ai.state["temperature"],
                    ai.state["max_tokens"],
                ): (prov, model)
                for prov, model in selected
            }

            with Live(
                ui.print_compare_table(user_input, ordered_columns, results),
                console=ui._console,
                refresh_per_second=4,
                vertical_overflow="visible",
            ) as live:
                for future in as_completed(futures):
                    prov, model, result = future.result()
                    display_key = (providers_map[prov], model)

                    results[display_key] = {
                        "status": result.get("status", "Terminé"),
                        "elapsed": result.get("elapsed", "-"),
                        "tokens": result.get("tokens", "-"),
                        "reply": result.get("reply", ""),
                    }

                    live.update(
                        ui.print_compare_table(user_input, ordered_columns, results)
                    )


# --- Boucle principale -------------------------------------------------------

def main() -> None:
    ui.print_info("\nBonjour !\n")

    try:
        ai.init_state()
    except ValueError as e:
        ui.print_error(str(e))

    show_help()

    while True:
        try:
            cmd = ui.ask_command()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

        if not cmd:
            continue

        match cmd:
            case "chat":
                mode_chat()
            case "compare":
                mode_compare()
            case "setmodel":
                change_model()
            case "settings":
                configure_settings()
            case "loadmodels":
                load_models()
            case "status":
                show_status()
            case "reset":
                clear_history()
            case "help":
                show_help()
            case "exit" | "quit" | "q" | "bye":
                sys.exit(0)
            case _:
                ui.print_error(f"Commande inconnue : '{cmd}'")
                show_help()


if __name__ == "__main__":
    main()
