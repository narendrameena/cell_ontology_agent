"""Optional LLM layer — provider-agnostic, zero SDK dependency (uses requests).

CLARA is *useful without an LLM*: the deterministic pipeline grounds, tests and
drafts on its own.  When a key is present the LLM adds two things that need
judgement — planning the tool order and polishing the prose definition — but it
never invents ontology terms; those always come from grounded tool output.

    export ANTHROPIC_API_KEY=...     # or OPENAI_API_KEY=...
    export CLARA_MODEL=claude-sonnet-5   # optional override
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
        self.model = os.environ.get("CLARA_MODEL", "")
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
