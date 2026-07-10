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
from .tools.go_support import QuickGOTool
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
        self.go = self.registry.register(QuickGOTool())
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

        # 1. existing-term check (only CL cell-type CURIEs count as a duplicate; an
        #    imported anatomy/GO term returned by the CL search is not a cell type)
        existing_hits = [h for h in self.ols(request.name, ontology="cl", rows=5,
                                             offline=self.offline)
                         if h.curie.startswith("CL:")]
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
            prior_markers = list(request.markers) + list(request.surface_markers)
            co = sum(1 for m in prior_markers
                     if any(m.lower() in (p.title + " " + p.snippet).lower() for p in papers))
            panel = self.mark.from_prior(prior_markers, literature_hits=len(papers),
                                         grounded=co)
        self._log(trace, "marker_panel", "test marker specificity",
                  summary="panel=[%s] score=%.2f (%s)"
                  % (", ".join(panel.markers), panel.score, panel.method))

        # 6. ground GO functions ('capable of') and surface-protein markers (PRO)
        functions = []
        for fq in request.functions:
            t = self._ground(fq, "go")
            if t and t.curie.startswith("GO:"):
                functions.append(t)
        if request.functions:
            self._log(trace, "ols_search", "ground functions in GO",
                      summary=(", ".join("%s (%s)" % (f.label, f.curie) for f in functions)
                               or "none grounded"), prov="EBI OLS4")
        surface, surface_ungrounded = [], []
        for sm in request.surface_markers:
            t = self._ground_surface(sm)
            if t:
                surface.append(t)
            else:
                surface_ungrounded.append(sm)
        if request.surface_markers:
            self._log(trace, "ols_search", "ground surface markers in PRO",
                      summary="grounded=[%s] unverified=[%s]"
                      % (", ".join("%s->%s" % (s.query, s.curie) for s in surface),
                         ", ".join(surface_ungrounded) or "-"), prov="EBI OLS4 (PRO)")

        # 6b. GO x marker intersection (QuickGO) — which markers a defining function supports
        all_markers = list(request.markers) + list(request.surface_markers)
        go_support = {}
        if functions and all_markers:
            go_support = self.go.support(all_markers, functions,
                                         organism=request.organism, offline=self.offline)
            self._log(trace, "go_marker_support", "GO x marker intersection (QuickGO)",
                      summary=(", ".join("%s<-%s" % (m, "/".join(g)) for m, g in go_support.items())
                               or "no marker supported by a defining GO function"),
                      prov="QuickGO (ECO:0000269/0000318)")

        # 7. draft definition (+ optional LLM CL-standard prose)
        definition = self.drafter(request.name, parent, location, panel,
                                  functions=functions, surface=surface,
                                  surface_ungrounded=surface_ungrounded,
                                  organism=request.organism)
        if self.llm.available:
            facts = ("genus=%s; location=%s; GO functions=%s; transcriptomic markers=%s (in %s); "
                     "surface markers=%s") % (
                parent.label if parent else "cell",
                location.label if location else "n/a",
                "; ".join(f.label for f in functions) or "n/a",
                ", ".join(panel.markers) or "n/a", request.organism,
                ", ".join([s.label for s in surface] + surface_ungrounded) or "n/a")
            refs = "; ".join("%s (PMID %s)" % (p.title, p.pmid) for p in papers[:5])
            drafted = self.llm.draft_cl_definition(parent.label if parent else "cell", facts, refs)
            if drafted:
                definition.textual = drafted
                definition.drafted_by = "llm:%s (grounded, CL house-style)" % self.llm.model
        self._log(trace, "draft_definition", "compose text + OWL + ROBOT",
                  summary=definition.textual)

        # 8. critique
        crit = critique(request.name, existing, parent, location, panel, papers)
        self._log(trace, "critic", "verification & confidence",
                  summary="confidence=%.2f needs_review=%s"
                  % (crit.confidence, crit.needs_expert_review))

        return CurationDossier(
            request=request, existing=existing, parent=parent, location=location,
            functions=functions, surface=surface, surface_ungrounded=surface_ungrounded,
            go_support=go_support, panel=panel, papers=papers, definition=definition,
            critique=crit, trace=trace, llm_used=llm_used)

    def _ground(self, query: str, ontology: str) -> Optional[TermMatch]:
        hits = self.ols(query, ontology=ontology, rows=5, offline=self.offline)
        return hits[0] if hits else None

    def _ground_surface(self, symbol: str):
        """Ground a surface-marker symbol to PRO. Bare symbols like 'CD4' fuzzy-match
        (e.g. CD44), so we try '<sym> molecule' first and require an exact/synonym hit."""
        sym = symbol.lower().strip()
        for q in (symbol + " molecule", symbol):
            for h in self.ols(q, ontology="pr", rows=8, offline=self.offline):
                lbl = h.label.lower().strip()
                syns = [s.lower() for s in h.synonyms]
                if lbl == sym or lbl == sym + " molecule" or sym in lbl.split() or sym in syns:
                    return h
        return None
