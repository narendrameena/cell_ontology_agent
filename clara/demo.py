"""Two worked examples that exercise the whole agent.

  A) An existing type — "CD4-positive, alpha-beta T cell".
     CLARA should recognise it already exists in CL and say *align, don't create*.

  B) A novel brain type — "striatal parvalbumin-positive GABAergic interneuron",
     with a real marker panel tested on a (bundled, synthetic) expression matrix.
     CLARA should ground the genus (interneuron) and location (striatum), test
     GAD1/GAD2/PVALB, pull literature, draft a computable definition, and flag it
     for expert review.
"""
from __future__ import annotations

import os
from typing import Optional

from .agent import CuratorAgent
from .models import CurationRequest

DEMO_CSV = os.path.join(os.path.dirname(__file__), "..", "demo_data",
                        "striatum_demo_expr.csv")


def run_demo(out: str = "demo_output", offline: Optional[bool] = None,
             use_llm: bool = True) -> None:
    agent = CuratorAgent(offline=offline, use_llm=use_llm, verbose=True)

    print("\n########## EXAMPLE A — existing type (expect: align, don't create) ##########")
    a = CurationRequest(
        name="CD4-positive, alpha-beta T cell",
        description="A mature alpha-beta T cell that expresses CD4",
        markers=["CD4", "IL7R"], organism="Homo sapiens")
    da = agent.curate(a)
    pa = da.save(out)

    print("\n########## EXAMPLE B — novel brain type (expect: grounded draft, review) ##########")
    b = CurationRequest(
        name="striatal parvalbumin-positive GABAergic interneuron",
        description="A GABAergic inhibitory interneuron of the striatum expressing parvalbumin",
        markers=["GAD1", "GAD2", "PVALB"],
        location_hint="striatum",
        expr_csv=DEMO_CSV if os.path.exists(DEMO_CSV) else "",
        cluster_col="cluster", target_cluster="striatal_PV_interneuron",
        taxonomy_ref="BICAN Human Basal Ganglia consensus taxonomy (illustrative)",
        organism="Homo sapiens")
    db = agent.curate(b)
    pb = db.save(out)

    print("\n\nDossiers written to: %s" % os.path.abspath(out))
    for p in list(pa.values()) + list(pb.values()):
        print("  - %s" % p)
