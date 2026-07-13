#!/usr/bin/env python3
"""Headline benchmark chart — CellScribe vs the Cell Ontology's own logical definitions.
   python3 figures/make_benchmark.py  ->  figures/benchmark.{png,pdf}
Reads benchmark/results/metrics.json (produced by benchmark/run_benchmark.py).
"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
M = json.load(open(os.path.join(ROOT, "benchmark", "results", "metrics.json")))

INK="#1b2733"; MUT="#5A6472"
BLUE="#2C6FA6"; TEAL="#2F9E8F"; GREEN="#4C8C4A"; AMBER="#C6791F"; PURPLE="#7E6BB5"; ROSE="#C25E7C"
plt.rcParams["font.family"] = "DejaVu Sans"

# (label, value, n, color) — pulled from the real metrics
WEAK = "#A0522D"   # muted sienna marks the honest weak spot
rows = [
    ("Location → Uberon\n(exact@1)",          M["B3_location"]["exact@1"],            M["B3_location"]["n"],       GREEN),
    ("Existing-vs-novel\ndiscrimination (F1)", M["B6_discrimination"]["f1"],           M["B6_discrimination"]["n"], BLUE),
    ("GO-function grounding\n(exact@1)",       M["B7_go_function"]["exact@1"],         M["B7_go_function"]["n"],    AMBER),
    ("Logical-def reconstruction\n(fully rebuilt)", M["B8_reconstruction"]["fully_reconstructed_frac"], M["B8_reconstruction"]["n"], PURPLE),
    ("Term recognition\n(recall@5)",           M["B1_recognition"]["recall@5"],        M["B1_recognition"]["n"],    TEAL),
    ("Surface marker → PRO\n(symbol match)",   M["B4_surface"]["any_PR"],              M["B4_surface"]["n"],        ROSE),
    ("Genus derivation\n(hierarchically valid)", M["B2_genus"]["hierarchically_valid_rate"], M["B2_genus"]["n"],   WEAK),
]
rows = sorted(rows, key=lambda r: r[1], reverse=True)

fig, ax = plt.subplots(figsize=(11, 7.0), dpi=200)
fig.patch.set_facecolor("white")
ax.set_xlim(0, 1.0); ax.set_ylim(-0.7, len(rows)-0.3)
ys = list(range(len(rows)))[::-1]

for y, (lab, val, n, col) in zip(ys, rows):
    ax.add_patch(FancyBboxPatch((0, y-0.32), 1.0, 0.64, boxstyle="round,pad=0,rounding_size=0.04",
                 fc="#eef1f4", ec="none"))
    ax.add_patch(FancyBboxPatch((0, y-0.32), max(val, 0.02), 0.64, boxstyle="round,pad=0,rounding_size=0.04",
                 fc=col, ec="none"))
    ax.text(val-0.015, y, "%.3f" % val, color="white", fontsize=13, fontweight="bold",
            va="center", ha="right")
    ax.text(1.005, y, "n=%d" % n, color=MUT, fontsize=9, va="center", ha="left")
    ax.text(-0.02, y, lab, color=INK, fontsize=10.5, va="center", ha="right")

ax.axvline(1.0, color="#c9d2da", lw=1, ls=":")
ax.set_yticks([]); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_xticklabels(["0", "0.25", "0.50", "0.75", "1.0"], color=MUT, fontsize=9)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#c9d2da")
ax.tick_params(length=0)

gs = M.get("gold_standard", {})
fig.suptitle("CellScribe vs the Cell Ontology's own expert-curated logical definitions",
             x=0.02, ha="left", fontsize=15, fontweight="bold", color=INK, y=0.99)
ax.set_title("gold standard: cl.json — %s CL terms, %s with logical definitions   ·   scored against CL, no LLM in the loop"
             % (gs.get("cl_terms_with_label", "3537"), gs.get("cl_terms_with_logical_def", "1737")),
             loc="left", fontsize=10, color=MUT, pad=12)
fig.subplots_adjust(left=0.28, right=0.93, top=0.86, bottom=0.09)
fig.text(0.5, 0.015, "Genus is the honest weak spot (heuristic) → roadmap: reasoner-derived parent   ·   B6 precision 1.00 (0 FP)",
         color=MUT, fontsize=8.5, style="italic", ha="center")

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "benchmark." + ext), facecolor="white")
print("wrote benchmark.{png,pdf,svg}")
