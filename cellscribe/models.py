"""Shared, dependency-free data models for CellScribe.

Everything a tool returns is a small, JSON-serialisable dataclass.  Keeping the
shapes explicit is deliberate: the whole design bet is *grounding + provenance*,
so every object carries where it came from.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TermMatch:
    """An ontology term grounded via EBI OLS (CL / Uberon / GO / PR / ...)."""
    query: str
    curie: str                      # e.g. "CL:0000617"
    iri: str
    label: str
    ontology: str                   # "cl", "uberon", ...
    definition: str = ""
    synonyms: List[str] = field(default_factory=list)
    score: float = 0.0              # OLS relevance (normalised 0-1)
    source: str = "EBI OLS4"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Paper:
    """A literature hit from Europe PMC."""
    pmid: str
    title: str
    authors: str = ""
    journal: str = ""
    year: str = ""
    doi: str = ""
    url: str = ""
    snippet: str = ""               # extracted evidence sentence(s)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarkerPanel:
    """A minimal marker set with a specificity score (NS-Forest-style)."""
    markers: List[str]
    score: float                    # 0-1, higher = cleaner separation
    method: str
    per_gene: Dict[str, Dict[str, float]] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Definition:
    """A drafted Cell Ontology entry: text + computable axioms + ROBOT row."""
    label: str
    textual: str
    manchester_owl: str
    obo_lines: List[str] = field(default_factory=list)
    robot_header: List[str] = field(default_factory=list)
    robot_row: List[str] = field(default_factory=list)
    relations: Dict[str, str] = field(default_factory=dict)
    drafted_by: str = "template"    # "template" or "llm:<model>"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Critique:
    """Output of the verification / self-critique step."""
    confidence: float               # 0-1
    needs_expert_review: bool       # blocking issues present?
    disposition: str = ""           # ALIGN / PROPOSE_NEW / INSUFFICIENT
    checks: Dict[str, bool] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Step:
    """One entry in the agent's reasoning/execution trace (for auditability)."""
    index: int
    tool: str
    action: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    output_summary: str = ""
    provenance: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CurationRequest:
    """What the curator (or an upstream atlas-ingest step) hands the agent."""
    name: str
    description: str = ""
    markers: List[str] = field(default_factory=list)          # transcriptomic (expression) markers
    surface_markers: List[str] = field(default_factory=list)  # cell-surface protein markers -> PRO
    functions: List[str] = field(default_factory=list)        # GO biological processes -> 'capable of'
    components: List[str] = field(default_factory=list)        # GO cellular components -> 'has part'
    location_hint: str = ""
    parent_hint: str = ""
    expr_csv: str = ""              # optional path to cells x genes matrix
    cluster_col: str = "cluster"
    target_cluster: str = ""
    taxonomy_ref: str = ""         # e.g. a BICAN taxonomy id / dataset DOI
    organism: str = "Homo sapiens"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
