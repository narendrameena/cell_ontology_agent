# CLARA — a grounded, agentic assistant for Cell Ontology curation

*Cell-ontology Literature-And-marker Reasoning Agent.*

CLARA takes a cell type (a name, optionally a description, marker genes and an
expression matrix) and returns a **curation dossier**: grounded ontology terms,
a tested marker panel, cited literature, a *computable* draft definition
(OWL + ROBOT), and the agent's own critique + recommended disposition —
so a curator reviews **evidence and doubts, not an unverified answer**.

It is inspired by Stanford's **Biomni** (a general-purpose biomedical agent =
an *environment* of tool schemas + an *agent* that retrieves, plans, executes
and self-critiques), narrowed to the Cell Ontology curation loop and wired to
public resources (EBI OLS, Europe PMC).

> **Design bet:** LLMs are strong drafters but weak authorities. So every claim
> is grounded in a real CURIE (EBI OLS) and a real paper (Europe PMC), markers
> are tested on data, and nothing is committed without a human. The LLM is
> optional and may only *plan* and *polish* — never invent an ontology term.

---

## Quickstart

```bash
pip install -r requirements.txt          # requests (+ pandas/numpy for the marker test)
# or: pip install -e .                    # gives a `clara` command

python run_demo.py                        # OFFLINE by default (uses shipped fixtures)
python run_demo.py --online               # refresh from EBI OLS / Europe PMC
python -m clara.cli tools                 # list the tool registry
python -m clara.cli curate --name "..." --markers GENE1,GENE2 --location "..." --out out/
```

See **[`examples/`](examples/)** for runnable scripts and **[Tests](#tests)** below.

---

## What it does (verified, live)

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

Verdict : PROPOSE new term for curator approval   (a human makes the final call)
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
  with a data-tested marker panel and routed for approval.

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
   Tool registry (declarative schemas):
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
| Grounding to curb hallucination | every term is a real CURIE; the LLM never invents terms |

---

## Optional LLM (planner / polisher)

CLARA is *useful without an LLM*. With a key it adds two judgement tasks —
ordering tools and polishing prose — but never invents ontology terms.

```bash
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY=...
export CLARA_MODEL=claude-sonnet-5   # optional
python -m clara.cli curate --name "..." --markers ...      # (omit --no-llm)
```

**Offline / air-gapped:** `CLARA_OFFLINE=1` forces cache-only using the shipped
`demo_data/fixtures/`, so the demo and tests run with no network.

---

## Examples

Runnable, offline (they use the shipped fixtures):

```bash
python examples/01_curate_api.py       # programmatic API: request -> dossier
python examples/02_marker_matrix.py    # NS-Forest-style marker test on a matrix
```

See **[`examples/README.md`](examples/README.md)** for a walk-through.

## Tests

No pytest required — the suite self-runs and is also pytest-compatible:

```bash
python tests/test_clara.py     # -> "N passed" (offline, deterministic)
# or, if you have pytest:
pytest -q
```

The tests cover ontology grounding, the marker panel, definition drafting, the
critic's disposition logic, the query cascade, and the parent word-boundary fix,
plus two end-to-end agent runs (align-existing and propose-new) — all offline.

---

## Design principles

1. **Grounding over generation** — terms from OLS, evidence from Europe PMC; the LLM plans/polishes only.
2. **Evidence & provenance are first-class** — the output is a dossier (markers, papers, CURIEs, confidence), not an answer.
3. **Human-in-the-loop** — CLARA never writes to CL; it proposes a *disposition* (ALIGN / PROPOSE_NEW / INSUFFICIENT).
4. **Test, don't assert** — marker specificity is measured on data (NS-Forest-style), not claimed.
5. **Auditable** — every run emits a step-by-step trace.

## Use cases

* Extending CL with new types from single-cell / spatial atlas taxonomies (ground genus + location, test markers, draft OWL, route for approval).
* Triaging cluster annotations: is this type already in CL, or genuinely new?
* Seeding knowledge-graph edges — grounded CURIEs + relations (`part of`, `expresses`) are graph edges by construction.
* A teaching example of a grounded, verifiable agentic workflow.

## Honest limitations & roadmap

* Parent/genus derivation is a heuristic + OLS grounding; production should take the parent from a reference taxonomy or an LLM proposal *validated against CL by a reasoner (ELK)*.
* The marker test is a faithful NS-Forest *re-implementation*; swap in the real `nsforest` package and Scanpy/AnnData for scale.
* Evidence extraction is sentence-level keyword matching; upgrade to SPIRES/OntoGPT-style schema-constrained extraction.
* Next: ELK reasoning to auto-classify drafts; ROBOT-template round-trip into an ODK repo; batch mode over a whole atlas with a gold-standard **precision/recall + curator edit-distance** evaluation; integrate with ecosystem tools (OntoGPT, DRAGON-AI, Aurelian) rather than duplicate them.

---

*Built by Narendra Meena. Public data: EBI OLS4, Europe PMC. MIT-licensed. Not affiliated with the Cell Ontology / OBO Foundry projects.*
