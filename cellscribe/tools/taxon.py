"""Taxon grounding and taxon constraints (Tan et al. 2026, "Taxon constraints").

CL formalises whether a cell type exists in a taxon with `in_taxon` (RO:0002162),
`never_in_taxon` (RO:0002161) and `present_in_taxon` (RO:0002175), so a reasoner
can flag assertions that are not valid in all species where the type occurs (the
paper's example: 'taste receptor cell' must not be part_of 'tongue' because
arthropods have taste receptor cells but no tongue).

CellScribe grounds the organism to NCBITaxon and emits `present_in_taxon`, and
warns when a broadly-conserved genus is given a specific location that may not
hold across all its taxa.
"""
from __future__ import annotations

from typing import Optional

from ..models import TermMatch

# curated organism -> NCBITaxon (the species CL/BICAN atlases work with)
NCBITAXON = {
    "homo sapiens": ("NCBITaxon:9606", "Homo sapiens"),
    "human": ("NCBITaxon:9606", "Homo sapiens"),
    "mus musculus": ("NCBITaxon:10090", "Mus musculus"),
    "mouse": ("NCBITaxon:10090", "Mus musculus"),
    "macaca mulatta": ("NCBITaxon:9544", "Macaca mulatta"),
    "callithrix jacchus": ("NCBITaxon:9483", "Callithrix jacchus"),
    "rattus norvegicus": ("NCBITaxon:10116", "Rattus norvegicus"),
    "danio rerio": ("NCBITaxon:7955", "Danio rerio"),
    "drosophila melanogaster": ("NCBITaxon:7227", "Drosophila melanogaster"),
}
PRESENT_IN_TAXON = "RO:0002175"
IN_TAXON = "RO:0002162"
NEVER_IN_TAXON = "RO:0002161"

# very general genera where a specific location/marker may not hold across all taxa
_BROAD = ("neuron", "muscle cell", "epithelial cell", "fibroblast", "endothelial cell",
          "glial cell", "stem cell", "secretory cell", "leukocyte", "cell")


def ground_taxon(organism: str) -> Optional[TermMatch]:
    t = NCBITAXON.get((organism or "").lower().strip())
    if not t:
        return None
    return TermMatch(query=organism, curie=t[0], iri="", label=t[1],
                     ontology="ncbitaxon", score=1.0, source="NCBI Taxonomy")


def taxon_caveat(genus_label: str, location_label: str) -> str:
    if location_label and genus_label and genus_label.lower() in _BROAD:
        return ("Genus '%s' is broadly conserved across taxa; verify that location '%s' holds "
                "in ALL species where this cell type exists before asserting part_of "
                "(cf. taste receptor cell / tongue). Consider a taxon constraint."
                % (genus_label, location_label))
    return ""
