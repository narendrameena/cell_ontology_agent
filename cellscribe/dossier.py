"""The curation dossier — CellScribe's deliverable.

Not "an answer": a reviewable package (verdict + grounded terms + tested markers
+ cited evidence + computable draft + the agent's own trace), rendered to JSON,
Markdown, a ROBOT template and an OWL snippet.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import (Critique, CurationRequest, Definition, MarkerPanel, Paper,
                     Step, TermMatch)


@dataclass
class CurationDossier:
    request: CurationRequest
    existing: Optional[TermMatch] = None
    parent: Optional[TermMatch] = None
    location: Optional[TermMatch] = None
    functions: List[TermMatch] = field(default_factory=list)          # grounded GO functions
    surface: List[TermMatch] = field(default_factory=list)            # grounded PRO surface markers
    surface_ungrounded: List[str] = field(default_factory=list)       # symbols that didn't ground
    go_support: Dict[str, List[str]] = field(default_factory=dict)    # marker -> supporting GO ids
    panel: Optional[MarkerPanel] = None
    papers: List[Paper] = field(default_factory=list)
    definition: Optional[Definition] = None
    critique: Optional[Critique] = None
    trace: List[Step] = field(default_factory=list)
    llm_used: str = "none (deterministic)"
    sources: List[str] = field(default_factory=lambda: [
        "EBI OLS4 (Cell Ontology, Uberon)", "Europe PMC"])

    # ------------------------------------------------------------------ serialisers
    def to_dict(self) -> Dict[str, Any]:
        def d(x):
            return x.to_dict() if x is not None else None
        return {
            "request": self.request.to_dict(),
            "existing_match": d(self.existing),
            "parent": d(self.parent),
            "location": d(self.location),
            "functions": [f.to_dict() for f in self.functions],
            "surface_markers": [s.to_dict() for s in self.surface],
            "surface_ungrounded": self.surface_ungrounded,
            "go_marker_support": self.go_support,
            "marker_panel": d(self.panel),
            "literature": [p.to_dict() for p in self.papers],
            "definition": d(self.definition),
            "critique": d(self.critique),
            "trace": [s.to_dict() for s in self.trace],
            "llm_used": self.llm_used,
            "sources": self.sources,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_robot_tsv(self) -> str:
        if not self.definition:
            return ""
        rows = self.definition.robot_header + [self.definition.robot_row]
        return "\n".join("\t".join(str(c) for c in r) for r in rows)

    def to_owl(self) -> str:
        if not self.definition:
            return ""
        return ("# Manchester-syntax equivalence axiom (draft; ID pending)\n"
                "Class: %s\n    EquivalentTo:\n    %s"
                % (self.definition.robot_row[0], self.definition.manchester_owl))

    def to_markdown(self) -> str:
        r = self.request
        c = self.critique
        L: List[str] = []
        L.append("# CellScribe curation dossier — %s" % r.name)
        L.append("_Agentic Cell Ontology draft · sources: %s · LLM: %s_\n"
                 % (", ".join(self.sources), self.llm_used))

        if c:
            L.append("## Verdict")
            L.append("**Disposition: %s**" % c.disposition)
            flag = "  ⚠️ blocking issues to resolve" if c.needs_expert_review else ""
            L.append("Confidence **%.2f**%s" % (c.confidence, flag))
            L.append("_Human-in-the-loop: CellScribe never writes to CL — a curator makes the final call._\n")

        L.append("## Request")
        L.append("- name: **%s**" % r.name)
        if r.description:
            L.append("- description: %s" % r.description)
        if r.markers:
            L.append("- proposed markers: %s" % ", ".join(r.markers))
        if r.location_hint:
            L.append("- location hint: %s" % r.location_hint)
        if r.taxonomy_ref:
            L.append("- taxonomy ref: %s" % r.taxonomy_ref)
        L.append("")

        if self.existing:
            e = self.existing
            L.append("## Existing-term check")
            flag = "**possible duplicate**" if e.score >= 0.9 else "nearest existing term"
            L.append("- %s: %s (%s), match %.2f" % (flag, e.label, e.curie, e.score))
            if e.definition:
                L.append("  - _%s_" % e.definition[:200])
            L.append("")

        L.append("## Grounded terms")
        for role, t in [("genus / parent", self.parent), ("location", self.location)]:
            if t:
                L.append("- %s: **%s** `%s` (match %.2f, %s)"
                         % (role, t.label, t.curie, t.score, t.source))
        for f in self.functions:
            L.append("- GO function (`capable of`): **%s** `%s`" % (f.label, f.curie))
        for s in self.surface:
            L.append("- surface marker (`has plasma membrane part`): **%s** `%s`" % (s.label, s.curie))
        if self.surface_ungrounded:
            L.append("- surface markers not confidently grounded to PRO (verify): %s"
                     % ", ".join(self.surface_ungrounded))
        L.append("")

        if self.go_support:
            L.append("## GO-supported markers (Fig 1 / Table 1 intersection)")
            L.append("_Markers that are also annotated to a defining GO function "
                     "(QuickGO, evidence ECO:0000269/0000318) — higher-confidence:_")
            for m, gos in self.go_support.items():
                L.append("- **%s** ← %s" % (m, ", ".join(gos)))
            L.append("")

        if self.panel:
            p = self.panel
            L.append("## Marker panel (%s)" % p.method)
            L.append("- panel: **%s** — separation score **%.2f**"
                     % (", ".join(p.markers) if p.markers else "(none)", p.score))
            for g, st in p.per_gene.items():
                L.append("  - `%s`: precision %.2f, recall %.2f, F-beta %.2f"
                         % (g, st.get("precision", 0), st.get("recall", 0), st.get("fbeta", 0)))
            if p.note:
                L.append("  - _%s_" % p.note)
            L.append("")

        if self.papers:
            L.append("## Literature evidence (Europe PMC)")
            for pp in self.papers:
                cite = "%s %s. *%s* (%s). PMID %s" % (
                    pp.authors.split(",")[0] + " et al." if pp.authors else "",
                    pp.title, pp.journal, pp.year, pp.pmid)
                L.append("- %s" % cite.strip())
                if pp.snippet:
                    L.append("  - > %s" % pp.snippet)
            L.append("")

        if self.definition:
            df = self.definition
            L.append("## Drafted definition  _(drafted by: %s)_" % df.drafted_by)
            L.append("**Textual (genus-differentia):** %s\n" % df.textual)
            L.append("**OWL equivalence (Manchester):**")
            L.append("```\n%s\n```" % df.manchester_owl)
            L.append("**ROBOT template:**")
            L.append("```\n%s\n```" % self.to_robot_tsv())
            L.append("")

        if c:
            L.append("## Critique (verification & failure-mode checks)")
            L.append("- checks: " + ", ".join(
                "%s=%s" % (k, "✓" if v else "✗") for k, v in c.checks.items()))
            for i in c.issues:
                L.append("- ⚠️ %s" % i)
            for rec in c.recommendations:
                L.append("- → %s" % rec)
            L.append("")

        L.append("## Agent trace")
        for s in self.trace:
            L.append("%d. **%s** — %s" % (s.index, s.tool, s.action))
            if s.output_summary:
                L.append("   - %s" % s.output_summary)
            if s.provenance:
                L.append("   - _prov: %s_" % s.provenance)
        return "\n".join(L)

    # ------------------------------------------------------------------ io
    def save(self, outdir: str) -> Dict[str, str]:
        os.makedirs(outdir, exist_ok=True)
        slug = "".join(ch if ch.isalnum() else "_" for ch in self.request.name).strip("_")[:60] or "dossier"
        paths = {
            "json": os.path.join(outdir, slug + ".json"),
            "markdown": os.path.join(outdir, slug + ".md"),
            "robot": os.path.join(outdir, slug + ".robot.tsv"),
            "owl": os.path.join(outdir, slug + ".omn"),
        }
        with open(paths["json"], "w") as fh:
            fh.write(self.to_json())
        with open(paths["markdown"], "w") as fh:
            fh.write(self.to_markdown())
        with open(paths["robot"], "w") as fh:
            fh.write(self.to_robot_tsv())
        with open(paths["owl"], "w") as fh:
            fh.write(self.to_owl())
        return paths
