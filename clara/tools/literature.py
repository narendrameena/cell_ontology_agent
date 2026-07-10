"""Literature evidence via Europe PMC.

Retrieval-augmented grounding: pull real papers for the (cell type + markers)
and extract the sentences that actually mention them, so a draft definition can
cite evidence rather than assert it.
"""
from __future__ import annotations

import re
from typing import List, Optional

from ..cache import http_get_json
from ..models import Paper
from ..registry import Tool, ToolSpec

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_SENT = re.compile(r"(?<=[.!?])\s+")


_STOP = {"the", "and", "a", "an", "of", "positive", "negative", "expressing", "cell", "cells"}


def build_query(name: str, markers: Optional[List[str]] = None,
                organism: str = "") -> str:
    parts = ['"%s"' % name.strip()] if name else []
    markers = [m for m in (markers or []) if m]
    if markers:
        parts.append("(" + " OR ".join(markers[:6]) + ")")
    if organism:
        parts.append('"%s"' % organism)
    return " AND ".join(parts) if parts else name


def build_query_cascade(name: str, markers: Optional[List[str]] = None,
                        organism: str = "") -> List[str]:
    """Ordered queries from most precise to most permissive.

    A full quoted cell-type name rarely appears verbatim in abstracts, so we fall
    back to unquoted tokens + markers, then markers alone, so novel types still
    surface evidence instead of returning zero hits.
    """
    m = [x for x in (markers or []) if x]
    mm = "(" + " OR ".join(m[:6]) + ")" if m else ""
    toks = [t for t in re.findall(r"[A-Za-z0-9\-]+", name or "")
            if len(t) > 2 and t.lower() not in _STOP]
    qs: List[str] = []
    if name and mm and organism:
        qs.append('"%s" AND %s' % (name, mm))
    if name and mm:
        qs.append('"%s" AND %s' % (name, mm))
        qs.append("%s AND %s" % (" ".join(toks), mm))       # unquoted tokens
    if toks and mm:
        qs.append("%s AND %s" % (" ".join(toks[-3:]), mm))  # head tokens
    if mm:
        qs.append(mm)                                        # markers alone
    if name:
        qs.append('"%s"' % name)
    seen, out = set(), []
    for q in qs:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _extract_snippet(abstract: str, terms: List[str], limit: int = 260) -> str:
    if not abstract:
        return ""
    terms_l = [t.lower() for t in terms if t]
    for sent in _SENT.split(abstract):
        s = sent.lower()
        if any(t in s for t in terms_l):
            return sent.strip()[:limit]
    return abstract.strip()[:limit]


class EuropePMCTool(Tool):
    spec = ToolSpec(
        name="literature_search",
        description="Search Europe PMC for papers supporting a cell type and its marker "
                    "genes, and extract the evidence sentence from each abstract.",
        tags=["literature", "evidence", "pubmed", "europepmc", "rag", "citation",
              "markers", "deep search", "verification"],
        input_schema={"name": "str", "markers": "List[str]", "rows": "int"},
        returns="List[Paper] with extracted evidence snippets",
    )

    def __call__(self, name: str, markers: Optional[List[str]] = None,
                 organism: str = "", rows: int = 5,
                 offline: Optional[bool] = None) -> List[Paper]:
        data = None
        for query in build_query_cascade(name, markers, organism):
            data = http_get_json(
                EPMC,
                {"query": query, "format": "json", "pageSize": rows, "resultType": "core"},
                offline=offline,
            )
            if data and data.get("resultList", {}).get("result"):
                break  # first query that yields evidence wins
        out: List[Paper] = []
        if not data:
            return out
        terms = [name] + list(markers or [])
        for r in data.get("resultList", {}).get("result", []):
            pmid = r.get("pmid") or r.get("id", "")
            jinfo = r.get("journalInfo", {}) or {}
            journal = (jinfo.get("journal", {}) or {}).get("title", "") or r.get("journalTitle", "")
            doi = r.get("doi", "")
            out.append(Paper(
                pmid=str(pmid),
                title=r.get("title", "").rstrip("."),
                authors=r.get("authorString", ""),
                journal=journal,
                year=str(r.get("pubYear", "")),
                doi=doi,
                url=("https://doi.org/" + doi) if doi else
                    ("https://europepmc.org/article/MED/" + str(pmid) if pmid else ""),
                snippet=_extract_snippet(r.get("abstractText", ""), terms),
            ))
        return out
