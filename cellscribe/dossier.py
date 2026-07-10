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
    taxon: Optional[TermMatch] = None                                # grounded NCBITaxon
    official_name: str = ""                                           # T-type naming policy suggestion
    taxon_caveat: str = ""                                            # broadly-conserved location warning
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
            "taxon": d(self.taxon),
            "official_name": self.official_name,
            "taxon_caveat": self.taxon_caveat,
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
        if r.reference_data:
            L.append("- reference data: %s  _(data-linked T-type — mapping is a hypothesis)_" % r.reference_data)
        L.append("")

        if self.official_name and self.official_name != r.name:
            L.append("## Suggested official name (T-type naming policy)")
            L.append("**%s**  _(input name kept as a synonym)_\n" % self.official_name)
        if self.taxon:
            L.append("**Taxon:** %s `%s`  (asserted as `present_in_taxon`, RO:0002175)\n"
                     % (self.taxon.label, self.taxon.curie))
        if self.taxon_caveat:
            L.append("> ⚠️ **Taxon caveat:** %s\n" % self.taxon_caveat)

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

    # ------------------------------------------------------------ CL-native outputs
    def _synonyms(self) -> List[str]:
        # keep the source/input name as a synonym when we suggest a new official name
        if self.official_name and self.official_name != self.request.name:
            return [self.request.name]
        return []

    def to_kgcl(self) -> str:
        """Knowledge Graph Change Language — CL's near-English edit format."""
        if not self.definition:
            return ""
        nid = self.definition.robot_row[0]
        L = ["create class %s" % nid,
             'create edge %s rdfs:label "%s"' % (nid, self.official_name or self.request.name),
             'add definition to %s "%s"' % (nid, self.definition.textual)]
        if self.parent:
            L.append("create edge %s rdfs:subClassOf %s" % (nid, self.parent.curie))
        for syn in self._synonyms():
            L.append('create synonym "%s" for %s' % (syn, nid))
        return "\n".join(L)

    def to_miracl(self) -> str:
        """MIRACL (Minimal Information Reporting About a CelL) spreadsheet row."""
        hdr = ["proposed_name", "synonyms", "definition", "part_of_uberon", "genus_cl",
               "markers", "surface_markers_pro", "go_functions", "organism_ncbitaxon",
               "reference", "orcid"]
        row = [self.official_name or self.request.name, "|".join(self._synonyms()),
               self.definition.textual if self.definition else "",
               self.location.curie if self.location else "",
               self.parent.curie if self.parent else "",
               "|".join(self.panel.markers if self.panel else []),
               "|".join(s.curie for s in self.surface),
               "|".join(f.curie for f in self.functions),
               self.taxon.curie if self.taxon else "",
               self.request.reference_data or self.request.taxonomy_ref, self.request.orcid]
        return "\t".join(hdr) + "\n" + "\t".join(row)

    def to_github_issue(self) -> str:
        """Pre-filled CL 'new term request' issue (the fields CL editors ask for)."""
        L = ["### New cell type term request",
             "**Preferred label:** %s" % (self.official_name or self.request.name)]
        if self._synonyms():
            L.append("**Synonyms:** %s" % ", ".join(self._synonyms()))
        L.append("**Definition (with reference):** %s" % (self.definition.textual if self.definition else ""))
        L.append("**Part of (Uberon):** %s" % (
            "%s (%s)" % (self.location.label, self.location.curie) if self.location else "—"))
        L.append("**Genus / is_a (CL):** %s" % (
            "%s (%s)" % (self.parent.label, self.parent.curie) if self.parent else "—"))
        if self.panel and self.panel.markers:
            L.append("**Markers:** %s (%s)" % (", ".join(self.panel.markers), self.request.organism))
        pmids = [p.pmid for p in self.papers if p.pmid]
        if pmids:
            L.append("**References:** " + ", ".join("PMID:%s" % p for p in pmids))
        L.append("**Submitter ORCID:** %s" % (self.request.orcid or "(please add)"))
        if self.critique:
            L.append("\n_Auto-drafted by CellScribe · %s · confidence %.2f · requires curator review._"
                     % (self.critique.disposition, self.critique.confidence))
        return "\n".join(L)

    def to_sssom(self) -> str:
        """SSSOM mapping row (align-to-existing, or a cross-species bridge)."""
        if not self.existing:   # nothing to map to -> no SSSOM row (a new term is not a mapping)
            return "# no existing CL term to map to (this is a new-term proposal, not a mapping)"
        cross = self.taxon is not None and self.request.organism.lower() not in ("homo sapiens", "human")
        pred = "semapv:crossSpeciesExactMatch" if cross else "skos:exactMatch"
        hdr = ["subject_label", "predicate_id", "object_id", "object_label",
               "mapping_justification", "confidence", "subject_source"]
        row = [self.request.name, pred, self.existing.curie if self.existing else "",
               self.existing.label if self.existing else "", "semapv:ManualMappingCuration",
               "%.2f" % (self.existing.score if self.existing else 0.0), "CellScribe"]
        out = "\t".join(hdr) + "\n" + "\t".join(row)
        if cross:
            out += ("\n# HYPOTHESIS: cross-species mapping — transcriptomic similarity may reflect "
                    "convergence, not homology; requires expert review.")
        return out

    def to_kg_tsv(self) -> str:
        """Knowledge-graph edges (subject, predicate, object, provenance) for Neo4j/RDF load."""
        if not self.definition:
            return ""
        nid = self.definition.robot_row[0]
        rows = [["subject", "predicate", "object", "provenance"]]
        if self.parent:
            rows.append([nid, "is_a", self.parent.curie, "EBI OLS"])
        if self.location:
            rows.append([nid, "part_of", self.location.curie, "EBI OLS"])
        for f in self.functions:
            rows.append([nid, "capable_of", f.curie, "EBI OLS"])
        for s in self.surface:
            rows.append([nid, "has_plasma_membrane_part", s.curie, "PRO"])
        for m in (self.panel.markers if self.panel else []):
            prov = ("GO-supported:" + "/".join(self.go_support[m])) if m in self.go_support else "marker panel"
            rows.append([nid, "expresses", m, prov])
        if self.taxon:
            rows.append([nid, "present_in_taxon", self.taxon.curie, "NCBI Taxonomy"])
        return "\n".join("\t".join(r) for r in rows)

    # ------------------------------------------------------------------ io
    def save(self, outdir: str) -> Dict[str, str]:
        os.makedirs(outdir, exist_ok=True)
        slug = "".join(ch if ch.isalnum() else "_" for ch in self.request.name).strip("_")[:60] or "dossier"
        writers = {
            "json": (".json", self.to_json()),
            "markdown": (".md", self.to_markdown()),
            "robot": (".robot.tsv", self.to_robot_tsv()),
            "owl": (".omn", self.to_owl()),
            "kgcl": (".kgcl.txt", self.to_kgcl()),
            "miracl": (".miracl.tsv", self.to_miracl()),
            "issue": (".issue.md", self.to_github_issue()),
            "kg": (".kg.tsv", self.to_kg_tsv()),
        }
        if self.existing:                       # SSSOM only meaningful when aligning
            writers["sssom"] = (".sssom.tsv", self.to_sssom())
        paths = {}
        for key, (ext, content) in writers.items():
            p = os.path.join(outdir, slug + ext)
            with open(p, "w") as fh:
                fh.write(content)
            paths[key] = p
        return paths
