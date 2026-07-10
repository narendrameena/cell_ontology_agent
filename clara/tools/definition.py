"""Draft a Cell Ontology entry: human-readable text + computable axioms.

Produces the four artefacts a curator actually needs to review:
  * a genus-differentia textual definition,
  * an OWL class expression (Manchester syntax) for the equivalence axiom,
  * OBO-style logical-definition lines, and
  * a ROBOT template row (the format CL is edited in).

Everything is composed from *grounded* terms (real CURIEs) and the tested
marker panel — never free-text invented by a model.
"""
from __future__ import annotations

from typing import List, Optional

from ..models import Definition, MarkerPanel, TermMatch
from ..registry import Tool, ToolSpec

# Relations used in CL logical definitions
REL = {
    "part of": "BFO:0000050",
    "expresses": "RO:0002292",
}
PENDING_ID = "CL:NEW_0000001"   # placeholder until an ID range is minted


class DefinitionDrafter(Tool):
    spec = ToolSpec(
        name="draft_definition",
        description="Compose a genus-differentia definition, an OWL/Manchester equivalence "
                    "axiom, OBO logical-definition lines and a ROBOT template row from "
                    "grounded parent/location terms and a marker panel.",
        tags=["definition", "owl", "robot", "axiom", "logical definition", "draft",
              "genus differentia", "curation"],
        input_schema={"name": "str", "parent": "TermMatch", "location": "TermMatch",
                      "panel": "MarkerPanel"},
        returns="Definition",
    )

    def __call__(self, name: str, parent: Optional[TermMatch],
                 location: Optional[TermMatch], panel: Optional[MarkerPanel],
                 function: Optional[TermMatch] = None,
                 organism: str = "Homo sapiens") -> Definition:
        genus_label = parent.label if parent else "cell"
        genus_curie = parent.curie if parent else "CL:0000000"
        markers = panel.markers if panel else []

        # ---- textual (genus-differentia) ----
        clauses = []
        if location:
            clauses.append("located in the %s" % location.label)
        if markers:
            clauses.append("expressing " + ", ".join(markers))
        diff = (" that is " + " and ".join(clauses)) if clauses else ""
        article = "An" if genus_label[:1].lower() in "aeiou" else "A"
        textual = "%s %s%s." % (article, genus_label, diff)
        if organism and organism.lower() != "homo sapiens":
            textual = textual[:-1] + " (%s)." % organism

        # ---- Manchester OWL (equivalence) ----
        man = ["'%s'" % genus_label]
        if location:
            man.append("('part of' some '%s')" % location.label)
        for m in markers:
            man.append("('expresses' some %s)" % m)
        manchester = "\n    and ".join(man)

        # ---- OBO logical-definition lines ----
        obo = ["[Term]", "id: %s" % PENDING_ID, "name: %s" % name,
               'def: "%s" [%s]' % (textual, "CLARA:auto-draft"),
               "is_a: %s ! %s" % (genus_curie, genus_label)]
        if location:
            obo.append("intersection_of: %s ! %s" % (genus_curie, genus_label))
            obo.append("intersection_of: %s %s ! part of %s"
                       % (REL["part of"], location.curie, location.label))
        for m in markers:
            obo.append("relationship: %s %s ! expresses %s" % (REL["expresses"], m, m))

        # ---- ROBOT template ----
        header = ["ID", "LABEL", "TYPE", "DEFINITION", "PARENT", "EQUIVALENT", "MARKERS"]
        robot_directives = ["ID", "LABEL", "TYPE", "A IAO:0000115", "SC %",
                            "EC 'cell'", "A CLARA:marker SPLIT=|"]
        eq = "%s%s%s" % (
            "'%s'" % genus_label,
            (" and ('part of' some '%s')" % location.label) if location else "",
            "".join(" and ('expresses' some %s)" % m for m in markers),
        )
        row = [PENDING_ID, name, "owl:Class", textual, genus_curie, eq, "|".join(markers)]

        return Definition(
            label=name, textual=textual, manchester_owl=manchester,
            obo_lines=obo, robot_header=[header, robot_directives], robot_row=row,
            relations=REL,
        )
