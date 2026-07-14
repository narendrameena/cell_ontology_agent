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


def test_ecosystem_handoff_targets_verified():
    """The LLM hand-offs declare the REAL import paths (checked against ontogpt
    1.1.x / curategpt 0.2.x / aurelian 0.4.x); and when a package IS installed, its
    target must actually import — so this self-verifies on a Python >=3.11 env with
    the packages present, and documents the paths everywhere else."""
    h = integrations.verify_handoffs()
    assert h["dragon_ai"]["target"] == "curategpt.agents.dragon_agent.DragonAgent"
    assert h["ontogpt_spires"]["target"] == "ontogpt.engines.spires_engine.SPIRESEngine"
    assert h["aurelian"]["target"] == "aurelian.agents.literature.literature_agent.literature_agent"
    # Invariant: when a package IS installed, its hand-off target either resolves
    # outright or stops only at the LLM-credentials boundary — NEVER a wrong/renamed
    # import path (ImportError/ModuleNotFoundError/AttributeError). Verified true in a
    # Python 3.11 venv: ontogpt+curategpt resolve; aurelian needs_key.
    for key, e in h.items():
        if e["installed"] and not e["resolved"]:
            assert e["needs_key"] is True, \
                "%s failed for a non-credentials reason (bad path?): %s" % (key, e["error"])


def test_llm_ecosystem_status_and_parse():
    from cellscribe import llm_ecosystem as L
    s = L.status()
    assert {"venv", "ontogpt", "model", "key_var", "key_present"} <= set(s)
    assert L.key_var_for("groq/llama-3.3-70b-versatile") == "GROQ_API_KEY"
    assert L.key_var_for("gpt-4o-mini") == "OPENAI_API_KEY"
    assert L.key_var_for("xai/grok-4.5") == "XAI_API_KEY"        # audit fix: was OPENAI_API_KEY
    assert L.key_var_for("anthropic/claude-3-5-haiku-latest") == "ANTHROPIC_API_KEY"
    # light YAML parse keeps only grounded CURIEs, drops AUTO:/ungrounded
    ents = L._parse_named_entities(
        "named_entities:\n- id: CL:0000617\n  label: GABAergic neuron\n"
        "- id: AUTO:xyz\n  label: junk\n- id: UBERON:0002435\n  label: striatum\nextracted_object:\n")
    ids = [e["id"] for e in ents]
    assert ids == ["CL:0000617", "UBERON:0002435"] and ents[0]["label"] == "GABAergic neuron"


def test_llm_extract_graceful_without_key():
    """With no provider key set, the live path never crashes — it returns a clear,
    actionable ok=False (needs_key or needs_venv)."""
    import os as _os
    from cellscribe import llm_ecosystem as L
    saved = _os.environ.pop("GROQ_API_KEY", None)
    try:
        r = L.ontogpt_cell_type("A GABAergic interneuron of the striatum.",
                                model="groq/llama-3.3-70b-versatile")
        assert r["ok"] is False and (r.get("needs_key") or r.get("needs_venv"))
    finally:
        if saved is not None:
            _os.environ["GROQ_API_KEY"] = saved


def test_llm_direct_path_helpers():
    """The keyless direct path (LLM REST + OLS grounding): pure helpers are correct
    and chat_complete degrades gracefully with no key (never a crash / live call)."""
    from cellscribe import llm_ecosystem as L
    assert L._bare_model("groq/llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"
    assert L._bare_model("gpt-4o-mini") == "gpt-4o-mini"
    assert L._base_url_for("groq/x").endswith("groq.com/openai/v1")
    assert L._base_url_for("xai/grok-4.5") == "https://api.x.ai/v1"
    assert L._first_json('noise {"a": 1, "b": [2, 3]} tail') == {"a": 1, "b": [2, 3]}
    assert L._first_json("no json here") is None
    import os as _os
    saved = _os.environ.pop("GROQ_API_KEY", None)
    try:
        r = L.chat_complete("hi", model="groq/llama-3.1-8b-instant")
        assert r["ok"] is False and r["needs_key"] is True and r["key_var"] == "GROQ_API_KEY"
    finally:
        if saved is not None:
            _os.environ["GROQ_API_KEY"] = saved


def test_nsforest_fallback_still_works():
    # prefer_nsforest=False forces the built-in NS-Forest-style path, so this is
    # deterministic whether or not the real package is installed.
    mp = markers.MarkerPanelTool().from_matrix(
        CSV, "cluster", "striatal_PV_interneuron",
        candidate_genes=["GAD1", "GAD2", "PVALB"], prefer_nsforest=False)
    assert "PVALB" in mp.markers   # built-in fallback still produces a specific panel


def test_real_nsforest_when_installed():
    """Runs the REAL nsforest package on the richer fixture when the extra is
    installed (`pip install 'cellscribe[nsforest]'`); self-skips otherwise so the
    base-env suite stays green. Verified against nsforest 4.1 in an isolated venv."""
    if not markers.nsforest_available():
        print("  [skip] nsforest/scanpy/anndata not installed")
        return
    rich = os.path.join(ROOT, "demo_data", "striatum_nsforest_demo_expr.csv")
    mp = markers.real_nsforest_panel(rich, "cluster", "striatal_PV_interneuron",
                                     species="Homo sapiens", context="striatum")
    assert mp is not None and mp.markers, "real nsforest returned no panel"
    assert "PVALB" in mp.markers
    assert "real package" in mp.method


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


CL_OWL = os.path.join(ROOT, ".tools", "cl-base.owl")


def test_classify_against_real_cl():
    """ELK classification against a real CL import module: a novel term is placed
    under CL and flagged NOT redundant; a candidate that mirrors an existing CL
    term's logical definition is flagged a DUPLICATE. Self-skips unless Java +
    robot.jar + a downloaded cl-base.owl are present (verified vs CL v2026-06-08)."""
    if not (robot_tools.robot_available() and os.path.exists(CL_OWL)):
        print("    (skip: needs Java + robot.jar + .tools/cl-base.owl)"); return
    # (a) novel term -> coherent, placed under a CL superclass, no duplicate
    r = reasoning.classify_against_cl(_dossier(), CL_OWL)
    assert r["available"] and r["coherent"] is True
    assert r["redundant_with_existing"] is False
    assert any(s["curie"].startswith("CL:") for s in r["inferred_superclasses"])
    # (b) mirror the real axiom CL:0000014 == CL:0000039 and (capable_of some GO:0017145)
    from types import SimpleNamespace as NS
    stub = NS(parent=NS(curie="CL:0000039", label="germ line cell"), location=None,
              surface=[], functions=[NS(curie="GO:0017145", label="stem cell division")])
    r2 = reasoning.classify_against_cl(stub, CL_OWL)
    assert r2["redundant_with_existing"] is True
    assert any(e["curie"] == "CL:0000014" for e in r2["equivalent_to"])


def test_classify_tool_error_is_not_incoherency():
    """Audit fix: a ROBOT/tool failure (here: a non-OWL --cl-owl file) must NOT be
    reported as a logical incoherency. Expect coherent is None (could-not-classify),
    never coherent=False. Self-skips without Java/ROBOT."""
    if not robot_tools.robot_available():
        print("    (skip: ROBOT/Java unavailable)"); return
    bogus = os.path.join(tempfile.mkdtemp(), "not_an_ontology.owl")
    with open(bogus, "w") as fh:
        fh.write("this is plainly not OWL\n")
    r = reasoning.classify_against_cl(_dossier(), bogus, timeout=120)
    assert r["available"] is True
    # must be the could-not-classify state, never coherent=False (a false incoherency)
    assert r.get("coherent") is None, "tool error misreported as coherent=%r" % r.get("coherent")
    assert "did not complete" in (r.get("note", "").lower())


def test_classify_no_differentia_is_not_a_duplicate():
    """Audit fix: a genus-only dossier (no location/function/surface differentia) must
    NOT be reported DUPLICATE_OF_EXISTING against its own genus — that's a misleading
    'already exists' verdict; expect INSUFFICIENT_DIFFERENTIA. Self-skips without Java."""
    if not (robot_tools.robot_available() and os.path.exists(CL_OWL)):
        print("    (skip: needs Java + robot.jar + cl-base.owl)"); return
    from types import SimpleNamespace as NS
    stub = NS(parent=NS(curie="CL:0000540", label="neuron"), location=None, surface=[], functions=[])
    r = reasoning.classify_against_cl(stub, CL_OWL, timeout=180)
    assert r["disposition"] == "INSUFFICIENT_DIFFERENTIA"
    assert r["redundant_with_existing"] is False and r["equivalent_to"] == []


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
