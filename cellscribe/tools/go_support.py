"""GO-based marker support via QuickGO — the paper's GO x marker intersection.

The Cell Ontology paper (Fig 1, Table 1, Methods "CL-Knowledge graph and GO-Marker
cross-analysis") derives transcriptomic signatures of a cell type's *defining*
functions/components by intersecting the genes annotated to those GO terms with
markers from transcriptomic data. A marker that is BOTH differentially expressed
AND annotated to the cell type's GO function is higher-confidence.

We query QuickGO for genes annotated to a GO term, restricted to the same
manually-reviewed evidence used in the paper: ECO:0000269 (experimental) and
ECO:0000318 (biological aspect of ancestor).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..cache import http_get_json
from ..registry import Tool, ToolSpec

QUICKGO = "https://www.ebi.ac.uk/QuickGO/services/annotation/search"
# manually-asserted evidence codes used by the CL paper (Methods)
EVIDENCE = "ECO:0000269,ECO:0000318"
ORGANISM_TAXON = {"homo sapiens": "9606", "mus musculus": "10090",
                  "human": "9606", "mouse": "10090"}


def taxon_for(organism: str) -> List[str]:
    """Species to query. We union the requested organism with mouse+human, since
    canonical GO annotation is densest there and marker symbols are homologous."""
    t = ORGANISM_TAXON.get((organism or "").lower().strip())
    taxa = ["9606", "10090"]
    if t and t not in taxa:
        taxa.append(t)
    return taxa


class QuickGOTool(Tool):
    spec = ToolSpec(
        name="go_marker_support",
        description="For a GO term, return the genes annotated to it (QuickGO, manual "
                    "evidence ECO:0000269/0000318), to intersect with a cell type's markers "
                    "and flag which markers are supported by the cell type's defining GO function.",
        tags=["go", "quickgo", "marker", "evidence", "gene", "function", "verification",
              "signature"],
        input_schema={"go_id": "str (GO:xxxxxxx)", "taxa": "List[str] NCBI taxon ids"},
        returns="set of gene symbols (upper-cased)",
    )

    def genes_for_go(self, go_id: str, taxa: List[str],
                     offline: Optional[bool] = None) -> set:
        symbols = set()
        for taxon in taxa:
            data = http_get_json(
                QUICKGO,
                {"goId": go_id, "taxonId": taxon, "evidenceCode": EVIDENCE,
                 "evidenceCodeUsage": "descendants", "limit": 200, "geneProductType": "protein"},
                offline=offline,
                headers={"Accept": "application/json",
                         "User-Agent": "CellScribe/0.1 (cell-ontology curation)"},
            )
            if not data:
                continue
            for r in data.get("results", []):
                sym = r.get("symbol")
                if sym:
                    symbols.add(sym.upper())
        return symbols

    def support(self, markers: List[str], go_terms: List, organism: str = "Homo sapiens",
                offline: Optional[bool] = None) -> Dict[str, List[str]]:
        """marker -> list of GO ids (of the cell type's functions) that annotate it."""
        taxa = taxon_for(organism)
        out: Dict[str, List[str]] = {m: [] for m in markers}
        for go in go_terms:
            go_id = getattr(go, "curie", None) or (go if isinstance(go, str) else None)
            if not go_id or not go_id.startswith("GO:"):
                continue
            genes = self.genes_for_go(go_id, taxa, offline=offline)
            for m in markers:
                if m.upper() in genes:
                    out[m].append(go_id)
        return {m: v for m, v in out.items() if v}

    def __call__(self, go_id: str, taxa: List[str], offline: Optional[bool] = None):
        return self.genes_for_go(go_id, taxa, offline=offline)
