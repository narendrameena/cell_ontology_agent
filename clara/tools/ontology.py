"""Ontology grounding via the EBI Ontology Lookup Service (OLS4).

Grounds free text to real CURIEs in the Cell Ontology (CL), Uberon (anatomy),
GO (processes) and PR (proteins).  This is the anti-hallucination backbone:
nothing enters a draft unless it resolves to a real ontology term.
"""
from __future__ import annotations

from typing import List, Optional

from ..cache import http_get_json
from ..models import TermMatch
from ..registry import Tool, ToolSpec

OLS_SEARCH = "https://www.ebi.ac.uk/ols4/api/search"


def _label_score(query: str, label: str, is_exact_syn: bool = False) -> float:
    q, l = query.lower().strip(), (label or "").lower().strip()
    if not l:
        return 0.0
    if q == l:
        return 1.0
    if is_exact_syn:
        return 0.9
    qset, lset = set(q.split()), set(l.split())
    if not qset:
        return 0.0
    jacc = len(qset & lset) / len(qset | lset)
    contain = 0.15 if (q in l or l in q) else 0.0
    return min(0.85, 0.55 * jacc + contain + 0.3 * (len(qset & lset) / len(qset)))


class OLSSearchTool(Tool):
    spec = ToolSpec(
        name="ols_search",
        description="Ground a free-text cell type, tissue, process or protein to real "
                    "ontology terms (CURIEs) via EBI OLS4. Ontologies: cl, uberon, go, pr.",
        tags=["ontology", "grounding", "cell type", "anatomy", "CL", "Uberon", "GO",
              "curie", "term", "lookup", "search"],
        input_schema={"query": "str", "ontology": "str (cl|uberon|go|pr)", "rows": "int"},
        returns="List[TermMatch] ranked by label match",
    )

    def __call__(self, query: str, ontology: str = "cl", rows: int = 5,
                 offline: Optional[bool] = None) -> List[TermMatch]:
        data = http_get_json(
            OLS_SEARCH,
            {
                "q": query,
                "ontology": ontology,
                "rows": rows,
                "fieldList": "iri,label,short_form,obo_id,description,ontology_name,synonym",
            },
            offline=offline,
        )
        out: List[TermMatch] = []
        if not data:
            return out
        for doc in data.get("response", {}).get("docs", []):
            label = doc.get("label", "")
            syns = doc.get("synonym", []) or []
            is_syn = any(query.lower().strip() == s.lower().strip() for s in syns)
            desc = doc.get("description") or []
            out.append(TermMatch(
                query=query,
                curie=doc.get("obo_id") or (doc.get("short_form", "").replace("_", ":")),
                iri=doc.get("iri", ""),
                label=label,
                ontology=doc.get("ontology_name", ontology),
                definition=(desc[0] if isinstance(desc, list) and desc else ""),
                synonyms=syns[:6],
                score=round(_label_score(query, label, is_syn), 3),
            ))
        out.sort(key=lambda t: t.score, reverse=True)
        return out


def best_match(registry_tool: OLSSearchTool, query: str, ontology: str = "cl",
               min_score: float = 0.0, offline: Optional[bool] = None) -> Optional[TermMatch]:
    hits = registry_tool(query, ontology=ontology, rows=5, offline=offline)
    if hits and hits[0].score >= min_score:
        return hits[0]
    return None
