#!/usr/bin/env python3
"""Example 1 — use CLARA programmatically (no CLI).

An EXISTING type: CLARA recognises it's already in CL and says "align, don't
create". Runs OFFLINE from the shipped fixtures, so no network is needed.

    python examples/01_curate_api.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault("CLARA_OFFLINE", "1")
os.environ.setdefault("CLARA_CACHE", os.path.join(ROOT, "demo_data", "fixtures"))

from clara import CuratorAgent, CurationRequest

agent = CuratorAgent(offline=True, use_llm=False, verbose=True)

request = CurationRequest(
    name="CD4-positive, alpha-beta T cell",
    description="A mature alpha-beta T cell that expresses CD4",
    markers=["CD4", "IL7R"],
)

dossier = agent.curate(request)

print("\n================= DOSSIER (markdown) =================\n")
print(dossier.to_markdown())

# Other renderings are available too:
#   dossier.to_json()        -> str
#   dossier.to_robot_tsv()   -> str (ROBOT template)
#   dossier.to_owl()         -> str (Manchester OWL)
#   dossier.save("out_dir")  -> writes all four to disk
