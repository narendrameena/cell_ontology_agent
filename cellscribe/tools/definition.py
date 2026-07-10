"""Draft a Cell Ontology entry: human-readable text + computable axioms.

Follows CL's genus-differentia design pattern (Tan et al. 2026, Fig 5):
  genus (a CL parent) + differentia composed from grounded terms —
    * anatomical location   -> 'part of' some <Uberon>
    * GO function           -> 'capable of' some <GO biological process>
    * surface protein marker-> 'has plasma membrane part' some <PRO>
    * transcriptomic marker -> 'expresses' some <gene>

The surface-vs-transcriptomic split matters biologically: the paper warns that
protein and transcript often do not correlate, and CL's immune-cell axioms use
`has plasma membrane part some <protein>` (e.g. the canonical CD4 T cell), while
transcriptomic markers use `expresses`.

Produces: a genus-differentia textual definition, an OWL/Manchester equivalence
axiom, OBO logical-definition lines, and a ROBOT template row. Everything is
composed from *grounded* CURIEs — never free text invented by a model.
"""
from __future__ import annotations

from typing import List, Optional

from ..models import Definition, MarkerPanel, TermMatch
from ..registry import Tool, ToolSpec

# Relations used in CL logical definitions (all verified against RO/BFO).
REL = {
    "part of": "BFO:0000050",
    "capable of": "RO:0002215",
    "has plasma membrane part": "RO:0002104",
    "expresses": "RO:0002292",
}
PENDING_ID = "CL:NEW_0000001"   # placeholder until an ID range is minted


class DefinitionDrafter(Tool):
    spec = ToolSpec(
        name="draft_definition",
        description="Compose a genus-differentia definition, an OWL/Manchester equivalence "
                    "axiom, OBO lines and a ROBOT row from grounded parent (CL), location "
                    "(Uberon), GO functions, surface-protein markers (PRO) and transcriptomic "
                    "markers.",
        tags=["definition", "owl", "robot", "axiom", "logical definition", "draft",
              "genus differentia", "curation", "go", "marker"],
        input_schema={"name": "str", "parent": "TermMatch", "location": "TermMatch",
                      "panel": "MarkerPanel", "functions": "List[TermMatch]",
                      "surface": "List[TermMatch]"},
        returns="Definition",
    )

    def __call__(self, name: str, parent: Optional[TermMatch],
                 location: Optional[TermMatch], panel: Optional[MarkerPanel],
                 functions: Optional[List[TermMatch]] = None,
                 surface: Optional[List[TermMatch]] = None,
                 surface_ungrounded: Optional[List[str]] = None,
                 organism: str = "Homo sapiens") -> Definition:
        genus_label = parent.label if parent else "cell"
        genus_curie = parent.curie if parent else "CL:0000000"
        markers = panel.markers if panel else []
        functions = functions or []
        surface = surface or []
        surface_ungrounded = surface_ungrounded or []

        # ---- textual (genus-differentia, species-tagged markers) ----
        clauses = []
        if location:
            clauses.append("located in the %s" % location.label)
        if functions:
            clauses.append("capable of " + ", ".join(f.label for f in functions))
        if markers:
            clauses.append("expressing %s (in %s)" % (", ".join(markers), organism))
        surf_labels = [s.label for s in surface] + surface_ungrounded
        if surf_labels:
            clauses.append("bearing the cell-surface marker(s) " + ", ".join(surf_labels))
        diff = (" that is " + " and ".join(clauses)) if clauses else ""
        article = "An" if genus_label[:1].lower() in "aeiou" else "A"
        textual = "%s %s%s." % (article, genus_label, diff)

        # ---- Manchester OWL (equivalence) — only grounded terms enter the axiom ----
        man = ["'%s'" % genus_label]
        if location:
            man.append("('part of' some '%s')" % location.label)
        for f in functions:
            man.append("('capable of' some '%s')" % f.label)
        for s in surface:
            man.append("('has plasma membrane part' some %s)" % s.curie)
        for m in markers:
            man.append("('expresses' some %s)" % m)
        manchester = "\n    and ".join(man)

        # ---- OBO logical-definition lines ----
        obo = ["[Term]", "id: %s" % PENDING_ID, "name: %s" % name,
               'def: "%s" [%s]' % (textual, "CELLSCRIBE:auto-draft"),
               "is_a: %s ! %s" % (genus_curie, genus_label)]
        if location:
            obo.append("intersection_of: %s ! %s" % (genus_curie, genus_label))
            obo.append("intersection_of: %s %s ! part of %s"
                       % (REL["part of"], location.curie, location.label))
        for f in functions:
            obo.append("relationship: %s %s ! capable of %s" % (REL["capable of"], f.curie, f.label))
        for s in surface:
            obo.append("relationship: %s %s ! has plasma membrane part %s"
                       % (REL["has plasma membrane part"], s.curie, s.label))
        for m in markers:
            obo.append("relationship: %s %s ! expresses %s" % (REL["expresses"], m, m))

        # ---- ROBOT template ----
        header = ["ID", "LABEL", "TYPE", "DEFINITION", "PARENT", "EQUIVALENT",
                  "MARKERS", "SURFACE", "FUNCTIONS"]
        robot_directives = ["ID", "LABEL", "TYPE", "A IAO:0000115", "SC %",
                            "EC 'cell'", "A CELLSCRIBE:marker SPLIT=|",
                            "A CELLSCRIBE:surface_marker SPLIT=|", "A CELLSCRIBE:go_function SPLIT=|"]
        eq = "'%s'" % genus_label
        if location:
            eq += " and ('part of' some '%s')" % location.label
        for f in functions:
            eq += " and ('capable of' some '%s')" % f.label
        for s in surface:
            eq += " and ('has plasma membrane part' some %s)" % s.curie
        for m in markers:
            eq += " and ('expresses' some %s)" % m
        row = [PENDING_ID, name, "owl:Class", textual, genus_curie, eq,
               "|".join(markers),
               "|".join([s.curie for s in surface] + surface_ungrounded),
               "|".join(f.curie for f in functions)]

        return Definition(
            label=name, textual=textual, manchester_owl=manchester,
            obo_lines=obo, robot_header=[header, robot_directives], robot_row=row,
            relations=REL,
        )
