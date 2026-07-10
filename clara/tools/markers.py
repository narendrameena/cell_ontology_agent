"""Marker-panel analysis — an NS-Forest-style minimal marker finder.

NS-Forest (Aevermann et al.) finds the smallest set of genes that best
discriminates a cell-type cluster.  This is a faithful, dependency-light
re-implementation of the *idea*: score each candidate gene by how binary and
specific its expression is for the target cluster, then greedily assemble a
minimal panel and report an F-beta separation score.  Pure numpy/pandas so it
runs anywhere; swap in the real NS-Forest package for production.
"""
from __future__ import annotations

from typing import List, Optional

from ..models import MarkerPanel
from ..registry import Tool, ToolSpec

try:
    import numpy as np
    import pandas as pd
except Exception:  # pragma: no cover
    np = None
    pd = None


def _binary_scores(expr, labels, target, gene, thresh):
    on = expr[gene] > thresh
    in_t = labels == target
    tp = int((on & in_t).sum())
    fp = int((on & ~in_t).sum())
    fn = int((~on & in_t).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    beta2 = 0.5 ** 2  # favour precision (specificity) — NS-Forest uses Fbeta<1
    denom = (beta2 * prec + rec)
    fbeta = (1 + beta2) * prec * rec / denom if denom else 0.0
    return {"precision": round(prec, 3), "recall": round(rec, 3),
            "fbeta": round(fbeta, 3), "on_fraction_in_cluster": round(rec, 3)}


class MarkerPanelTool(Tool):
    spec = ToolSpec(
        name="marker_panel",
        description="Given an expression matrix (cells x genes + cluster labels), find a "
                    "minimal, specific marker panel for the target cluster and score its "
                    "separation (NS-Forest-style). Falls back to a prior-based score if no "
                    "matrix is supplied.",
        tags=["markers", "bioinformatic", "ns-forest", "expression", "specificity",
              "single-cell", "test", "confidence"],
        input_schema={"expr_csv": "str", "cluster_col": "str", "target_cluster": "str",
                      "candidate_genes": "List[str]", "max_markers": "int"},
        returns="MarkerPanel(markers, score, method, per_gene)",
    )

    def from_matrix(self, expr_csv: str, cluster_col: str, target_cluster: str,
                    candidate_genes: Optional[List[str]] = None,
                    max_markers: int = 3, thresh: float = 0.0) -> MarkerPanel:
        if pd is None:
            raise RuntimeError("pandas/numpy required for matrix mode")
        df = pd.read_csv(expr_csv)
        labels = df[cluster_col].astype(str)
        target = str(target_cluster)
        genes = candidate_genes or [c for c in df.columns if c != cluster_col]
        genes = [g for g in genes if g in df.columns]

        per_gene = {g: _binary_scores(df, labels, target, g, thresh) for g in genes}
        ranked = sorted(genes, key=lambda g: per_gene[g]["fbeta"], reverse=True)

        # greedy: add genes while the AND-combined panel keeps improving precision
        panel: List[str] = []
        best = 0.0
        in_t = labels == target
        for g in ranked:
            trial = panel + [g]
            on = (df[trial] > thresh).all(axis=1)
            tp = int((on & in_t).sum()); fp = int((on & ~in_t).sum())
            fn = int((~on & in_t).sum())
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            beta2 = 0.25
            denom = (beta2 * prec + rec)
            fbeta = (1 + beta2) * prec * rec / denom if denom else 0.0
            if fbeta >= best and len(trial) <= max_markers:
                panel, best = trial, fbeta
            if best >= 0.98 or len(panel) >= max_markers:
                break
        if not panel and ranked:
            panel = ranked[:1]
            best = per_gene[panel[0]]["fbeta"]
        return MarkerPanel(
            markers=panel, score=round(float(best), 3), method="NS-Forest-style (F-beta, beta=0.5)",
            per_gene={g: per_gene[g] for g in panel},
            note="Minimal panel maximising in-cluster specificity on the supplied matrix.",
        )

    def from_prior(self, genes: List[str], literature_hits: int = 0,
                   grounded: int = 0) -> MarkerPanel:
        """No expression matrix: score confidence from evidence, not data."""
        genes = [g for g in genes if g]
        if not genes:
            return MarkerPanel(markers=[], score=0.0, method="prior (no markers)",
                               note="No markers supplied and no matrix — cannot test.")
        lit = min(1.0, literature_hits / 5.0)
        grd = (grounded / len(genes)) if genes else 0.0
        score = round(0.35 + 0.35 * lit + 0.30 * grd, 3)
        return MarkerPanel(
            markers=genes[:4], score=min(score, 0.9),
            method="prior (evidence-weighted, no matrix)",
            note="No expression matrix supplied; confidence reflects literature + grounding, "
                 "not a data-driven separation. Supply --expr for a real NS-Forest-style test.",
        )

    def __call__(self, **kwargs):
        if kwargs.get("expr_csv"):
            return self.from_matrix(
                kwargs["expr_csv"], kwargs.get("cluster_col", "cluster"),
                kwargs["target_cluster"], kwargs.get("candidate_genes"),
                kwargs.get("max_markers", 3))
        return self.from_prior(kwargs.get("candidate_genes", []),
                               kwargs.get("literature_hits", 0),
                               kwargs.get("grounded", 0))
