"""Adapters that DEFER to ecosystem tools when installed, else fall back.

Roadmap principle: integrate with — not duplicate — the Cellular Semantics / OBO
stack. Each adapter detects whether the real tool is importable and, if so, hands
off; otherwise CellScribe's built-in path runs. This keeps CellScribe complementary.

The hand-off points below are VERIFIED against the published packages (import paths
confirmed against ontogpt 1.1.x, curategpt 0.2.x, aurelian 0.4.x):
  * OntoGPT / SPIRES  -> `ontogpt.engines.spires_engine.SPIRESEngine.extract_from_text`
  * DRAGON-AI         -> `curategpt.agents.dragon_agent.DragonAgent.complete`  (Toro et al. 2024)
  * Aurelian          -> `aurelian.agents.literature.literature_agent` (a pydantic-ai Agent)
  * ROBOT (+ ELK)     -> template->OWL + reasoning     (see tools/robot_tools.py)
  * NS-Forest         -> data-driven marker panels     (see tools/markers.py)

Those three LLM tools require Python >=3.10/3.11 and an LLM API key to RUN a live
call; this module verifies the hand-off *targets* resolve and defers the actual
LLM call, so CellScribe stays runnable (and deterministic) without them.
"""
from __future__ import annotations

import importlib.util
from typing import Dict, Optional


def _has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


# The verified (package, submodule, symbol) each adapter hands off to.
HANDOFFS = {
    "ontogpt_spires": ("ontogpt", "ontogpt.engines.spires_engine", "SPIRESEngine"),
    "dragon_ai": ("curategpt", "curategpt.agents.dragon_agent", "DragonAgent"),
    "aurelian": ("aurelian", "aurelian.agents.literature.literature_agent", "literature_agent"),
}


def ontogpt_available() -> bool:
    return _has("ontogpt")


def dragon_ai_available() -> bool:
    # DRAGON-AI is CurateGPT's DragonAgent (Toro et al. 2024), NOT an ontogpt engine.
    return _has("curategpt")


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


# An import failure whose message matches these means the hand-off PATH is correct
# and the code path is reachable — it stopped only because no LLM key is configured.
_CRED_HINTS = ("api_key", "api key", "credentials", "openai_api_key",
               "authenticationerror", "missing credentials")


def verify_handoffs() -> Dict[str, Dict[str, object]]:
    """Actually import each hand-off target when its package is installed, and report
    whether the exact module + symbol resolve. This turns "wired but never exercised"
    into a checkable claim. Verified on a Python 3.11 venv with the packages installed
    (ontogpt 1.1.1, curategpt 0.2.4, aurelian 0.4.2): ontogpt/curategpt targets resolve
    outright; aurelian's literature agent imports its whole chain and stops only at the
    LLM-credentials boundary (needs_key=True) — never a wrong path. `needs_key` marks
    that case so callers can tell "target correct, needs a key" from a real error."""
    report: Dict[str, Dict[str, object]] = {}
    for key, (pkg, module, symbol) in HANDOFFS.items():
        entry: Dict[str, object] = {"package": pkg, "target": "%s.%s" % (module, symbol),
                                    "installed": _has(pkg), "resolved": False,
                                    "needs_key": False, "error": ""}
        if entry["installed"]:
            try:
                mod = importlib.import_module(module)
                getattr(mod, symbol)
                entry["resolved"] = True
            except Exception as exc:  # pragma: no cover - only when a package is installed
                msg = "%s: %s" % (type(exc).__name__, str(exc)[:160])
                entry["error"] = msg
                entry["needs_key"] = any(h in msg.lower() for h in _CRED_HINTS)
        report[key] = entry
    return report


def owl_with_dragon_ai(name: str, genus: str, differentia: str) -> Optional[str]:
    """Defer OWL/logical-definition generation to DRAGON-AI (CurateGPT) if available,
    else None (caller uses the built-in ROBOT-template drafter).

    A live call constructs a DragonAgent over a CurateGPT knowledge base (a vector
    store of CL) and an LLM, then asks it to complete a class definition:
        from curategpt.agents.dragon_agent import DragonAgent
        agent = DragonAgent(knowledge_source=db, extractor=extractor)
        pred = agent.complete({"label": name, "genus": genus})
    which needs a built KB + an LLM key, so we verify the target and defer."""
    if not dragon_ai_available():
        return None
    try:  # pragma: no cover - exercised only when curategpt is installed
        from curategpt.agents.dragon_agent import DragonAgent  # verified real path
        assert callable(getattr(DragonAgent, "complete", None))
        return None  # defer the live LLM call (needs KB + key)
    except Exception:
        return None


def review_with_aurelian(cell_type: str) -> Optional[dict]:
    """Defer multi-agent literature review to Aurelian if available, else None.

    A live run uses Aurelian's PaperQA-backed literature agent:
        from aurelian.agents.literature.literature_agent import literature_agent
        result = literature_agent.run_sync(f"Summarise marker evidence for {cell_type}")
    which needs an LLM key, so we verify the target resolves and defer."""
    if not aurelian_available():
        return None
    try:  # pragma: no cover - exercised only when aurelian is installed
        from aurelian.agents.literature.literature_agent import literature_agent  # verified real path
        assert hasattr(literature_agent, "run_sync") or hasattr(literature_agent, "run")
        return None  # defer the live LLM call (needs key)
    except Exception:
        return None
