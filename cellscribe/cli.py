"""Command-line interface for CellScribe.

    python -m cellscribe.cli curate --name "..." --markers GAD1,PVALB --location striatum --out out/
    python -m cellscribe.cli demo --out demo_output/
    python -m cellscribe.cli tools
"""
from __future__ import annotations

import argparse
import os
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
    if getattr(args, "reason", False):
        from cellscribe import reasoning
        dossier.reasoning = reasoning.classify(dossier)
        r = dossier.reasoning.get("reasoner") or {}
        if r.get("available"):
            print("Reason  : ELK coherent=%s, classifies under genus=%s"
                  % (r.get("coherent"), r.get("classifies_under_genus")))
        else:
            print("Reason  : structural %s (install a JRE + robot.jar for ELK)"
                  % dossier.reasoning["structural"])
    if getattr(args, "cl_owl", ""):
        from cellscribe import reasoning
        cc = reasoning.classify_against_cl(dossier, args.cl_owl)
        dossier.reasoning = cc
        if not cc.get("available"):
            print("Classify: %s" % cc.get("note"))
        elif cc.get("coherent") is False:
            print("Classify: INCOHERENT — %s" % cc.get("note"))
        elif cc.get("coherent") is None:
            print("Classify: could not classify — %s" % cc.get("note"))
        else:
            sup = ", ".join("%s (%s)" % (s["label"] or "?", s["curie"]) for s in cc["inferred_superclasses"]) or "—"
            print("Classify: %s  [ELK vs %s]" % (cc["disposition"], os.path.basename(args.cl_owl)))
            print("          inferred superclasses: %s" % sup)
            if cc["redundant_with_existing"]:
                dup = ", ".join("%s (%s)" % (e["label"] or "?", e["curie"]) for e in cc["equivalent_to"])
                print("          ⚠ already in CL — equivalent to: %s" % dup)
    if getattr(args, "robot_owl", ""):
        from cellscribe.tools import robot_tools
        ok, msg = robot_tools.materialize_dossier(dossier, args.robot_owl, reason_after=True)
        print("ROBOT   : template->OWL %s -> %s  [%s]" % ("ok" if ok else "FAILED", args.robot_owl, msg[:80]))
    if args.out:
        paths = dossier.save(args.out)
        print("\nSaved: " + ", ".join(paths.values()))
    return 0


def cmd_integrations(args) -> int:
    from cellscribe import integrations
    print("CellScribe ecosystem integrations (live if the package/tool is installed):\n")
    for name, live in integrations.status().items():
        print("  [%s] %s" % ("live" if live else " -- ", name))
    print("\nVerified LLM hand-off targets (import paths checked against the real packages):")
    for name, e in integrations.verify_handoffs().items():
        if not e["installed"]:
            mark = "not installed (needs Python >=3.10/3.11 + LLM key)"
        elif e["resolved"]:
            mark = "resolved"
        elif e["needs_key"]:
            mark = "import OK; live call needs an LLM key"
        else:
            mark = "ERROR: %s" % e["error"]
        print("  %-16s -> %-52s [%s]" % (name, e["target"], mark))
    from cellscribe import llm_ecosystem as L
    s = L.status()
    print("\nLive LLM hand-off (OntoGPT/SPIRES via subprocess):")
    print("  venv        : %s" % (s["venv"] or "not built (run scripts/setup_llm_env.sh)"))
    print("  model       : %s  (key var %s: %s)"
          % (s["model"], s["key_var"], "SET" if s["key_present"] else "unset — get a free one at console.groq.com"))
    print("\n(built-in fallbacks run when an integration is unavailable)")
    return 0


def cmd_llm_extract(args) -> int:
    from cellscribe import llm_ecosystem as L
    text = args.text
    if not text and args.name:
        text = args.name + (". " + args.description if args.description else "")
    if not text:
        print("provide --text or --name"); return 2
    model = args.model or L.DEFAULT_MODEL

    if args.engine == "ontogpt":   # native OntoGPT CLI (needs the venv + a grounding backend)
        print("Running OntoGPT SPIRES (cell_type template) via %s ...\n" % model)
        r = L.ontogpt_cell_type(text, model=model)
        if not r["ok"]:
            print("Live extraction unavailable: %s" % r.get("error"))
            if r.get("needs_key"):
                print("  -> set %s in your environment, then re-run" % r.get("key_var", "OPENAI_API_KEY"))
            if r.get("needs_venv"):
                print("  -> bash scripts/setup_llm_env.sh")
            return 1
        print("Model: %s" % r["model"])
        for e in r.get("named_entities", []):
            print("  %-16s %s" % (e["id"], e["label"]))
        print("\n--- raw SPIRES output (first 1500 chars) ---")
        print((r.get("raw") or "")[:1500])
        return 0

    # default: keyless-grounding path — LLM extraction + CellScribe's OLS grounder
    print("SPIRES-style extraction via %s → grounding via EBI OLS (no extra key) ...\n" % model)
    r = L.extract_celltype_facts(text, model=model)
    if not r["ok"]:
        print("Live extraction unavailable: %s" % r.get("error"))
        if r.get("needs_key"):
            print("  -> set %s in your environment, then re-run" % r.get("key_var", "OPENAI_API_KEY"))
        return 1
    facts = r["facts"]
    print("Extracted by %s:" % r["model"])
    for k in ("cell_type", "transcriptomic_markers", "surface_markers", "location", "functions"):
        if facts.get(k) not in (None, "", []):
            print("  %-22s %s" % (k, facts[k]))

    from cellscribe.tools.ontology import OLSSearchTool, best_match
    tool = OLSSearchTool()

    def _g(label, onto):
        if not label:
            return None
        m = best_match(tool, str(label), ontology=onto)
        return "%s (%s)" % (m.label, m.curie) if m else "unmatched"

    def _as_list(v):                       # the LLM may return a bare string for a 1-item field
        if isinstance(v, list):
            return v
        return [] if v in (None, "") else [v]

    print("\nGrounded to ontologies (EBI OLS4):")
    if facts.get("cell_type"):
        print("  cell type  → %s" % _g(facts["cell_type"], "cl"))
    if facts.get("location"):
        print("  location   → %s" % _g(facts["location"], "uberon"))
    for fn in _as_list(facts.get("functions"))[:4]:
        print("  function   → %s" % _g(fn, "go"))
    for mk in _as_list(facts.get("surface_markers"))[:4]:
        print("  surface    → %s" % _g(mk, "pr"))
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
    c.add_argument("--reason", action="store_true", help="run the ELK reasoner over the self-contained draft (needs Java + robot.jar)")
    c.add_argument("--cl-owl", default="", help="classify the draft against a real CL import module "
                                                "(e.g. cl-base.owl): ELK places it in the CL hierarchy and "
                                                "flags duplicates of existing terms (needs Java + robot.jar)")
    c.add_argument("--robot-owl", default="", help="materialise the draft into an OWL file via ROBOT")
    c.set_defaults(func=cmd_curate)

    d = sub.add_parser("demo", help="run the bundled worked examples")
    d.add_argument("--out", default="demo_output")
    d.add_argument("--offline", action="store_true")
    d.add_argument("--no-llm", action="store_true")
    d.set_defaults(func=cmd_demo)

    t = sub.add_parser("tools", help="list the tool registry")
    t.set_defaults(func=cmd_tools)

    i = sub.add_parser("integrations", help="show which ecosystem integrations are live")
    i.set_defaults(func=cmd_integrations)

    le = sub.add_parser("llm-extract", help="live OntoGPT/SPIRES cell_type extraction via an LLM (default Groq free tier)")
    le.add_argument("--text", default="", help="text to extract from (e.g. an abstract or description)")
    le.add_argument("--name", default="", help="cell-type name (used as text if --text omitted)")
    le.add_argument("--description", default="")
    le.add_argument("--model", default="", help="model (default groq/llama-3.3-70b-versatile)")
    le.add_argument("--engine", default="direct", choices=["direct", "ontogpt"],
                    help="direct = LLM + OLS grounding (keyless); ontogpt = native OntoGPT CLI (needs grounding backend)")
    le.set_defaults(func=cmd_llm_extract)
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
