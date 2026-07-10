"""CuratorAgent — the A1-style orchestrator.

Flow (mirrors Biomni-A1: retrieve -> plan -> execute code/tools -> self-critique):

    retrieve relevant tools
      -> ground the type in CL (already exists?)
      -> ground a parent (genus) and location  [self-corrects once if ungrounded]
      -> gather literature evidence
      -> test the marker panel (NS-Forest-style, or evidence-weighted prior)
      -> draft a computable definition (optionally LLM-polished prose)
      -> critique: grounding / duplication / support -> confidence + review flag

Every step is appended to an auditable trace.
"""
from __future__ import annotations

import re
import sys
from typing import List, Optional

from .dossier import CurationDossier
from .llm import LLMClient
from .models import CurationRequest, MarkerPanel, Step, TermMatch
from .registry import ToolRegistry
from .tools.definition import DefinitionDrafter
from .tools.literature import EuropePMCTool
from .tools.markers import MarkerPanelTool
from .tools.ontology import OLSSearchTool
from .tools.validation import critique

# Ordered specific -> generic. Match on word-START boundaries (\b<key>) so that,
# e.g., "t cell" does NOT match inside "trophoblast cell", while a prefix like
# "epithel" still matches "epithelial".
_PARENT_HINTS = [
    (("interneuron", "gabaergic", "inhibitory"), "interneuron"),
    (("glutamatergic", "excitatory", "pyramidal"), "glutamatergic neuron"),
    (("dopaminergic",), "dopaminergic neuron"),
    (("cd4", "cd8", "thymocyte"), "T cell"),
    (("t cell", "t-cell", "t lymphocyte"), "T cell"),
    (("b cell", "b-cell", "plasma cell"), "B cell"),
    (("macrophage", "microglia", "monocyte", "kupffer"), "macrophage"),
    (("astrocyte",), "astrocyte"),
    (("oligodendrocyte",), "oligodendrocyte"),
    (("trophoblast", "cytotrophoblast", "syncytiotrophoblast"), "trophoblast cell"),
    (("neuron",), "neuron"),
    (("epithel",), "epithelial cell"),
    (("fibroblast",), "fibroblast"),
    (("endotheli",), "endothelial cell"),
]


def _derive_parent(text: str) -> str:
    t = text.lower()
    for keys, phrase in _PARENT_HINTS:
        for k in keys:
            if re.search(r"\b" + re.escape(k), t):
                return phrase
    return "cell"


class CuratorAgent:
    def __init__(self, offline: Optional[bool] = None, use_llm: bool = True,
                 verbose: bool = True) -> None:
        self.offline = offline
        self.verbose = verbose
        self.registry = ToolRegistry()
        self.ols = self.registry.register(OLSSearchTool())
        self.lit = self.registry.register(EuropePMCTool())
        self.mark = self.registry.register(MarkerPanelTool())
        self.drafter = self.registry.register(DefinitionDrafter())
        self.llm = LLMClient() if use_llm else LLMClient.__new__(LLMClient)
        if not use_llm:
            self.llm.provider = None

    # ------------------------------------------------------------------ util
    def _log(self, trace: List[Step], tool: str, action: str, summary: str = "",
             prov: str = "", **inputs) -> None:
        step = Step(index=len(trace) + 1, tool=tool, action=action,
                    inputs=inputs, output_summary=summary, provenance=prov)
        trace.append(step)
        if self.verbose:
            print("  [%d] %-16s %s%s" % (step.index, tool, action,
                                         (" — " + summary) if summary else ""),
                  flush=True)

    # ------------------------------------------------------------------ main
    def curate(self, request: CurationRequest) -> CurationDossier:
        trace: List[Step] = []
        goal = ("Curate a Cell Ontology entry for '%s' (%s); markers: %s; location: %s"
                % (request.name, request.description or "no description",
                   ", ".join(request.markers) or "none", request.location_hint or "none"))
        if self.verbose:
            print("\nGOAL: %s\n" % goal, flush=True)

        # 0. tool retrieval
        selected = self.registry.select(goal, k=6)
        self._log(trace, "retrieval", "selected tools",
                  summary=", ".join(t.spec.name for t in selected), goal=goal)

        # 0b. plan (LLM if available, else default order)
        default_plan = ["ols_search", "literature_search", "marker_panel",
                        "draft_definition"]
        plan = None
        if self.llm.available:
            plan = self.llm.plan_tools(goal, [t.spec.name for t in selected])
        llm_used = ("%s:%s" % (self.llm.provider, self.llm.model)) if self.llm.available else "none (deterministic)"
        self._log(trace, "planner", "planned steps",
                  summary=" -> ".join(plan or default_plan)
                  + (" (LLM)" if plan else " (default)"))

        # 1. existing-term check
        existing_hits = self.ols(request.name, ontology="cl", rows=5, offline=self.offline)
        existing = existing_hits[0] if existing_hits else None
        self._log(trace, "ols_search", "existing-term check in CL",
                  summary=("nearest: %s (%s) %.2f" % (existing.label, existing.curie, existing.score)
                           if existing else "no CL match"),
                  prov="EBI OLS4", query=request.name)

        # 2. parent (genus) grounding, with one self-correction
        parent_query = request.parent_hint or _derive_parent(request.name + " " + request.description)
        parent = self._ground(parent_query, "cl")
        if not (parent and parent.curie.startswith("CL:")):
            alt = _derive_parent(request.description or request.name)
            if alt != parent_query:
                self._log(trace, "self-correct", "parent ungrounded; re-deriving genus",
                          summary="'%s' -> '%s'" % (parent_query, alt))
                parent = self._ground(alt, "cl")
                parent_query = alt
        self._log(trace, "ols_search", "ground parent/genus in CL",
                  summary=("%s (%s) %.2f" % (parent.label, parent.curie, parent.score)
                           if parent else "UNGROUNDED"),
                  prov="EBI OLS4", query=parent_query)

        # 3. location grounding (Uberon)
        location = None
        if request.location_hint:
            location = self._ground(request.location_hint, "uberon")
            self._log(trace, "ols_search", "ground location in Uberon",
                      summary=("%s (%s) %.2f" % (location.label, location.curie, location.score)
                               if location else "UNGROUNDED"),
                      prov="EBI OLS4", query=request.location_hint)

        # 4. literature
        papers = self.lit(request.name, request.markers, organism=request.organism,
                          rows=5, offline=self.offline)
        self._log(trace, "literature_search", "Europe PMC evidence",
                  summary="%d papers" % len(papers), prov="Europe PMC",
                  query=request.name)

        # 5. marker panel
        if request.expr_csv:
            panel = self.mark.from_matrix(
                request.expr_csv, request.cluster_col, request.target_cluster,
                candidate_genes=request.markers or None)
        else:
            co = sum(1 for m in request.markers
                     if any(m.lower() in (p.title + " " + p.snippet).lower() for p in papers))
            panel = self.mark.from_prior(request.markers, literature_hits=len(papers),
                                         grounded=co)
        self._log(trace, "marker_panel", "test marker specificity",
                  summary="panel=[%s] score=%.2f (%s)"
                  % (", ".join(panel.markers), panel.score, panel.method))

        # 6. draft definition (+ optional LLM prose polish)
        definition = self.drafter(request.name, parent, location, panel,
                                  organism=request.organism)
        if self.llm.available:
            ctx = "parent=%s; location=%s; markers=%s" % (
                parent.label if parent else "cell",
                location.label if location else "n/a",
                ", ".join(panel.markers))
            polished = self.llm.polish_definition(definition.textual, ctx)
            if polished:
                definition.textual = polished
                definition.drafted_by = "llm:%s (grounded)" % self.llm.model
        self._log(trace, "draft_definition", "compose text + OWL + ROBOT",
                  summary=definition.textual)

        # 7. critique
        crit = critique(request.name, existing, parent, location, panel, papers)
        self._log(trace, "critic", "verification & confidence",
                  summary="confidence=%.2f needs_review=%s"
                  % (crit.confidence, crit.needs_expert_review))

        return CurationDossier(
            request=request, existing=existing, parent=parent, location=location,
            panel=panel, papers=papers, definition=definition, critique=crit,
            trace=trace, llm_used=llm_used)

    def _ground(self, query: str, ontology: str) -> Optional[TermMatch]:
        hits = self.ols(query, ontology=ontology, rows=5, offline=self.offline)
        return hits[0] if hits else None
