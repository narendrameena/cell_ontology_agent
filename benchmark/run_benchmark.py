#!/usr/bin/env python3
"""Benchmark CellScribe against the manually-curated Cell Ontology (gold standard).

Gold standard: the Cell Ontology (Tan et al. 2026) — expert-curated logical
definitions (genus, `part of` Uberon location, `has plasma membrane part` PRO
markers, `capable of` GO functions). We ask: from a cell type's NAME alone, how
well does CellScribe recover the terms that CL editors curated by hand?

  B1  Term-recognition recall@k        (does grounding retrieve the right CL CURIE?)
  B2  Genus/parent derivation           (name -> parent vs curated is_a; exact/ancestor/default)
  B3  Anatomical location grounding     (Uberon label -> curated UBERON CURIE)
  B4  Surface-marker grounding to PRO   (gene symbol -> curated PR CURIE)
  B6  Existing-vs-novel discrimination  (real cell types vs anatomy decoys)

All OLS calls are cached and run through a thread pool. Outputs -> results/.
"""
import csv
import json
import os
import random
import sys
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["CELLSCRIBE_CACHE"] = os.path.join(HERE, ".bench_cache")

from cellscribe.agent import CuratorAgent, _derive_parent
from cellscribe.tools.ontology import OLSSearchTool

CL_JSON = os.environ.get("CL_JSON", os.path.join(ROOT, "cl-full.json"))
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)
random.seed(0)
WORKERS = int(os.environ.get("WORKERS", 12))
SHORT = lambda iri: iri.rsplit("/", 1)[-1].replace("_", ":")


def load_cl(path):
    g = json.load(open(path))["graphs"][0]
    label, syns, defn = {}, defaultdict(list), {}
    for n in g["nodes"]:
        cur = SHORT(n.get("id", ""))
        if n.get("lbl"):
            label[cur] = n["lbl"]
        meta = n.get("meta", {}) or {}
        for s in meta.get("synonyms", []) or []:
            if s.get("val"):
                syns[cur].append(s["val"])
        if (meta.get("definition") or {}).get("val"):
            defn[cur] = meta["definition"]["val"]
    parents = defaultdict(set)
    for e in g["edges"]:
        if e.get("pred") == "is_a":
            parents[SHORT(e["sub"])].add(SHORT(e["obj"]))
    ld = defaultdict(lambda: {"genus": set(), "part_of": set(), "hpmp": set(), "capable_of": set()})
    for a in g.get("logicalDefinitionAxioms", []):
        cur = SHORT(a["definedClassId"])
        if not cur.startswith("CL:"):
            continue
        for gid in a.get("genusIds", []):
            ld[cur]["genus"].add(SHORT(gid))
        for r in a.get("restrictions") or []:
            if not r:
                continue
            p = r.get("propertyId", ""); f = SHORT(r.get("fillerId", ""))
            if p.endswith("BFO_0000050") and f.startswith("UBERON:"):
                ld[cur]["part_of"].add(f)
            elif p.endswith("RO_0002104") and f.startswith("PR:"):
                ld[cur]["hpmp"].add(f)
            elif p.endswith("RO_0002215") and f.startswith("GO:"):
                ld[cur]["capable_of"].add(f)
    return label, dict(syns), defn, dict(parents), dict(ld)


def ancestors(curie, parents):
    seen, q = set(), deque([curie])
    while q:
        for p in parents.get(q.popleft(), ()):
            if p not in seen:
                seen.add(p); q.append(p)
    return seen


def pmap(fn, items):
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        return [r for r in ex.map(fn, items) if r is not None]


print("loading gold standard ...", flush=True)
LABEL, SYN, DEFN, PARENTS, LD = load_cl(CL_JSON)
cl_terms = [c for c in LABEL if c.startswith("CL:")]
print("CL terms with label: %d | with logical def: %d" % (len(cl_terms), len(LD)), flush=True)

ols = OLSSearchTool()
agent = CuratorAgent(offline=False, use_llm=False, verbose=False)


def cl_hits(q):
    return [h for h in ols(q, ontology="cl", rows=5, offline=False) if h.curie.startswith("CL:")]


# ---------- per-item workers ----------
def b1_one(cur):
    curies = [h.curie for h in cl_hits(LABEL[cur])]
    scores = [h.score for h in cl_hits(LABEL[cur])] if False else None
    row = {"curie": cur, "label": LABEL[cur],
           "r1": int(bool(curies) and curies[0] == cur),
           "r3": int(cur in curies[:3]), "r5": int(cur in curies[:5])}
    s = SYN.get(cur, [])
    if s:
        sh = [h.curie for h in cl_hits(s[0])]
        row["syn"] = s[0]; row["syn_r5"] = int(cur in sh[:5])
    return row


def b2_one(cur):
    gold = {g for g in (LD.get(cur, {}).get("genus", set()) | PARENTS.get(cur, set())) if g.startswith("CL:")}
    if not gold:
        return None
    anc = ancestors(cur, PARENTS)
    pq = _derive_parent(LABEL[cur] + " " + DEFN.get(cur, ""))
    hits = cl_hits(pq)
    P = hits[0].curie if hits else None
    if pq == "cell":
        cat = "defaulted"
    elif P and P in gold:
        cat = "exact"
    elif P and P in anc:
        cat = "ancestor"
    else:
        cat = "miss"
    return {"curie": cur, "label": LABEL[cur], "derived": pq, "grounded": P,
            "gold": ";".join(sorted(gold)), "category": cat}


def b3_one(cur):
    golds = LD[cur]["part_of"]
    if not golds:
        return None
    gold = sorted(golds)[0]
    gl = LABEL.get(gold)
    if not gl:
        return None
    hits = ols(gl, ontology="uberon", rows=5, offline=False)
    curies = [h.curie for h in hits]
    return {"curie": cur, "loc_label": gl, "gold": gold,
            "top": curies[0] if curies else None,
            "exact1": int(bool(curies) and curies[0] == gold),
            "top5": int(gold in curies[:5]),
            "score": hits[0].score if hits else 0.0}


def _symbol(pr_label):
    lab = pr_label.replace(" molecule", "").replace(" (human)", "").replace(" (mouse)", "")
    tok = lab.split()
    return tok[0] if tok and tok[0].isupper() else (lab.split("/")[0].strip() if lab else lab)


def b4_one(pair):
    pr, prlabel = pair
    sym = _symbol(prlabel)
    got = agent._ground_surface(sym)
    return {"gold_pr": pr, "pr_label": prlabel, "symbol": sym,
            "grounded": got.curie if got else None,
            "exact": int(bool(got) and got.curie == pr),
            "any_pr": int(bool(got) and got.curie.startswith("PR:"))}


def b6_one(item):
    kind, query = item
    hits = cl_hits(query)
    return {"kind": kind, "query": query,
            "score": hits[0].score if hits else 0.0,
            "is_existing": int(bool(hits) and hits[0].score >= 0.90)}


# ---- Tier 2/3 benchmarks ----
def b7_one(cur):
    """GO-function grounding: curated `capable_of` GO label -> exact GO CURIE."""
    gos = LD[cur].get("capable_of", set())
    if not gos:
        return None
    gold = sorted(gos)[0]
    gl = LABEL.get(gold)
    if not gl:
        return None
    hits = ols(gl, ontology="go", rows=5, offline=False)
    curies = [h.curie for h in hits]
    return {"curie": cur, "go_label": gl, "gold": gold,
            "exact1": int(bool(curies) and curies[0] == gold),
            "top5": int(gold in curies[:5])}


def b8_one(cur):
    """Logical-definition reconstruction: from curated surface forms, does CellScribe
    reproduce CL's curated differentia (part_of Uberon / capable_of GO / hpmp PRO)?"""
    ld = LD.get(cur, {})
    gpo, ggo, gpr = ld.get("part_of", set()), ld.get("capable_of", set()), ld.get("hpmp", set())
    total = len(gpo) + len(ggo) + len(gpr)
    if total == 0:
        return None
    emit_po = set()
    if gpo:
        h = ols(LABEL.get(sorted(gpo)[0], ""), ontology="uberon", rows=5, offline=False)
        if h:
            emit_po.add(h[0].curie)
    emit_go = set()
    for g in ggo:
        h = ols(LABEL.get(g, ""), ontology="go", rows=5, offline=False)
        if h and h[0].curie.startswith("GO:"):
            emit_go.add(h[0].curie)
    emit_pr = set()
    for p in gpr:
        got = agent._ground_surface(_symbol(LABEL.get(p, "")))
        if got:
            emit_pr.add(got.curie)
    matched = len(gpo & emit_po) + len(ggo & emit_go) + len(gpr & emit_pr)
    return {"curie": cur, "partof_n": len(gpo), "partof_ok": len(gpo & emit_po),
            "go_n": len(ggo), "go_ok": len(ggo & emit_go),
            "pr_n": len(gpr), "pr_ok": len(gpr & emit_pr),
            "total": total, "matched": matched, "completeness": round(matched / total, 3)}


def dump(name, rows):
    if not rows:
        return
    with open(os.path.join(RESULTS, name + ".csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)


# ---------- run ----------
t0 = time.time()
with_def = sorted(LD.keys())
with_loc = [c for c in with_def if LD[c]["part_of"]]
with_pr = [c for c in with_def if LD[c]["hpmp"]]
uberon_labels = sorted({LABEL[c] for c in LABEL if c.startswith("UBERON:")})

sample1 = random.sample(cl_terms, min(int(os.environ.get("N1", 400)), len(cl_terms)))
print("B1 recognition + B2 genus (n=%d) ..." % len(sample1), flush=True)
r1 = pmap(b1_one, sample1); dump("b1_recognition", r1)
r2 = pmap(b2_one, sample1); dump("b2_genus", r2)

sample3 = random.sample(with_loc, min(int(os.environ.get("N3", 400)), len(with_loc)))
print("B3 location (n=%d) ..." % len(sample3), flush=True)
r3 = pmap(b3_one, sample3); dump("b3_location", r3)

pr_pairs = sorted({(pr, LABEL[pr]) for c in with_pr for pr in LD[c]["hpmp"] if pr in LABEL})
sample4 = random.sample(pr_pairs, min(int(os.environ.get("N4", 300)), len(pr_pairs)))
print("B4 surface->PRO (n=%d unique proteins) ..." % len(sample4), flush=True)
r4 = pmap(b4_one, sample4); dump("b4_surface", r4)

posN = min(int(os.environ.get("N6", 250)), len(cl_terms))
pos = [("cell_type", LABEL[c]) for c in random.sample(cl_terms, posN)]
neg = [("anatomy_decoy", l) for l in random.sample(uberon_labels, min(posN, len(uberon_labels)))]
print("B6 discrimination (pos=%d neg=%d) ..." % (len(pos), len(neg)), flush=True)
r6 = pmap(b6_one, pos + neg); dump("b6_discrimination", r6)

# ---- Tier 2/3 ----
with_go = [c for c in with_def if LD[c]["capable_of"]]
with_diff = [c for c in with_def if LD[c]["part_of"] or LD[c]["capable_of"] or LD[c]["hpmp"]]
sample7 = random.sample(with_go, min(int(os.environ.get("N7", 250)), len(with_go)))
print("B7 GO-function grounding (n=%d) ..." % len(sample7), flush=True)
r7 = pmap(b7_one, sample7); dump("b7_go_function", r7)
sample8 = random.sample(with_diff, min(int(os.environ.get("N8", 250)), len(with_diff)))
print("B8 logical-definition reconstruction (n=%d) ..." % len(sample8), flush=True)
r8 = pmap(b8_one, sample8); dump("b8_reconstruction", r8)


def rate(rows, key):
    v = [r[key] for r in rows if key in r]
    return round(sum(v) / len(v), 4) if v else 0.0


syn_rows = [r for r in r1 if "syn_r5" in r]
gc = defaultdict(int)
for r in r2:
    gc[r["category"]] += 1
tp = sum(1 for r in r6 if r["kind"] == "cell_type" and r["is_existing"])
fn = sum(1 for r in r6 if r["kind"] == "cell_type" and not r["is_existing"])
fp = sum(1 for r in r6 if r["kind"] == "anatomy_decoy" and r["is_existing"])
tn = sum(1 for r in r6 if r["kind"] == "anatomy_decoy" and not r["is_existing"])
prec = tp / (tp + fp) if (tp + fp) else 0.0
rec = tp / (tp + fn) if (tp + fn) else 0.0
f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
ct = [r["score"] for r in r6 if r["kind"] == "cell_type"]
dc = [r["score"] for r in r6 if r["kind"] == "anatomy_decoy"]

metrics = {
    "gold_standard": {"source": "Cell Ontology cl.json (expert-curated)",
                      "cl_terms_with_label": len(cl_terms), "cl_terms_with_logical_def": len(LD),
                      "with_part_of_uberon": len(with_loc), "with_hpmp_pro": len(with_pr)},
    "B1_recognition": {"n": len(r1), "recall@1": rate(r1, "r1"), "recall@3": rate(r1, "r3"),
                       "recall@5": rate(r1, "r5"), "synonym_recall@5": rate(syn_rows, "syn_r5"),
                       "synonym_n": len(syn_rows)},
    "B2_genus": {"n": len(r2), **{k: gc[k] for k in ("exact", "ancestor", "defaulted", "miss")},
                 "exact_rate": round(gc["exact"] / len(r2), 4) if r2 else 0,
                 "hierarchically_valid_rate": round((gc["exact"] + gc["ancestor"]) / len(r2), 4) if r2 else 0},
    "B3_location": {"n": len(r3), "exact@1": rate(r3, "exact1"), "recall@5": rate(r3, "top5"),
                    "mean_top_score": round(sum(r["score"] for r in r3) / len(r3), 4) if r3 else 0},
    "B4_surface": {"n": len(r4), "exact_PR": rate(r4, "exact"), "any_PR": rate(r4, "any_pr")},
    "B6_discrimination": {"n": len(r6), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                          "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
                          "mean_score_cell_type": round(sum(ct) / len(ct), 4) if ct else 0,
                          "mean_score_decoy": round(sum(dc) / len(dc), 4) if dc else 0},
    "B7_go_function": {"n": len(r7), "exact@1": rate(r7, "exact1"), "recall@5": rate(r7, "top5")},
    "B8_reconstruction": {
        "n": len(r8),
        "part_of_exact": round(sum(r["partof_ok"] for r in r8) / max(1, sum(r["partof_n"] for r in r8)), 4),
        "go_function_recall": round(sum(r["go_ok"] for r in r8) / max(1, sum(r["go_n"] for r in r8)), 4),
        "surface_marker_recall": round(sum(r["pr_ok"] for r in r8) / max(1, sum(r["pr_n"] for r in r8)), 4),
        "overall_restriction_recall": round(sum(r["matched"] for r in r8) / max(1, sum(r["total"] for r in r8)), 4),
        "mean_completeness": round(sum(r["completeness"] for r in r8) / len(r8), 4) if r8 else 0,
        "fully_reconstructed_frac": round(sum(1 for r in r8 if r["completeness"] >= 0.999) / len(r8), 4) if r8 else 0},
    "runtime_sec": round(time.time() - t0, 1),
}
json.dump(metrics, open(os.path.join(RESULTS, "metrics.json"), "w"), indent=2)
print("\n=== METRICS ===")
print(json.dumps(metrics, indent=2))
