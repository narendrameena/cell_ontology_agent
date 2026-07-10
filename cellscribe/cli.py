"""Command-line interface for CellScribe.

    python -m cellscribe.cli curate --name "..." --markers GAD1,PVALB --location striatum --out out/
    python -m cellscribe.cli demo --out demo_output/
    python -m cellscribe.cli tools
"""
from __future__ import annotations

import argparse
import sys
from typing import List

from .agent import CuratorAgent
from .models import CurationRequest


def _csv(s: str) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _print_summary(dossier) -> None:
    c = dossier.critique
    print("\n" + "=" * 70)
    print("DOSSIER: %s" % dossier.request.name)
    print("=" * 70)
    if c:
        print("Verdict : %s" % c.disposition)
        flag = "  [blocking issues]" if c.needs_expert_review else ""
        print("Conf.   : %.2f%s  (curator makes the final call)" % (c.confidence, flag))
    if dossier.existing and dossier.existing.score >= 0.9:
        print("Existing: possible duplicate of %s (%s)"
              % (dossier.existing.label, dossier.existing.curie))
    if dossier.parent:
        print("Parent  : %s (%s)" % (dossier.parent.label, dossier.parent.curie))
    if dossier.location:
        print("Location: %s (%s)" % (dossier.location.label, dossier.location.curie))
    if dossier.panel:
        print("Markers : [%s] score %.2f" % (", ".join(dossier.panel.markers), dossier.panel.score))
    print("Papers  : %d" % len(dossier.papers))
    if dossier.definition:
        print("Draft   : %s" % dossier.definition.textual)
    if c and c.issues:
        print("Issues  :")
        for i in c.issues:
            print("   - %s" % i)


def cmd_curate(args) -> int:
    agent = CuratorAgent(offline=args.offline, use_llm=not args.no_llm, verbose=True)
    req = CurationRequest(
        name=args.name, description=args.description or "", markers=_csv(args.markers),
        surface_markers=_csv(args.surface_markers), functions=_csv(args.functions),
        components=_csv(args.components),
        location_hint=args.location or "", parent_hint=args.parent or "",
        expr_csv=args.expr or "", cluster_col=args.cluster_col,
        target_cluster=args.target or "", taxonomy_ref=args.taxonomy or "",
        reference_data=args.reference or "", orcid=args.orcid or "",
        organism=args.organism)
    dossier = agent.curate(req)
    _print_summary(dossier)
    if args.out:
        paths = dossier.save(args.out)
        print("\nSaved: " + ", ".join(paths.values()))
    return 0


def cmd_tools(args) -> int:
    agent = CuratorAgent(use_llm=False, verbose=False)
    print("CellScribe tool registry (Biomni-E1-style declarative schemas):\n")
    for t in agent.registry.all():
        print("• %s" % t.spec.name)
        print("    %s" % t.spec.description)
        print("    inputs : %s" % t.spec.input_schema)
        print("    returns: %s" % t.spec.returns)
        print("    tags   : %s\n" % ", ".join(t.spec.tags))
    return 0


def cmd_demo(args) -> int:
    from .demo import run_demo
    run_demo(out=args.out, offline=args.offline, use_llm=not args.no_llm)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cellscribe", description="Agentic Cell Ontology curation assistant.")
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("curate", help="curate one cell type")
    c.add_argument("--name", required=True)
    c.add_argument("--description", default="")
    c.add_argument("--markers", default="", help="comma-separated transcriptomic (expression) markers")
    c.add_argument("--surface-markers", default="", help="cell-surface protein markers (grounded to PRO)")
    c.add_argument("--functions", default="", help="GO biological-process functions (grounded to GO)")
    c.add_argument("--components", default="", help="GO cellular components")
    c.add_argument("--location", default="", help="anatomical location (grounded to Uberon)")
    c.add_argument("--parent", default="", help="parent/genus hint (grounded to CL)")
    c.add_argument("--expr", default="", help="path to cells x genes CSV with a cluster column")
    c.add_argument("--cluster-col", default="cluster")
    c.add_argument("--target", default="", help="target cluster label in the CSV")
    c.add_argument("--taxonomy", default="", help="taxonomy/dataset reference")
    c.add_argument("--reference", default="", help="versioned reference-dataset link (data-linked T-type)")
    c.add_argument("--orcid", default="", help="submitter ORCID (for the GitHub new-term issue)")
    c.add_argument("--organism", default="Homo sapiens")
    c.add_argument("--out", default="", help="output directory for the dossier")
    c.add_argument("--offline", action="store_true", help="cache-only, no network")
    c.add_argument("--no-llm", action="store_true", help="force deterministic mode")
    c.set_defaults(func=cmd_curate)

    d = sub.add_parser("demo", help="run the bundled worked examples")
    d.add_argument("--out", default="demo_output")
    d.add_argument("--offline", action="store_true")
    d.add_argument("--no-llm", action="store_true")
    d.set_defaults(func=cmd_demo)

    t = sub.add_parser("tools", help="list the tool registry")
    t.set_defaults(func=cmd_tools)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
