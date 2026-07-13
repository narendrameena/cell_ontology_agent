"""Live hand-off to the OBO/Monarch LLM stack (OntoGPT/SPIRES, DRAGON-AI, Aurelian).

Those tools need Python >=3.10/3.11, so they live in a separate virtualenv (built by
`scripts/setup_llm_env.sh`) and CellScribe — which runs on 3.8+ — invokes their CLIs
as subprocesses. This keeps process isolation (no dependency clash) while giving a
genuinely live hand-off.

The LLM backend is pluggable through OntoGPT's litellm layer. The default is Groq's
free tier (`groq/llama-3.3-70b-versatile`), chosen because it needs only a free
`GROQ_API_KEY`; override with `CELLSCRIBE_LLM_MODEL` (e.g. `gpt-4o-mini`,
`anthropic/claude-3-5-haiku-latest`) and the matching provider key.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

DEFAULT_MODEL = os.environ.get("CELLSCRIBE_LLM_MODEL", "groq/llama-3.3-70b-versatile")

# which env var holds the key for a given litellm provider prefix
_PROVIDER_KEY = {
    "groq/": "GROQ_API_KEY",
    "xai/": "XAI_API_KEY",
    "gpt-": "OPENAI_API_KEY",
    "openai/": "OPENAI_API_KEY",
    "o1": "OPENAI_API_KEY",
    "o3": "OPENAI_API_KEY",
    "anthropic/": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini/": "GEMINI_API_KEY",
    "together/": "TOGETHER_API_KEY",
    "mistral/": "MISTRAL_API_KEY",
    "deepseek/": "DEEPSEEK_API_KEY",
}

# where to get a key, per provider (shown in the "needs key" message)
_KEY_HELP = {
    "GROQ_API_KEY": "free tier at https://console.groq.com/keys",
    "XAI_API_KEY": "https://console.x.ai (pay-as-you-go)",
    "OPENAI_API_KEY": "https://platform.openai.com/api-keys",
    "ANTHROPIC_API_KEY": "https://console.anthropic.com/settings/keys",
}

# OpenAI-compatible REST base URL per provider prefix — lets CellScribe (Python 3.8)
# call the LLM directly with `requests`, no venv needed, for the keyless extraction path.
_PROVIDER_BASE = {
    "groq/": "https://api.groq.com/openai/v1",
    "xai/": "https://api.x.ai/v1",
    "openai/": "https://api.openai.com/v1",
    "gpt-": "https://api.openai.com/v1",
    "o1": "https://api.openai.com/v1",
    "o3": "https://api.openai.com/v1",
    "deepseek/": "https://api.deepseek.com",
    "together/": "https://api.together.xyz/v1",
    "cerebras/": "https://api.cerebras.ai/v1",
}


def _base_url_for(model: str) -> str:
    for prefix, url in _PROVIDER_BASE.items():
        if model.startswith(prefix):
            return url
    return os.environ.get("CELLSCRIBE_LLM_BASE", "https://api.openai.com/v1")


def _bare_model(model: str) -> str:
    return model.split("/", 1)[1] if "/" in model else model


def key_var_for(model: str) -> str:
    """Env var holding the API key for `model`'s litellm provider. Falls back to
    OPENAI_API_KEY for unmapped providers (litellm's own default)."""
    for prefix, var in _PROVIDER_KEY.items():
        if model.startswith(prefix):
            return var
    return "OPENAI_API_KEY"


def llm_venv() -> Optional[str]:
    """Locate the persistent Python 3.11 LLM venv (env override, then ./.llm-venv,
    then the dev RAM venv)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for cand in (os.environ.get("CELLSCRIBE_LLM_VENV"),
                 os.path.join(here, ".llm-venv"),
                 "/dev/shm/ogpt_venv"):
        if cand and os.path.exists(os.path.join(cand, "bin", "ontogpt")):
            return cand
    return None


def _bin(name: str) -> Optional[str]:
    v = llm_venv()
    p = os.path.join(v, "bin", name) if v else None
    return p if (p and os.path.exists(p)) else None


def ontogpt_bin() -> Optional[str]:
    return _bin("ontogpt")


def key_present(model: str = DEFAULT_MODEL) -> bool:
    return bool(os.environ.get(key_var_for(model)))


def status(model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    return {"venv": llm_venv(), "ontogpt": ontogpt_bin() is not None,
            "model": model, "key_var": key_var_for(model),
            "key_present": key_present(model)}


def _parse_named_entities(yaml_text: str) -> List[Dict[str, str]]:
    """Light parse of OntoGPT's `named_entities:` block (id + label pairs), so we
    avoid a YAML dependency in the 3.8 env. The raw output is always returned too."""
    ents, cur = [], None
    in_block = False
    for line in (yaml_text or "").splitlines():
        if re.match(r"^named_entities:\s*$", line):
            in_block = True
            continue
        if in_block and re.match(r"^\w", line):  # next top-level key ends the block
            break
        if in_block:
            m = re.match(r"\s*-?\s*id:\s*(\S+)", line)
            if m:
                if cur:
                    ents.append(cur)
                cur = {"id": m.group(1).strip('"\''), "label": ""}
            m = re.match(r"\s*label:\s*(.+)", line)
            if m and cur is not None:
                cur["label"] = m.group(1).strip().strip('"\'')
    if cur:
        ents.append(cur)
    # keep only ontology-grounded CURIEs (PREFIX:LOCAL), drop AUTO:/ungrounded
    return [e for e in ents if re.match(r"^[A-Za-z][A-Za-z0-9]+:[0-9A-Za-z]+$", e["id"])
            and not e["id"].startswith("AUTO:")]


def ontogpt_cell_type(text: str, model: Optional[str] = None,
                      timeout: int = 240) -> Dict[str, Any]:
    """Run OntoGPT's SPIRES engine with the `cell_type` template over `text`,
    LLM-backed by `model` (default Groq free tier). Returns:
      {ok, model, raw, named_entities:[{id,label}], error, needs_key}
    A deterministic caller falls back when ok is False."""
    binp = ontogpt_bin()
    if not binp:
        return {"ok": False, "error": "LLM venv not found — run scripts/setup_llm_env.sh",
                "needs_venv": True}
    model = model or DEFAULT_MODEL
    kvar = key_var_for(model)
    if not os.environ.get(kvar):
        hint = _KEY_HELP.get(kvar, "")
        return {"ok": False, "needs_key": True, "model": model, "key_var": kvar,
                "error": "%s not set for model %s%s"
                         % (kvar, model, (" (%s)" % hint if hint else ""))}
    env = dict(os.environ)
    env.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")  # avoid a network fetch on import
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "input.txt")
        out = os.path.join(tmp, "out.yaml")
        with open(inp, "w") as fh:
            fh.write(text)
        cmd = [binp, "extract", "-t", "cell_type", "-i", inp, "--model", model, "-o", out]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "ontogpt timed out after %ss" % timeout, "model": model}
        raw = ""
        if os.path.exists(out):
            with open(out) as fh:
                raw = fh.read()
        if not raw and proc.returncode != 0:
            return {"ok": False, "model": model,
                    "error": (proc.stderr or proc.stdout or "ontogpt failed")[-500:]}
        return {"ok": True, "model": model, "raw": raw,
                "named_entities": _parse_named_entities(raw)}


# --------------------------------------------------------------------------- direct
# A keyless-grounding live path: CellScribe calls the LLM directly over the provider's
# OpenAI-compatible REST API (via `requests`, so it works in the base 3.8 env with no
# venv), does SPIRES-style schema-constrained extraction, and grounds the result with
# CellScribe's own OLS grounder — no BioPortal key and no multi-GB semsql downloads.

_EXTRACT_SYSTEM = (
    "You are a careful cell-biology ontology curator. From the text, extract a STRICT "
    "JSON object with exactly these keys: "
    '"cell_type" (string), '
    '"transcriptomic_markers" (list of gene symbols), '
    '"surface_markers" (list of cell-surface protein/gene symbols), '
    '"location" (a single anatomical structure), '
    '"functions" (list of Gene-Ontology biological-process names). '
    "Use ONLY facts explicitly stated in the text; use [] or \"\" when absent. "
    "Output ONLY the JSON object — no markdown, no commentary."
)


def _first_json(s: str):
    import json as _json
    m = re.search(r"\{.*\}", s or "", re.S)
    if not m:
        return None
    try:
        return _json.loads(m.group(0))
    except Exception:
        return None


def chat_complete(prompt: str, model: Optional[str] = None, system: Optional[str] = None,
                  timeout: int = 60, max_tokens: int = 800) -> Dict[str, Any]:
    """One chat turn against the provider's OpenAI-compatible endpoint via `requests`."""
    import requests
    model = model or DEFAULT_MODEL
    kvar = key_var_for(model)
    key = os.environ.get(kvar)
    if not key:
        hint = _KEY_HELP.get(kvar, "")
        return {"ok": False, "needs_key": True, "key_var": kvar, "model": model,
                "error": "%s not set%s" % (kvar, (" (%s)" % hint if hint else ""))}
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    try:
        r = requests.post(_base_url_for(model) + "/chat/completions",
                          headers={"Authorization": "Bearer " + key,
                                   "Content-Type": "application/json"},
                          json={"model": _bare_model(model), "messages": msgs,
                                "temperature": 0, "max_tokens": max_tokens},
                          timeout=timeout)
    except Exception as e:  # network/timeout
        return {"ok": False, "error": "request failed: %s" % e, "model": model}
    if r.status_code != 200:
        return {"ok": False, "model": model,
                "error": "HTTP %s: %s" % (r.status_code, r.text[:200])}
    try:
        content = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return {"ok": False, "model": model, "error": "unexpected response: %s" % e}
    return {"ok": True, "model": model, "content": content}


def extract_celltype_facts(text: str, model: Optional[str] = None,
                           timeout: int = 60) -> Dict[str, Any]:
    """SPIRES-style: LLM fills a fixed cell-type schema from `text`. Returns
    {ok, model, facts:{cell_type, transcriptomic_markers, surface_markers, location,
    functions}, raw}. The caller grounds the strings with CellScribe's OLS grounder."""
    res = chat_complete("Text:\n" + (text or ""), model=model,
                        system=_EXTRACT_SYSTEM, timeout=timeout)
    if not res.get("ok"):
        return res
    facts = _first_json(res["content"])
    if facts is None:
        return {"ok": False, "model": res["model"],
                "error": "model did not return parseable JSON", "raw": res["content"][:400]}
    return {"ok": True, "model": res["model"], "facts": facts, "raw": res["content"]}
