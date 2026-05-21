"""
ai.py
Abstraction AI basée sur any-llm, any-agent
"""

import os
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from any_llm import AnyLLM


load_dotenv()


# --- Providers ---------------------------------------------------------------

_providers: Dict[str, Dict] = {
    key.strip().lower(): {"label": key.strip().capitalize(), "models": [], "llm": None}
    for key in os.getenv("PROVIDERS", "").split(",")
    if key.strip()
}


def _get_or_create_llm_instance(provider_key: str):
    provider = _providers[provider_key]
    if provider.get("llm") is None:
        provider["llm"] = AnyLLM.create(provider_key)
    return provider["llm"]


def get_providers() -> List[Tuple[str, str]]:
    return [(k, v["label"]) for k, v in _providers.items()]


def get_models(provider_key: str) -> List[str]:
    return _providers.get(provider_key, {}).get("models", [])


def fetch_models(provider_key: str) -> List[str]:
    provider = _providers[provider_key]
    llm = _get_or_create_llm_instance(provider_key)
    provider["models"] = [m.id for m in llm.list_models()]
    return provider["models"]


# --- État global -------------------------------------------------------------

state: Dict = {}


def init_state() -> None:
    global state
    state = {
        "provider": "",
        "model": "",
        "history": [],
        "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "1.0")),
        "max_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "1024")),
    }

    default_model_raw = os.getenv("DEFAULT_MODEL", "")

    if "/" in default_model_raw:
        provider, model = default_model_raw.split("/", 1)
        state["provider"] = provider.strip().lower()
        state["model"] = model.strip()
    elif default_model_raw:
        raise ValueError("Format de DEFAULT_MODEL invalide dans le .env (attendu : provider/model)")


def set_active_model(provider_key: str, model: str) -> None:
    state["provider"] = provider_key
    state["model"] = model
    state["history"].clear()


def get_active_provider() -> str:
    return _providers.get(state.get("provider", ""), {}).get("label", "")


def is_model_configured() -> bool:
    return bool(state.get("provider")) and bool(state.get("model"))


# --- Complétion --------------------------------------------------------------

def complete(
    provider_key: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
) -> str:
    llm = _get_or_create_llm_instance(provider_key)
    response = llm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def complete_with_metadata(
    provider_key: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
) -> Dict:
    llm = _get_or_create_llm_instance(provider_key)
    response = llm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    usage = getattr(response, "usage", None)

    return {
        "reply": response.choices[0].message.content,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }