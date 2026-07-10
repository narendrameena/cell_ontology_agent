#!/usr/bin/env python3
"""Edge-case / robustness audit — probes where CellScribe breaks.

Run: python tests/test_edge_cases.py   (offline, deterministic)
These deliberately hit degenerate inputs (empty name, absent cluster, bad path,
ungrounded terms, unicode, duplicates) to verify the agent degrades gracefully.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["CELLSCRIBE_OFFLINE"] = "1"
os.environ["CELLSCRIBE_CACHE"] = os.path.join(ROOT, "demo_data", "fixtures")
CSV = os.path.join(ROOT, "demo_data", "striatum_demo_expr.csv")

from cellscribe.agent import CuratorAgent, _derive_parent
from cellscribe.dossier import CurationDossier
from cellscribe.models import CurationRequest, MarkerPanel, TermMatch
from cellscribe.tools.literature import build_query_cascade
from cellscribe.tools.markers import MarkerPanelTool
from cellscribe.tools.validation import critique


def _agent():
    return CuratorAgent(offline=True, use_llm=False, verbose=False)


# ---- degenerate agent inputs ----
def test_empty_name_no_crash():
    d = _agent().curate(CurationRequest(name=""))
    assert d.critique is not None


def test_unicode_name_no_crash():
    d = _agent().curate(CurationRequest(name="αβ T cell λ", markers=[]))
    assert d.critique is not None


def test_bad_expr_path_falls_back():
    d = _agent().curate(CurationRequest(
        name="CD4-positive, alpha-beta T cell", markers=["CD4"],
        expr_csv="/no/such/file.csv", target_cluster="x"))
    assert d.critique is not None  # must NOT crash on unreadable matrix


# ---- marker panel degenerate cases ----
def test_absent_target_cluster_no_crash():
    mp = MarkerPanelTool().from_matrix(CSV, "cluster", "NONEXISTENT",
                                       candidate_genes=["GAD1", "PVALB"])
    assert isinstance(mp.markers, list)


def test_all_candidate_genes_absent():
    mp = MarkerPanelTool().from_matrix(CSV, "cluster", "striatal_PV_interneuron",
                                       candidate_genes=["NOTAGENE1", "NOTAGENE2"])
    assert mp.markers == []


def test_duplicate_markers():
    mp = MarkerPanelTool().from_matrix(CSV, "cluster", "striatal_PV_interneuron",
                                       candidate_genes=["GAD1", "GAD1", "PVALB"])
    assert "GAD1" in mp.markers


def test_from_prior_empty():
    mp = MarkerPanelTool().from_prior([])
    assert mp.markers == [] and mp.score == 0.0


# ---- grounding / query degenerate cases ----
def test_ground_surface_empty():
    assert _agent()._ground_surface("") is None


def test_query_cascade_empty_inputs():
    assert build_query_cascade("", [], "") == []


def test_derive_parent_empty():
    assert _derive_parent("") == "cell"


# ---- critic / dossier degenerate cases ----
def test_critique_all_none():
    c = critique("x", None, None, None, None, [])
    assert 0.0 <= c.confidence <= 1.0 and c.disposition


def test_dossier_save_minimal():
    d = CurationDossier(request=CurationRequest(name="x/y:z"))
    out = d.save(tempfile.mkdtemp())
    assert os.path.exists(out["markdown"]) and os.path.exists(out["json"])


# ---- correctness regressions (audit findings) ----
def test_surface_markers_not_asserted_as_expresses():
    # bug: surface markers leaked into the transcriptomic `expresses` axiom
    d = _agent().curate(CurationRequest(
        name="CD4-positive, alpha-beta T cell", surface_markers=["CD4", "IL7R"],
        functions=["T cell receptor signaling pathway"], markers=[]))
    m = d.definition.manchester_owl
    assert "has plasma membrane part" in m
    assert "expresses" not in m


def test_organism_scopes_a_literature_query():
    qs = build_query_cascade("mouse microglia", ["P2RY12", "TMEM119"], "Mus musculus")
    assert any("Mus musculus" in q for q in qs)


def test_absent_target_returns_empty_panel():
    mp = MarkerPanelTool().from_matrix(CSV, "cluster", "NONEXISTENT",
                                       candidate_genes=["GAD1", "PVALB"])
    assert mp.markers == [] and mp.score == 0.0 and "no cells" in mp.note


def test_all_genes_absent_has_clear_note():
    mp = MarkerPanelTool().from_matrix(CSV, "cluster", "striatal_PV_interneuron",
                                       candidate_genes=["FOO", "BAR"])
    assert mp.markers == [] and "found as columns" in mp.note


def test_marker_dedup():
    mp = MarkerPanelTool().from_matrix(CSV, "cluster", "striatal_PV_interneuron",
                                       candidate_genes=["PVALB", "PVALB", "GAD1"])
    assert len(mp.markers) == len(set(mp.markers))


def test_missing_cluster_column_raises_clear_error():
    try:
        MarkerPanelTool().from_matrix(CSV, "NOTACOL", "striatal_PV_interneuron")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_none_description_no_crash():
    d = _agent().curate(CurationRequest(
        name="CD4-positive, alpha-beta T cell", description=None, markers=["CD4"]))
    assert d.critique is not None


def test_sssom_no_existing_is_not_a_mapping():
    s = CurationDossier(request=CurationRequest(name="novel type", organism="Mus musculus")).to_sssom()
    assert "exactMatch" not in s and "crossSpecies" not in s


def _main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    p = f = 0
    for n, fn in tests:
        try:
            fn(); print("  PASS  %s" % n); p += 1
        except Exception as exc:  # noqa: BLE001
            import traceback
            print("  FAIL  %s -> %r" % (n, exc)); f += 1
            traceback.print_exc()
    print("\n%d passed, %d failed" % (p, f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(_main())
