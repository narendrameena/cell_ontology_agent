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


def nsforest_available() -> bool:
    """True if the real NS-Forest package + Scanpy/AnnData are importable."""
    import importlib.util as u
    return all(u.find_spec(m) is not None for m in ("nsforest", "anndata", "scanpy"))


def real_nsforest_panel(expr_csv, cluster_col, target_cluster,
                        species="", context="") -> "Optional[MarkerPanel]":
    """Compute the marker panel with the REAL NS-Forest package (Aevermann et al.)
    on Scanpy/AnnData. Returns a MarkerPanel, or None if unavailable/failed so the
    caller falls back to the built-in re-implementation.

    NS-Forest's API differs across versions; this tries the current entry points
    defensively. Install with `pip install nsforest scanpy anndata`.
    """
    try:
        import anndata
        import nsforest as ns
        df = pd.read_csv(expr_csv)
        genes = [c for c in df.columns if c != cluster_col]
        obs = pd.DataFrame({cluster_col: df[cluster_col].astype(str).values})
        adata = anndata.AnnData(X=df[genes].values.astype(float),
                                obs=obs, var=pd.DataFrame(index=genes))
        # NS-Forest preprocessing + run (module paths vary by version)
        try:
            from nsforest import pp, nsforesting
            adata = pp.prep_medians(adata, cluster_col)
            adata = pp.prep_binary_scores(adata, cluster_col)
            res = nsforesting.NSForest(adata, cluster_header=cluster_col)
        except Exception:
            res = ns.NSForest(adata, cluster_header=cluster_col)  # older API
        col_markers = "NSForest_markers" if "NSForest_markers" in res.columns else "markers"
        row = res[res[res.columns[0]].astype(str) == str(target_cluster)]
        if not len(row):
            return None
        markers = list(row[col_markers].iloc[0])
        fbeta = float(row["f_score"].iloc[0]) if "f_score" in row.columns else 0.0
        return MarkerPanel(markers=markers, score=round(fbeta, 3),
                           method="NS-Forest (real package, Scanpy/AnnData)",
                           species=species, context=context,
                           note="Computed by the nsforest package on the supplied matrix.")
    except Exception:
        return None


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
                    max_markers: int = 3, thresh: float = 0.0,
                    species: str = "", context: str = "",
                    prefer_nsforest: bool = False) -> MarkerPanel:
        if pd is None:
            raise RuntimeError("pandas/numpy required for matrix mode")
        if prefer_nsforest and nsforest_available():   # real NS-Forest package if present
            p = real_nsforest_panel(expr_csv, cluster_col, target_cluster, species, context)
            if p is not None and p.markers:
                return p
        df = pd.read_csv(expr_csv)
        if cluster_col not in df.columns:
            raise ValueError("cluster column %r not in matrix (columns: %s)"
                             % (cluster_col, ", ".join(map(str, list(df.columns)[:8]))))
        labels = df[cluster_col].astype(str)
        target = str(target_cluster)
        cand = candidate_genes or [c for c in df.columns if c != cluster_col]
        seen, genes = set(), []                       # dedupe, keep order, real columns only
        for g in cand:
            if g in df.columns and g not in seen:
                seen.add(g); genes.append(g)
        in_t = labels == target
        n_pos, n_neg = int(in_t.sum()), int((~in_t).sum())
        M = "NS-Forest-style (F-beta, beta=0.5)"
        if not genes:
            return MarkerPanel(markers=[], score=0.0, method=M, species=species, context=context,
                               note="None of the candidate genes were found as columns in the matrix.")
        if n_pos == 0:
            return MarkerPanel(markers=[], score=0.0, method=M, species=species, context=context,
                               note="Target cluster %r has no cells in the matrix — cannot test markers." % target)

        per_gene = {g: _binary_scores(df, labels, target, g, thresh) for g in genes}
        ranked = sorted(genes, key=lambda g: per_gene[g]["fbeta"], reverse=True)

        # greedy: add a gene only if it STRICTLY improves the panel F-beta (true minimality)
        panel: List[str] = []
        best = 0.0
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
            if fbeta > best and len(trial) <= max_markers:
                panel, best = trial, fbeta
            if best >= 0.98 or len(panel) >= max_markers:
                break
        if not panel:
            panel = ranked[:1]
            best = per_gene[panel[0]]["fbeta"]

        on = (df[panel] > thresh).all(axis=1)
        tp = int((on & in_t).sum()); fp = int((on & ~in_t).sum()); fn = int((~on & in_t).sum())
        fprec = round(tp / (tp + fp), 3) if (tp + fp) else 0.0
        frec = round(tp / (tp + fn), 3) if (tp + fn) else 0.0
        note = ("Minimal panel maximising in-cluster specificity on the supplied matrix. "
                "Markers are context-dependent: this separation holds within the stated context.")
        if n_neg == 0:
            note = ("Only one cluster present — specificity cannot be assessed (precision is "
                    "trivially 1.0). ") + note
        return MarkerPanel(
            markers=panel, score=round(float(best), 3), method=M,
            precision=fprec, recall=frec, species=species, context=context,
            per_gene={g: per_gene[g] for g in panel}, note=note)

    def from_prior(self, genes: List[str], literature_hits: int = 0,
                   grounded: int = 0, species: str = "", context: str = "") -> MarkerPanel:
        """No expression matrix: score confidence from evidence, not data."""
        genes = [g for g in genes if g]
        if not genes:
            return MarkerPanel(markers=[], score=0.0, method="prior (no markers)",
                               note="No markers supplied and no matrix — cannot test.")
        lit = min(1.0, literature_hits / 5.0)
        grd = (grounded / len(genes)) if genes else 0.0
        score = round(0.35 + 0.35 * lit + 0.30 * grd, 3)
        return MarkerPanel(
            markers=genes[:4], score=min(score, 0.9), species=species, context=context,
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
