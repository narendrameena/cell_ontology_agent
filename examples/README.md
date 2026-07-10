# CLARA examples

Every example runs **offline** using the shipped fixtures in
`../demo_data/fixtures/` — no network or API key needed. To run them against the
live EBI OLS / Europe PMC instead, unset `CLARA_OFFLINE` at the top of the script
(or `export CLARA_OFFLINE=0`).

## 1. Programmatic API — existing type → "align, don't create"
```bash
python examples/01_curate_api.py
```
Curates `CD4-positive, alpha-beta T cell`. Because it's already in CL, CLARA
returns disposition **ALIGN** (duplicate of `CL:0000624`) and prints the full
Markdown dossier. Shows the core API: `CurationRequest` → `agent.curate()` →
`dossier.to_markdown() / to_json() / to_robot_tsv() / to_owl() / save()`.

## 2. Marker matrix — novel type → grounded proposal
```bash
python examples/02_marker_matrix.py
```
Curates a novel `striatal parvalbumin-positive GABAergic interneuron` with an
expression matrix. CLARA grounds the genus (`interneuron`, CL:0000099) and
location (`striatum`, UBERON:0002435), runs the NS-Forest-style marker test
(panel score ~1.0), drafts an OWL axiom + ROBOT row, and saves the dossier to
`examples/out/`. Expected tail:

```
Disposition : PROPOSE new term for curator approval
Confidence  : 1.00
Genus       : interneuron (CL:0000099)
Location    : striatum (UBERON:0002435)
Marker panel: ['GAD2', 'PVALB', 'GAD1'] | score 1.00
```

## 3. Command line
```bash
# the two bundled examples, end to end:
python run_demo.py

# curate anything (add --expr matrix.csv --target CLUSTER to test markers on data):
python -m clara.cli curate --name "hepatic stellate cell" \
    --markers DCN,COL1A1 --location liver --out out/

# inspect the tool registry:
python -m clara.cli tools
```

## 4. Tests
```bash
python tests/test_clara.py     # self-running, offline -> "N passed"
# or: pytest -q
```
