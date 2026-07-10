#!/usr/bin/env python3
"""Example 2 — curate a NOVEL type using an expression matrix.

The marker panel is tested on data (NS-Forest-style) rather than asserted.
CLARA grounds the genus + location, tests GAD1/GAD2/PVALB, drafts a computable
definition, and routes it for curator approval. Runs OFFLINE.

    python examples/02_marker_matrix.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault("CLARA_OFFLINE", "1")
os.environ.setdefault("CLARA_CACHE", os.path.join(ROOT, "demo_data", "fixtures"))

from clara import CuratorAgent, CurationRequest

CSV = os.path.join(ROOT, "demo_data", "striatum_demo_expr.csv")

agent = CuratorAgent(offline=True, use_llm=False, verbose=True)

request = CurationRequest(
    name="striatal parvalbumin-positive GABAergic interneuron",
    description="A GABAergic inhibitory interneuron of the striatum expressing parvalbumin",
    markers=["GAD1", "GAD2", "PVALB"],
    location_hint="striatum",
    expr_csv=CSV,                       # cells x genes + a 'cluster' column
    cluster_col="cluster",
    target_cluster="striatal_PV_interneuron",
    taxonomy_ref="example taxonomy",
)

dossier = agent.curate(request)

c = dossier.critique
print("\n================= RESULT =================")
print("Disposition :", c.disposition)
print("Confidence  : %.2f" % c.confidence)
print("Genus       :", dossier.parent.label, "(%s)" % dossier.parent.curie)
print("Location    :", dossier.location.label, "(%s)" % dossier.location.curie)
print("Marker panel:", dossier.panel.markers, "| score %.2f" % dossier.panel.score)
print("Papers      :", len(dossier.papers))
print("\n--- computable draft (OWL) ---")
print(dossier.to_owl())

out = dossier.save(os.path.join(HERE, "out"))
print("\nSaved dossier artefacts:")
for kind, path in out.items():
    print("  %-9s %s" % (kind, path))
