#!/usr/bin/env python3
"""CellScribe test suite — offline, deterministic, no pytest required.

Run either way:
    python tests/test_cellscribe.py      # self-running harness -> "N passed"
    pytest -q                       # standard pytest discovery

All tests run fully offline against the shipped fixtures in demo_data/fixtures,
so they are deterministic and need no network.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# Force offline + point the HTTP cache at the shipped fixtures BEFORE importing.
os.environ["CELLSCRIBE_OFFLINE"] = "1"
os.environ["CELLSCRIBE_CACHE"] = os.path.join(ROOT, "demo_data", "fixtures")

CSV = os.path.join(ROOT, "demo_data", "striatum_demo_expr.csv")

from cellscribe.agent import CuratorAgent, _derive_parent
from cellscribe.dossier import CurationDossier
from cellscribe.models import CurationRequest, MarkerPanel, TermMatch
from cellscribe.tools.definition import DefinitionDrafter
from cellscribe.tools.go_support import QuickGOTool, taxon_for
from cellscribe.tools.literature import build_query_cascade
from cellscribe.tools.markers import MarkerPanelTool
from cellscribe.tools.naming import suggest_official_name
from cellscribe.tools.ontology import OLSSearchTool
from cellscribe.tools.taxon import ground_taxon, taxon_caveat
from cellscribe.tools.validation import critique


# --------------------------------------------------------------- unit tests
def test_derive_parent_word_boundary():
    # "t cell" must NOT be matched inside "trophoblast cell"
    assert _derive_parent(
        "villous cytotrophoblast epithelial trophoblast cell of the placental villus"
    ) == "trophoblast cell"
    assert _derive_parent(
        "CD4-positive, alpha-beta T cell mature alpha-beta T cell expressing CD4"
    ) == "T cell"
    assert _derive_parent(
        "striatal parvalbumin-positive GABAergic interneuron"
    ) == "interneuron"


def test_ols_grounding_offline():
    ols = OLSSearchTool()
    cl = ols("interneuron", ontology="cl", rows=5, offline=True)
    assert cl and cl[0].curie == "CL:0000099", cl[:1]
    ub = ols("striatum", ontology="uberon", rows=5, offline=True)
    assert ub and ub[0].curie == "UBERON:0002435", ub[:1]


def test_ols_offline_miss_is_graceful():
    ols = OLSSearchTool()
    hits = ols("zzz_not_a_real_cell_type_qwerty", ontology="cl", offline=True)
    assert hits == []


def test_marker_panel_specificity():
    mp = MarkerPanelTool().from_matrix(
        CSV, "cluster", "striatal_PV_interneuron",
        candidate_genes=["GAD1", "GAD2", "PVALB", "SLC17A7", "AQP4"])
    assert "PVALB" in mp.markers
    assert mp.score >= 0.9, mp.score
    assert mp.method.startswith("NS-Forest")


def test_definition_drafter_owl_and_robot():
    parent = TermMatch("interneuron", "CL:0000099", "", "interneuron", "cl", score=1.0)
    loc = TermMatch("striatum", "UBERON:0002435", "", "striatum", "uberon", score=1.0)
    panel = MarkerPanel(markers=["GAD1", "PVALB"], score=1.0, method="test")
    d = DefinitionDrafter()("striatal PV interneuron", parent, loc, panel)
    assert d.textual.startswith("An interneuron")          # a/an grammar
    assert "expresses" in d.manchester_owl
    assert "part of" in d.manchester_owl
    assert d.robot_row[0] == "CL:NEW_0000001"
    assert d.robot_row[4] == "CL:0000099"                  # PARENT column


def test_critic_flags_duplicate():
    existing = TermMatch("x", "CL:0000624", "", "CD4-positive, alpha-beta T cell", "cl", score=1.0)
    parent = TermMatch("T cell", "CL:0000084", "", "T cell", "cl", score=1.0)
    panel = MarkerPanel(markers=["CD4"], score=0.8, method="prior")
    c = critique("CD4-positive, alpha-beta T cell", existing, parent, None, panel, papers=[])
    assert "ALIGN" in c.disposition
    assert c.needs_expert_review is True
    assert c.checks["not_duplicate"] is False


def test_query_cascade_relaxes():
    qs = build_query_cascade("striatal PV interneuron", ["GAD1", "PVALB"], "Homo sapiens")
    assert len(qs) >= 3
    assert "GAD1" in qs[0] and '"striatal PV interneuron"' in qs[0]   # precise first
    assert any(q == "(GAD1 OR PVALB)" for q in qs)                    # markers-only fallback present


# --------------------------------------------------------- integration (offline)
def test_agent_existing_type_aligns():
    agent = CuratorAgent(offline=True, use_llm=False, verbose=False)
    d = agent.curate(CurationRequest(
        name="CD4-positive, alpha-beta T cell",
        description="A mature alpha-beta T cell that expresses CD4",
        markers=["CD4", "IL7R"]))
    assert d.existing and d.existing.curie == "CL:0000624"
    assert "ALIGN" in d.critique.disposition
    assert d.critique.needs_expert_review is True


def test_agent_novel_type_proposes():
    agent = CuratorAgent(offline=True, use_llm=False, verbose=False)
    d = agent.curate(CurationRequest(
        name="striatal parvalbumin-positive GABAergic interneuron",
        description="A GABAergic inhibitory interneuron of the striatum expressing parvalbumin",
        markers=["GAD1", "GAD2", "PVALB"], location_hint="striatum",
        expr_csv=CSV, cluster_col="cluster", target_cluster="striatal_PV_interneuron"))
    assert d.parent and d.parent.curie == "CL:0000099"
    assert d.location and d.location.curie == "UBERON:0002435"
    assert "PVALB" in d.panel.markers and d.panel.score >= 0.9
    assert "PROPOSE" in d.critique.disposition
    assert d.critique.confidence >= 0.8


# ----------------------------------------------- GO / PRO / relations (paper-grounded)
def test_go_function_grounding():
    # rows=5 matches what the agent caches when grounding functions
    go = OLSSearchTool()("GABA biosynthetic process", ontology="go", rows=5, offline=True)
    assert go and go[0].curie == "GO:0009449", go[:1]


def test_surface_marker_grounds_to_pro():
    # bare 'CD4' fuzzy-matches CD44; the tool retries 'CD4 molecule' and requires an exact hit
    agent = CuratorAgent(offline=True, use_llm=False, verbose=False)
    cd4 = agent._ground_surface("CD4")
    assert cd4 is not None and cd4.curie == "PR:000001004", cd4


def test_go_marker_support_intersection():
    # GAD1/GAD2 ARE the GABA-synthesis enzymes; PVALB (an ID marker) is NOT annotated to synthesis
    go = TermMatch("GABA biosynthetic process", "GO:0009449", "", "GABA biosynthetic process", "go", score=1.0)
    support = QuickGOTool().support(["GAD1", "PVALB"], [go], organism="Homo sapiens", offline=True)
    assert "GAD1" in support and "GO:0009449" in support["GAD1"]
    assert "PVALB" not in support


def test_definition_uses_correct_relations():
    parent = TermMatch("interneuron", "CL:0000099", "", "interneuron", "cl", score=1.0)
    loc = TermMatch("striatum", "UBERON:0002435", "", "striatum", "uberon", score=1.0)
    func = TermMatch("GABA biosynthetic process", "GO:0009449", "", "GABA biosynthetic process", "go", score=1.0)
    surf = TermMatch("CD4", "PR:000001004", "", "CD4 molecule", "pr", score=1.0)
    d = DefinitionDrafter()("test type", parent, loc, MarkerPanel(["GAD1"], 1.0, "test"),
                            functions=[func], surface=[surf])
    assert "capable of" in d.manchester_owl              # GO function
    assert "has plasma membrane part" in d.manchester_owl  # surface protein
    assert "expresses" in d.manchester_owl               # transcriptomic marker
    assert d.relations["has plasma membrane part"] == "RO:0002104"
    assert d.relations["capable of"] == "RO:0002215"


def test_taxon_mapping():
    assert "9606" in taxon_for("Homo sapiens")
    assert "10090" in taxon_for("Mus musculus")


# ----------------------------------------------------- Tier 2/3 (taxon, naming, outputs)
def test_taxon_grounding():
    assert ground_taxon("Homo sapiens").curie == "NCBITaxon:9606"
    assert ground_taxon("Mus musculus").curie == "NCBITaxon:10090"
    assert ground_taxon("not a species") is None


def test_taxon_caveat_and_official_name():
    assert taxon_caveat("neuron", "striatum")            # broad genus + location -> caveat
    assert not taxon_caveat("interneuron", "striatum")   # specific genus -> no caveat
    nm = suggest_official_name("interneuron", ["GAD1", "PVALB"], "striatum")
    assert "interneuron" in nm and "GAD1/PVALB" in nm


def test_marker_panel_precision_recall_context():
    mp = MarkerPanelTool().from_matrix(
        CSV, "cluster", "striatal_PV_interneuron",
        candidate_genes=["GAD1", "GAD2", "PVALB", "AQP4"],
        species="Homo sapiens", context="striatum")
    assert 0.0 <= mp.precision <= 1.0 and 0.0 <= mp.recall <= 1.0
    assert mp.species == "Homo sapiens" and mp.context == "striatum"


def test_cl_native_outputs():
    req = CurationRequest(name="striatal PV interneuron", markers=["GAD1", "PVALB"],
                          location_hint="striatum", organism="Homo sapiens",
                          orcid="0000-0002-1825-0097", reference_data="CxG:dataset-v1")
    parent = TermMatch("interneuron", "CL:0000099", "", "interneuron", "cl", score=1.0)
    loc = TermMatch("striatum", "UBERON:0002435", "", "striatum", "uberon", score=1.0)
    func = TermMatch("GABA biosynthetic process", "GO:0009449", "", "GABA biosynthetic process", "go", score=1.0)
    panel = MarkerPanel(["GAD1", "PVALB"], 1.0, "test")
    d = DefinitionDrafter()(req.name, parent, loc, panel, functions=[func])
    doss = CurationDossier(request=req, parent=parent, location=loc, functions=[func],
                           panel=panel, definition=d, taxon=ground_taxon("Homo sapiens"),
                           official_name="interneuron of the striatum, GAD1/PVALB-expressing")
    assert "create class" in doss.to_kgcl()
    assert doss.to_miracl().splitlines()[0].startswith("proposed_name")
    assert "Preferred label" in doss.to_github_issue()
    kg = doss.to_kg_tsv()
    assert "part_of\tUBERON:0002435" in kg
    assert "capable_of\tGO:0009449" in kg
    assert "present_in_taxon\tNCBITaxon:9606" in kg


def test_sssom_align_output():
    req = CurationRequest(name="CD4-positive, alpha-beta T cell")
    existing = TermMatch("x", "CL:0000624", "", "CD4-positive, alpha-beta T cell", "cl", score=1.0)
    s = CurationDossier(request=req, existing=existing).to_sssom()
    assert "skos:exactMatch" in s and "CL:0000624" in s


# --------------------------------------------------------------- self-runner
def _main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print("  PASS  %s" % name)
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print("  FAIL  %s  -> %r" % (name, exc))
            failed += 1
    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
