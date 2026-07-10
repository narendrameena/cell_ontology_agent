"""Optional LLM layer — provider-agnostic, zero SDK dependency (uses requests).

CellScribe is *useful without an LLM*: the deterministic pipeline grounds, tests and
drafts on its own.  When a key is present the LLM adds two things that need
judgement — planning the tool order and polishing the prose definition — but it
never invents ontology terms; those always come from grounded tool output.

    export ANTHROPIC_API_KEY=...     # or OPENAI_API_KEY=...
    export CELLSCRIBE_MODEL=claude-sonnet-5   # optional override
"""
from __future__ import annotations

import json
import os
from typing import List, Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


class LLMClient:
    def __init__(self) -> None:
        self.provider = None
        self.model = os.environ.get("CELLSCRIBE_MODEL", "")
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
            self.model = self.model or "claude-sonnet-5"
        elif os.environ.get("OPENAI_API_KEY"):
            self.provider = "openai"
            self.model = self.model or "gpt-4o"

    @property
    def available(self) -> bool:
        return self.provider is not None and requests is not None

    # ------------------------------------------------------------------ low level
    def complete(self, system: str, user: str, max_tokens: int = 700) -> Optional[str]:
        if not self.available:
            return None
        try:
            if self.provider == "anthropic":
                r = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                             "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    data=json.dumps({"model": self.model, "max_tokens": max_tokens,
                                     "system": system,
                                     "messages": [{"role": "user", "content": user}]}),
                    timeout=40)
                r.raise_for_status()
                return r.json()["content"][0]["text"]
            else:
                r = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                             "content-type": "application/json"},
                    data=json.dumps({"model": self.model, "max_tokens": max_tokens,
                                     "messages": [{"role": "system", "content": system},
                                                  {"role": "user", "content": user}]}),
                    timeout=40)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            return None

    # ------------------------------------------------------------------ helpers
    def plan_tools(self, goal: str, tool_names: List[str]) -> Optional[List[str]]:
        """Ask the model to order the available tools for this goal.

        Constrained to the real tool names; anything off-menu is dropped, so the
        model cannot hallucinate a capability that does not exist.
        """
        out = self.complete(
            system="You are a planning module for an ontology-curation agent. "
                   "Return ONLY a JSON list of tool names, in execution order, "
                   "chosen from the provided set. No prose.",
            user="Goal: %s\nTools: %s" % (goal, ", ".join(tool_names)),
            max_tokens=200)
        if not out:
            return None
        try:
            start, end = out.find("["), out.rfind("]")
            plan = json.loads(out[start:end + 1])
            return [t for t in plan if t in tool_names] or None
        except Exception:
            return None

    def polish_definition(self, draft_text: str, context: str) -> Optional[str]:
        """Tighten the textual definition to genus-differentia house style.

        Grounded terms are fixed; the model may only rephrase, and we keep the
        result only if it stays a single sentence.
        """
        out = self.complete(
            system="You edit Cell Ontology textual definitions into concise "
                   "genus-differentia form (Aristotelian: 'A <parent> that <differentia>.'). "
                   "Do not add facts beyond the context. One sentence.",
            user="Context (grounded facts):\n%s\n\nDraft:\n%s\n\nReturn only the edited sentence."
                 % (context, draft_text),
            max_tokens=160)
        if out:
            out = out.strip().strip('"')
            if out.count(".") <= 2 and len(out) < 400:
                return out
        return None

    def draft_cl_definition(self, genus: str, facts: str, refs: str) -> Optional[str]:
        """Generate a CL-house-style definition from grounded facts.

        Uses the Cell Ontology's own standardized prompt (Tan et al. 2026, Methods):
        genus-differentia, 80-120 words, single paragraph, inline references, species-
        tagged markers, never naming the cell type. The grounded facts + retrieved
        references are fixed inputs so the model organises evidence, it does not invent it.
        """
        out = self.complete(
            system=("You are an expert cell biologist writing Cell Ontology definitions. "
                    "Each definition must: (1) NOT name the cell type; start with its general "
                    "classification, then the distinguishing characteristics; (2) describe "
                    "structural, functional and anatomical features; (3) note species presence/"
                    "absence when relevant; (4) mention key markers only if crucial, tagging the "
                    "species (e.g. 'marker X in mice'); (6) include inline references to key "
                    "statements; (7) be 80-120 words, one paragraph; (8) clear scientific language. "
                    "Use ONLY the grounded facts and references provided; add nothing unsupported."),
            user=("General classification (genus): %s\nGrounded facts: %s\n"
                  "Available references: %s\n\nWrite the definition paragraph only." )
                 % (genus, facts, refs or "(none retrieved)"),
            max_tokens=320)
        if out:
            out = out.strip().strip('"')
            if 40 <= len(out) <= 1200:
                return out
        return None
