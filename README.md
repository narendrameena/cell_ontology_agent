# CLARA — a grounded, agentic assistant for Cell Ontology curation

*Cell-ontology Literature-And-marker Reasoning Agent · prototype for the
Computational Biologist – Cell Ontology & Agentic AI role (JR103686).*

CLARA takes a cell type (a name, optionally a description, marker genes and an
expression matrix) and returns a **curation dossier**: grounded ontology terms,
a tested marker panel, cited literature, a *computable* draft definition
(OWL + ROBOT), and the agent's own critique + recommended disposition —
so a curator reviews **evidence and doubts, not an unverified answer**.

It is inspired by Stanford's **Biomni** (a general-purpose biomedical agent =
an *environment* of tool schemas + an *agent* that retrieves, plans, executes
and self-critiques), narrowed to the Cell Ontology curation loop and wired to
the same public resources the Cellular Semantics team's stack builds on.

> Design bet (from evaluating frontier models): **LLMs are strong drafters but
> weak authorities.** So every claim is grounded in a real CURIE (EBI OLS) and a
> real paper (Europe PMC), markers are tested on data, and nothing is committed
> without a human. The LLM is optional and may only *plan* and *polish* — never
> invent an ontology term.

---

## What it actually does (verified, live)

```
$ python -m clara.cli curate --name "striatal parvalbumin-positive GABAergic interneuron" \
      --description "A GABAergic interneuron of the striatum expressing parvalbumin" \
      --markers GAD1,GAD2,PVALB --location striatum \
      --expr demo_data/striatum_demo_expr.csv --target striatal_PV_interneuron --out out/

  [1] retrieval        selected tools — literature_search, marker_panel, ols_search, draft_definition
  [2] planner          planned steps — ols_search -> literature_search -> marker_panel -> draft_definition
  [3] ols_search       existing-term check in CL — no CL match
  [4] ols_search       ground parent/genus in CL — interneuron (CL:0000099) 1.00
  [5] ols_search       ground location in Uberon — striatum (UBERON:0002435) 1.00
  [6] literature_search Europe PMC evidence — 5 papers
  [7] marker_panel     test marker specificity — panel=[GAD2, PVALB, GAD1] score=1.00 (NS-Forest-style)
  [8] draft_definition compose text + OWL + ROBOT — An interneuron located in the striatum expressing ...
  [9] critic           verification & confidence — confidence=1.00

Verdict : PROPOSE new term for curator approval   (curator makes the final call)
```

The dossier is written as **JSON + Markdown + a ROBOT template (`.robot.tsv`) +
an OWL/Manchester snippet (`.omn`)**. Example computable draft:

```
Class: CL:NEW_0000001   # "striatal parvalbumin-positive GABAergic interneuron"
  EquivalentTo:
    'interneuron'
      and ('part of' some 'striatum')
      and ('expresses' some GAD2)
      and ('expresses' some PVALB)
      and ('expresses' some GAD1)
```

Two behaviours worth seeing in the demo:
* **Existing type → “ALIGN, don’t create.”** `CD4-positive, alpha-beta T cell`
  is recognised as `CL:0000624` and flagged as a duplicate.
* **Novel type → grounded proposal.** the striatal interneuron above is drafted
  with a data-tested marker panel and routed for curator approval.

---

## Architecture (Biomni-inspired)

```
                    ┌──────────────────────── CuratorAgent (A1-style) ───────────────────────┐
   CurationRequest  │  retrieve tools ▸ plan ▸ execute (grounded) ▸ self-correct ▸ critique   │  CurationDossier
  (name, markers,   │        │            │          │                    │          │        │  (JSON / Markdown /
   matrix, ...)  ───►        ▼            ▼          ▼                    ▼          ▼        ├──►  ROBOT / OWL +
                    │   registry     LLM plan   tool calls          re-derive    confidence  │     full trace)
                    │   .select()   (optional)  (below)             genus once   + disposition│
                    └────────────────────────────────┬───────────────────────────────────────┘
                                                      ▼
   Tool registry (Biomni-E1-style declarative schemas):
     • ols_search        EBI OLS4      → ground CL / Uberon / GO / PR terms  (anti-hallucination)
     • literature_search Europe PMC    → papers + extracted evidence sentence (RAG)
     • marker_panel      numpy/pandas  → NS-Forest-style minimal, specific panel + F-beta score
     • draft_definition  templating    → genus–differentia text + OWL axiom + ROBOT row
     • critic            rules         → grounding/duplication/support checks → confidence + flags
```

| Biomni | CLARA |
|---|---|
| Biomni-E1 environment (150 tools / 59 DBs) | `registry.py` — tool schemas over OLS, Europe PMC, NS-Forest-style analysis |
| Biomni-A1 retrieval → plan → code → self-critique | `agent.py` — `select()` → `plan_tools()` → grounded execution → `critic` |
| Declarative tool schemas | `ToolSpec` on every tool |
| Grounding to curb hallucination | every term is a real CURIE; LLM never invents terms |

---

## Install & run

```bash
pip install -r requirements.txt          # requests (+ pandas/numpy for the marker test)
# or: pip install -e .                    # gives a `clara` command

python run_demo.py                        # OFFLINE by default (uses shipped fixtures)
python run_demo.py --online               # refresh from EBI OLS / Europe PMC
python -m clara.cli tools                 # list the tool registry
python -m clara.cli curate --name "..." --markers GENE1,GENE2 --location "..." --out out/
```

Optional LLM planner/polisher (never invents terms; grounded output only):

```bash
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY=...
export CLARA_MODEL=claude-sonnet-5   # optional
python -m clara.cli curate --name "..." --markers ...      # (omit --no-llm)
```

**Offline / air-gapped:** `CLARA_OFFLINE=1` forces cache-only using the shipped
`demo_data/fixtures/` — the demo runs with no network (useful in an interview room).

---

## Design principles (why it's built this way)

1. **Grounding over generation** — terms come from OLS, evidence from Europe PMC; the LLM plans/polishes only.
2. **Evidence & provenance are first-class** — the output is a dossier (markers, papers, CURIEs, confidence), not an answer.
3. **Human-in-the-loop** — CLARA never writes to CL; it proposes a *disposition* (ALIGN / PROPOSE_NEW / INSUFFICIENT) for a curator.
4. **Test, don't assert** — marker specificity is measured on data (NS-Forest-style), not claimed.
5. **Auditable** — every run emits a step-by-step trace.

## How it maps to the role (JR103686)

* *Extend CL from HCA/BICAN atlases* → the novel-type path (ground genus + location, test markers, draft OWL, route for approval).
* *Build agentic Python workflows* → the retrieve→plan→execute→critique loop over a tool registry.
* *Open-source Python packages* → clean, typed, dependency-light package + CLI + tests-ready structure.
* *Knowledge graphs* → grounded CURIEs + relations (`part of`, `expresses`) are graph edges by construction.

## Honest limitations & roadmap

* Parent/genus derivation is a heuristic + OLS grounding; **production** should take the parent from the reference taxonomy (BICAN/Taxonomy Development Tools) or an LLM proposal *validated against CL by a reasoner (ELK)*.
* The marker test is a faithful NS-Forest *re-implementation*; swap in the real `nsforest` package and Scanpy/AnnData for scale.
* Evidence extraction is sentence-level keyword matching; upgrade to SPIRES/OntoGPT-style schema-constrained extraction.
* Next: ELK reasoning to auto-classify drafts; ROBOT-template round-trip into an ODK repo; batch mode over a whole atlas with a gold-standard **precision/recall + curator edit-distance** evaluation; integrate with DRAGON-AI / Aurelian rather than duplicate them.

*Prototype by Narendra Meena. Public data: EBI OLS4, Europe PMC. Not affiliated with the Cell Ontology project.*
