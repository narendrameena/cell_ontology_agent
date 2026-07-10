#!/usr/bin/env python3
"""Tests for the roadmap integrations: ELK reasoning, ROBOT round-trip, SPIRES-style
extraction, ecosystem adapters, and the real-nsforest fallback. Offline; the
ROBOT/ELK tests run for real when Java + robot.jar are present, else self-skip.
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

from cellscribe import CuratorAgent, CurationRequest, integrations, reasoning, spires
from cellscribe.tools import markers, robot_tools


def _dossier():
    return CuratorAgent(offline=True, use_llm=False, verbose=False).curate(CurationRequest(
        name="striatal parvalbumin-positive GABAergic interneuron",
        markers=["GAD1", "GAD2", "PVALB"], functions=["GABA biosynthetic process"],
        location_hint="striatum", expr_csv=CSV, cluster_col="cluster",
        target_cluster="striatal_PV_interneuron", organism="Homo sapiens"))


# ---- ecosystem adapters (detection + fallback) ----
def test_integrations_status():
    s = integrations.status()
    assert {"ontogpt_spires", "dragon_ai", "aurelian", "robot_elk", "nsforest"} <= set(s)
    assert all(isinstance(v, bool) for v in s.values())


def test_nsforest_fallback_still_works():
    mp = markers.MarkerPanelTool().from_matrix(
        CSV, "cluster", "striatal_PV_interneuron",
        candidate_genes=["GAD1", "GAD2", "PVALB"], prefer_nsforest=True)
    assert "PVALB" in mp.markers   # nsforest absent -> built-in fallback still produces a panel


# ---- SPIRES-style extraction ----
def test_spires_schema_shape():
    d = _dossier()
    out = spires.extract_marker_assertions(d.papers, ["GAD1", "PVALB"])
    assert {"assertions", "method", "grounded_n", "evidenced_n"} <= set(out)
    assert len(out["assertions"]) == 2 and all("marker" in a for a in out["assertions"])


# ---- reasoning: structural (always) + OWL builder ----
def test_structural_check():
    assert reasoning.structural_check(_dossier())["ok"] is True


def test_owl_from_dossier_wellformed():
    owl = reasoning.owl_from_dossier(_dossier())
    assert "EquivalentClasses" in owl and "CL_0000099" in owl and "UBERON_0002435" in owl


# ---- ELK / ROBOT (real if available) ----
def test_elk_classify():
    if not robot_tools.robot_available():
        print("    (skip: ROBOT/Java unavailable)"); return
    r = reasoning.classify(_dossier())["reasoner"]
    assert r["available"] and r["coherent"] is True


def test_elk_taxon_incoherence_detected():
    if not robot_tools.robot_available():
        print("    (skip: ROBOT/Java unavailable)"); return
    t = reasoning.taxon_incoherence_demo()
    assert t["available"] and t["incoherency_detected"] is True


def test_robot_template_roundtrip():
    if not robot_tools.robot_available():
        print("    (skip: ROBOT/Java unavailable)"); return
    ok, _msg = robot_tools.materialize_dossier(
        _dossier(), os.path.join(tempfile.mkdtemp(), "term.owl"), reason_after=True)
    assert ok is True


def _main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    p = f = 0
    for n, fn in tests:
        try:
            fn(); print("  PASS  %s" % n); p += 1
        except Exception as exc:  # noqa: BLE001
            import traceback
            print("  FAIL  %s -> %r" % (n, exc)); traceback.print_exc(); f += 1
    print("\n%d passed, %d failed" % (p, f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(_main())
