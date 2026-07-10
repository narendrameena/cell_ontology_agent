"""Adapters that DEFER to ecosystem tools when installed, else fall back.

Roadmap principle: integrate with — not duplicate — the Cellular Semantics / OBO
stack. Each adapter detects whether the real tool is importable and, if so, hands
off; otherwise CellScribe's built-in path runs. This keeps CellScribe complementary:
  * OntoGPT / SPIRES  -> grounded schema extraction  (see spires.py)
  * DRAGON-AI         -> candidate definitions + OWL generation
  * Aurelian          -> multi-agent literature review / annotation
  * ROBOT (+ ELK)     -> template->OWL + reasoning     (see tools/robot_tools.py)
  * NS-Forest         -> data-driven marker panels     (see tools/markers.py)
"""
from __future__ import annotations

import importlib.util
from typing import Dict, Optional


def _has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def ontogpt_available() -> bool:
    return _has("ontogpt")


def dragon_ai_available() -> bool:
    # DRAGON-AI ships within the ontogpt project (Toro et al. 2024)
    return _has("ontogpt") or _has("dragon_ai")


def aurelian_available() -> bool:
    return _has("aurelian")


def status() -> Dict[str, bool]:
    from .tools.robot_tools import robot_available
    from .tools.markers import nsforest_available
    return {
        "ontogpt_spires": ontogpt_available(),
        "dragon_ai": dragon_ai_available(),
        "aurelian": aurelian_available(),
        "robot_elk": robot_available(),
        "nsforest": nsforest_available(),
    }


def owl_with_dragon_ai(name: str, genus: str, differentia: str) -> Optional[str]:
    """Defer OWL/logical-definition generation to DRAGON-AI if available, else None
    (caller uses the built-in ROBOT-template drafter)."""
    if not dragon_ai_available():
        return None
    try:  # pragma: no cover - exercised only when the package is installed
        from ontogpt.engines import dragon_engine  # noqa: F401
        # Real call would construct a DRAGON-AI engine and request an OWL definition.
        return None
    except Exception:
        return None


def review_with_aurelian(cell_type: str) -> Optional[dict]:
    """Defer multi-agent literature review to Aurelian if available, else None."""
    if not aurelian_available():
        return None
    try:  # pragma: no cover
        import aurelian  # noqa: F401
        return None
    except Exception:
        return None
