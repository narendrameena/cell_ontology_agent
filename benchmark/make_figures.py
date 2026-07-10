#!/usr/bin/env python3
"""Publication-quality figures for the CellScribe benchmark (reads results/)."""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

# ---- Nature-ish style ----
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 10, "axes.titleweight": "bold", "xtick.labelsize": 8,
    "ytick.labelsize": 8, "legend.fontsize": 7.5, "figure.dpi": 150,
})
TEAL, NAVY, AMBER, CORAL, GREEN, GREY = "#1B9AAA", "#0F2E44", "#E8883A", "#D95D4E", "#2E9B76", "#9AA7B0"


def load_csv(name):
    p = os.path.join(RES, name + ".csv")
    if not os.path.exists(p):
        return []
    with open(p) as fh:
        return list(csv.DictReader(fh))


M = json.load(open(os.path.join(RES, "metrics.json")))


def letter(ax, s):
    ax.text(-0.14, 1.06, s, transform=ax.transAxes, fontsize=13, fontweight="bold", va="top")


def barlabels(ax, bars, fmt="%.2f", dy=0.01):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, fmt % b.get_height(),
                ha="center", va="bottom", fontsize=7.5)


fig, axes = plt.subplots(2, 3, figsize=(12.5, 7.4))
fig.suptitle("CellScribe recovers expert-curated Cell Ontology definitions from cell-type names",
             fontsize=12, fontweight="bold", y=0.99)

# ---- Panel a: B1 recognition recall ----
ax = axes[0, 0]
b1 = M["B1_recognition"]
vals = [b1["recall@1"], b1["recall@3"], b1["recall@5"], b1["synonym_recall@5"]]
labs = ["label\n@1", "label\n@3", "label\n@5", "synonym\n@5"]
cols = [TEAL, TEAL, TEAL, AMBER]
bars = ax.bar(labs, vals, color=cols, width=0.68)
barlabels(ax, bars)
ax.set_ylim(0, 1.08); ax.set_ylabel("recall")
ax.set_title("Term recognition (n=%d)" % b1["n"])
letter(ax, "a")

# ---- Panel b: B3 location grounding ----
ax = axes[0, 1]
b3 = M["B3_location"]
bars = ax.bar(["exact\n@1", "recall\n@5"], [b3["exact@1"], b3["recall@5"]],
              color=[TEAL, NAVY], width=0.6)
barlabels(ax, bars)
ax.set_ylim(0, 1.08); ax.set_ylabel("accuracy")
ax.set_title("Anatomical location → Uberon (n=%d)" % b3["n"])
letter(ax, "b")

# ---- Panel c: B2 genus derivation (stacked proportions) ----
ax = axes[0, 2]
b2 = M["B2_genus"]
n = max(1, b2["n"])
parts = [("exact", b2["exact"], GREEN), ("ancestor-consistent", b2["ancestor"], TEAL),
         ("defaulted to 'cell'", b2["defaulted"], GREY), ("incorrect", b2["miss"], CORAL)]
bottom = 0
for name, cnt, col in parts:
    frac = cnt / n
    ax.bar(0, frac, bottom=bottom, color=col, width=0.5)
    if frac > 0.04:
        ax.text(0, bottom + frac / 2, "%.0f%%" % (100 * frac), ha="center", va="center",
                fontsize=8, color="white", fontweight="bold")
    bottom += frac
ax.set_xlim(-0.6, 1.9); ax.set_xticks([]); ax.set_ylim(0, 1.0); ax.set_ylabel("fraction of terms")
ax.set_title("Genus derivation vs curated is_a (n=%d)" % b2["n"])
ax.legend(handles=[Patch(color=c, label=l) for l, _, c in parts], loc="center right",
          frameon=False, bbox_to_anchor=(1.98, 0.5))
letter(ax, "c")

# ---- Panel d: B4 surface marker -> PRO ----
ax = axes[1, 0]
b4 = M["B4_surface"]
bars = ax.bar(["exact\nPRO term", "any\nPRO term"], [b4["exact_PR"], b4["any_PR"]],
              color=[TEAL, GREY], width=0.6)
barlabels(ax, bars)
ax.set_ylim(0, 1.08); ax.set_ylabel("grounding rate")
ax.set_title("Surface marker (symbol) → PRO (n=%d)" % b4["n"])
letter(ax, "d")

# ---- Panel e: B6 score separation ----
ax = axes[1, 1]
b6 = load_csv("b6_discrimination")
ct = [float(r["score"]) for r in b6 if r["kind"] == "cell_type"]
dc = [float(r["score"]) for r in b6 if r["kind"] == "anatomy_decoy"]
bins = [i / 20 for i in range(21)]
ax.hist(ct, bins=bins, color=TEAL, alpha=0.8, label="cell types (real)")
ax.hist(dc, bins=bins, color=CORAL, alpha=0.7, label="anatomy decoys")
ax.axvline(0.90, color=NAVY, ls="--", lw=1)
ax.text(0.90, ax.get_ylim()[1] * 0.92, " threshold 0.90", fontsize=7, color=NAVY)
ax.set_xlabel("top CL match score"); ax.set_ylabel("count")
ax.set_title("Existing vs novel discrimination")
ax.legend(frameon=False, loc="upper left")
mb6 = M["B6_discrimination"]
ax.text(0.02, 0.60, "P=%.2f  R=%.2f  F1=%.2f" % (mb6["precision"], mb6["recall"], mb6["f1"]),
        transform=ax.transAxes, fontsize=8)
letter(ax, "e")

# ---- Panel f: summary table ----
ax = axes[1, 2]
ax.axis("off")
gs = M["gold_standard"]
rows = [
    ["Gold standard", "Cell Ontology"],
    ["CL terms (labelled)", "%d" % gs["cl_terms_with_label"]],
    ["  logical definition", "%d" % gs["cl_terms_with_logical_def"]],
    ["  part_of Uberon", "%d" % gs["with_part_of_uberon"]],
    ["  surface PRO marker", "%d" % gs["with_hpmp_pro"]],
    ["Recognition recall@5", "%.1f%%" % (100 * M["B1_recognition"]["recall@5"])],
    ["Location exact@1", "%.1f%%" % (100 * M["B3_location"]["exact@1"])],
    ["Genus hier.-valid", "%.1f%%" % (100 * M["B2_genus"]["hierarchically_valid_rate"])],
    ["Discrimination F1", "%.2f" % M["B6_discrimination"]["f1"]],
]
tbl = ax.table(cellText=rows, colWidths=[0.58, 0.42], loc="center", cellLoc="left")
tbl.auto_set_font_size(False); tbl.set_fontsize(8.2); tbl.scale(1, 1.35)
for (r, cc), cell in tbl.get_celld().items():
    cell.set_edgecolor("#DDDDDD")
    if cc == 1:
        cell.set_text_props(fontweight="bold", color=NAVY)
    if r in (0,):
        cell.set_text_props(fontweight="bold")
ax.set_title("Benchmark summary")
letter(ax, "f")

fig.tight_layout(rect=[0, 0, 1, 0.965])
fig.savefig(os.path.join(FIG, "benchmark_figure.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(FIG, "benchmark_figure.pdf"), bbox_inches="tight")
print("wrote", os.path.join(FIG, "benchmark_figure.png"))
