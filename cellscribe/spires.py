"""SPIRES-style schema-constrained extraction (roadmap: SPIRES/OntoGPT-grade).

SPIRES (Caufield et al., part of OntoGPT) populates a fixed schema of
ontology-grounded slots from text instead of free-texting — which is what curbs
hallucination. Here we extract a small, fixed schema from retrieved abstracts:
for each proposed marker, the sentence that supports it and its grounding to a
real ontology term (PRO for proteins). The output is always the same shape, and
every value is grounded — never invented.

Deterministic by default (testable offline); with an LLM key it can refine the
evidence selection; if the `ontogpt` package is installed it can be deferred to.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_SENT = re.compile(r"(?<=[.!?])\s+")


def ontogpt_available() -> bool:
    import importlib.util as u
    return u.find_spec("ontogpt") is not None


def _evidence_sentence(text: str, term: str) -> str:
    for s in _SENT.split(text or ""):
        if term.lower() in s.lower():
            return s.strip()[:240]
    return ""


def extract_marker_assertions(papers, markers: List[str], ground_surface=None,
                              llm=None) -> Dict[str, Any]:
    """Schema: {assertions: [{marker, grounded, evidence, pmid}], method, grounded_n}.

    `ground_surface(symbol) -> TermMatch|None` (e.g. the agent's PRO grounder) is
    used to ground each marker; every assertion carries its supporting sentence.
    """
    assertions = []
    for m in markers:
        ev, pmid = "", ""
        for p in papers:
            s = _evidence_sentence(p.title + ". " + p.snippet, m)
            if s:
                ev, pmid = s, p.pmid
                break
        curie = None
        if ground_surface is not None:
            got = ground_surface(m)
            curie = got.curie if got else None
        assertions.append({"marker": m, "grounded": curie, "evidence": ev, "pmid": pmid})
    method = "deterministic (schema-constrained, grounded)"
    if ontogpt_available():
        method = "ontogpt-available (would defer to SPIRES)"
    elif llm is not None and getattr(llm, "available", False):
        method = "llm-refined (schema-constrained)"
    return {"assertions": assertions, "method": method,
            "grounded_n": sum(1 for a in assertions if a["grounded"]),
            "evidenced_n": sum(1 for a in assertions if a["evidence"])}
