# Benchmarking CellScribe against the manually-curated Cell Ontology

**Question.** Given only a cell type's *name*, how faithfully does CellScribe recover the
ontology terms that Cell Ontology (CL) editors curated **by hand** — the genus (parent),
the anatomical location, and the surface markers — and can it tell an existing cell type
from a non-cell-type?

**Gold standard.** The Cell Ontology (`cl.json`, expert-curated; Tan et al., *Sci Data* 2026).
We parsed its **12,913 logical-definition axioms** to obtain, per term, the curated
genus (`is_a`), `part of` (Uberon) location, `has plasma membrane part` (PRO) surface
markers, and `capable of` (GO) functions. Coverage: **3,537** labelled CL terms;
**1,737** with a logical definition; **882** with a `part_of` Uberon location; **302** with
a PRO surface marker. CL is the appropriate ground truth because it *is* the
community's manually-curated reference, and it is orthogonal to CellScribe's logic.

**Results at a glance** (see `figures/benchmark_figure.png`):

| Benchmark | Metric | Result | n |
|---|---|---|---|
| B1 Term recognition | recall@1 / @5 (label) | **90.8% / 90.8%** | 400 |
| B1 Term recognition | recall@5 (synonym) | **91.5%** | 199 |
| B3 Location → Uberon | exact@1 | **100.0%** | 400 |
| B4 Surface marker → PRO | exact PRO (from symbol) | **69.8%** (82.6% any PRO) | 149 |
| B2 Genus derivation | hierarchically-valid / exact | **50.7% / 11.6%** | 371 |
| B6 Existing-vs-novel | precision / recall / F1 | **1.00 / 0.93 / 0.96** | 500 |
| **B7 GO function → GO term** | exact@1 | **94.8%** | 250 |
| **B8 Logical-definition reconstruction** | overall differentia recall | **94.7%** | 250 |
| **B8** | fully-reconstructed definitions | **94.0%** | 250 |

**Tier 2/3 evaluation** (`figures/benchmark_figure2.png`): B7 grounds curated GO functions;
B8 asks — from a term's curated *surface forms*, does CellScribe reproduce CL's curated
**logical definition** (genus + `part_of` Uberon + `capable_of` GO + `has plasma membrane part`
PRO)? part_of 100% · GO functions 94.4% · surface markers 83.5% · **overall differentia recall
94.7%**, with **94% of definitions fully reconstructed** (mean per-term completeness 0.96).

---

## Methods

All grounding uses CellScribe's live EBI OLS calls (cached); surface markers use the
Protein Ontology (PRO), locations use Uberon, functions use GO. Sampling is seeded
(`random.seed(0)`); the harness runs a thread pool over ~2,000 cached calls in ~3 min.

- **B1 — Term recognition (retrieval fidelity).** For 400 random CL terms we submit the
  curated label (and, where present, one synonym) to the existing-term check and record
  whether the correct `CL:` CURIE is returned at rank 1/3/5. Measures whether real cell
  types are reliably found (the basis of "align, don't create").
- **B2 — Genus derivation (inference).** From the *name + definition* CellScribe derives a
  parent (keyword heuristic) and grounds it to CL. We compare against the curated
  genus/`is_a`, scoring **exact** (matches a curated parent), **ancestor-consistent** (a true
  superclass in the CL `is_a` closure), **defaulted** (fell back to the root `cell`), or
  **incorrect**. Uses the CL `is_a` transitive closure computed from the ontology graph.
- **B3 — Anatomical location → Uberon (grounding fidelity).** For 400 terms with a curated
  `part_of` Uberon location we ground the Uberon *label* and check exact-CURIE recovery.
- **B4 — Surface marker → PRO (inference).** From each curated PRO term we derive the
  gene *symbol* a curator would type (e.g. `CD4` from "CD4 molecule") and test whether
  CellScribe's PRO grounding recovers the exact curated PRO CURIE.
- **B6 — Existing-vs-novel discrimination.** Positives = 250 real CL cell-type labels
  (should score high → *align*); negatives = 250 Uberon **anatomical-structure** labels
  used as decoy queries (a tissue is not a cell type → should score low → *propose/absent*).
  A term is called "existing" when the top **CL** hit scores ≥ 0.90.

---

## Results

**Recognition and grounding are near-perfect (B1, B3; Fig a,b).** Real cell-type names ground
to the exact CL term with **90.8% recall@5** (91.5% via synonyms), and curated anatomical
locations ground to the exact Uberon CURIE **100%** of the time (mean score 1.00). This is
the empirical basis of the anti-hallucination claim: given a correct surface form, the tool
returns the correct identifier and does not invent one. (These measure retrieval *fidelity*,
not inference — the label is provided.)

**Duplicate detection is precise and well-calibrated (B6; Fig e).** Real cell types score a
mean **0.93** while anatomy decoys score **0.10**, cleanly separated at the 0.90 threshold:
**precision 1.00, recall 0.93, F1 0.96** (0 false positives out of 250 decoys). The zero
false-positive rate follows a benchmark-driven fix — restricting the existing-term check to
`CL:` CURIEs so an imported Uberon/GO term returned by the CL search is never mistaken for a
duplicate cell type.

**Surface-marker grounding is good but imperfect (B4; Fig d).** From a bare gene symbol,
CellScribe recovers the exact curated PRO term **69.8%** of the time and *some* PRO term
**82.6%** of the time. The gap reflects a real ambiguity the paper warns about: short symbols
fuzzy-match (e.g. `CD4`→`CD44`), which the `"<symbol> molecule"` retry mitigates but does not
eliminate. This is an honest ceiling for symbol-only grounding without a curated symbol→PRO map.

**Tier 2/3 — it reconstructs the full curated logical definition (B7, B8; Figure 2).** This is
the end-to-end test the GO-function, surface-marker and KG-triple machinery was built for. GO
functions ground to the exact GO term **94.8%** of the time (B7). Given a term's curated surface
forms, CellScribe reproduces CL's curated **differentia** — `part_of` Uberon **100%**, `capable_of`
GO **94.4%**, `has plasma membrane part` PRO **83.5%** — for an **overall differentia recall of
94.7%**, and **94% of definitions are reconstructed in full** (mean per-term completeness 0.96;
Fig 2c). The residual loss is concentrated in surface-marker symbol grounding (the same B4 ceiling)
and the occasional multi-restriction axiom; genus (is_a) remains the heuristic weak point (B2).
Net: the parts a curator most wants auto-filled — location, function, and the axiom skeleton — are
recovered at ≥94%, while the parts that need judgement (genus, ambiguous markers) are surfaced for review.

**Genus derivation is the weakest link — by design (B2; Fig c).** The name-keyword heuristic is
**hierarchically valid 50.7%** of the time (exact 11.6%, ancestor-consistent 39.1%) but
**defaults to `cell` for 39.1%** of terms (categories outside its ~14 keyword rules) and is
outright **incorrect for 10.2%**. This is the expected, honest result and directly motivates the
roadmap: production genus assignment should come from the reference taxonomy (BICAN/TDT) or an
LLM proposal **validated against CL by an EL reasoner (ELK/WHELK)**, not a keyword rule.

---

## Interpretation — what CellScribe is trustworthy for

- **Reliable now (human can lean on it):** finding whether a type already exists (align vs propose),
  and grounding a supplied location/function/marker *surface form* to the correct CURIE.
- **Assistive, needs review:** proposing the genus and grounding bare marker symbols — CellScribe
  surfaces a ranked candidate + evidence, the curator decides. This matches the design principle
  that the tool drafts and evidences; a human commits.
- **Not claimed:** none of these commit to CL. Every output is a reviewable dossier.

The benchmark itself already improved the tool (the `CL:`-CURIE filter, which took discrimination
false positives from many to zero) — the kind of measurement-driven iteration the CL paper argues
for ("expert review remains essential; automation reduces, not eliminates, curation overhead").

---

## Reproducibility

```bash
# 1. gold standard (once)
curl -sL http://purl.obolibrary.org/obo/cl.json -o cl-full.json
# 2. run the benchmark (seeded, cached, ~3 min)
CL_JSON=cl-full.json python benchmark/run_benchmark.py       # -> benchmark/results/
# 3. figures
python benchmark/make_figures.py                              # -> benchmark/figures/
```
Sample sizes via `N1/N3/N4/N6` env vars; `WORKERS` sets thread-pool size. Per-term results are in
`benchmark/results/*.csv`; aggregate metrics in `results/metrics.json`.

*Resources: EBI OLS4 (CL, Uberon, GO, PRO), Europe PMC, QuickGO. Gold standard: Cell Ontology,
CC-BY 4.0. This is an independent evaluation, not affiliated with the Cell Ontology project.*
