#!/usr/bin/env python3
"""A live curation run, editorial style (flat, typographic, restrained) — matches
make_limitations.py.  One real run: striatal PV interneuron, LLM = Groq llama-3.3-70b.
   python3 figures/make_example.py -> figures/example.{png,pdf,svg}
"""
import os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#24303A"; GREY="#6B7580"; RULE="#D3D8DD"
BLUE="#3A6B96"; GREEN="#4E7A4E"; AMBER="#B07A2E"; TEAL="#2F7F77"; PURPLE="#6E5F94"; RED="#B0463A"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(15, 8.4), dpi=200)
ax.set_xlim(0, 15); ax.set_ylim(0, 8.4); ax.axis("off"); fig.patch.set_facecolor("white")


def rule(x1, x2, y, lw=1.1, color=RULE):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, solid_capstyle="round")


def vrule(x, y1, y2, lw=1.0, color=RULE):
    ax.plot([x, x], [y1, y2], color=color, lw=lw, solid_capstyle="round")


def heading(x, y, text, accent):
    ax.text(x, y, text, color=INK, fontsize=13, fontweight="bold")
    rule(x, x + 0.09 * len(text) + 0.2, y - 0.2, lw=2.6, color=accent)


def kv(x, y, label, value, vcolor, vx=1.5, vsize=10.5, vbold=True):
    ax.text(x, y, label, color=GREY, fontsize=9.5, va="center")
    ax.text(x + vx, y, value, color=vcolor, fontsize=vsize, fontweight="bold" if vbold else "normal", va="center")


# ---- title ----
ax.text(0.5, 7.95, "A live curation run, end to end", color=INK, fontsize=22, fontweight="bold")
ax.text(0.5, 7.55, "striatal parvalbumin-positive GABAergic interneuron  ·  Groq llama-3.3-70b (free tier)  ·  every ID grounded and ELK-verified",
        color=GREY, fontsize=10.8, style="italic")
ax.text(14.5, 7.9, "PROPOSE new term", color=GREEN, fontsize=13, fontweight="bold", ha="right")
rule(0.5, 14.5, 7.3, lw=1.3, color="#C3C9CF")

# quadrant dividers
vrule(7.5, 4.55, 7.05)
rule(0.5, 14.5, 4.2, lw=1.3, color="#C3C9CF")
vrule(7.5, 0.55, 3.9)

# ---- (1) ground  (top-left) ----
heading(0.5, 6.9, "1 · Ground", BLUE)
kv(0.5, 6.42, "input", "GAD1, GAD2, PVALB  ·  striatum  ·  human", INK, vsize=10, vbold=False)
kv(0.5, 5.98, "genus", "interneuron · CL:0000099", BLUE)
kv(0.5, 5.58, "location", "striatum · UBERON:0002435", GREEN)
kv(0.5, 5.18, "function", "GABA biosynthetic process · GO:0009449", AMBER)
kv(0.5, 4.78, "taxon", "Homo sapiens · NCBITaxon:9606", TEAL)

# ---- (2) test & evidence  (top-right) ----
heading(7.9, 6.9, "2 · Test & evidence", TEAL)
kv(7.9, 6.42, "NS-Forest", "GAD2, PVALB, GAD1", INK, vx=1.7)
ax.text(7.9, 5.98, "specificity", color=GREY, fontsize=9.5, va="center")
ax.text(9.6, 5.98, "F-beta 1.00", color=TEAL, fontsize=10.5, fontweight="bold", va="center")
ax.text(11.0, 5.98, "precision 1.0 · recall 1.0", color=GREY, fontsize=9, va="center")
kv(7.9, 5.54, "evidence", "5 Europe PMC papers", INK, vx=1.7, vbold=False)
kv(7.9, 5.1, "GO × marker", "GAD1, GAD2 ← GO:0009449", AMBER, vx=1.7)

# ---- (3) define · Groq  (bottom-left) ----
heading(0.5, 3.72, "3 · Define — Groq", AMBER)
ax.text(0.5, 3.32, "llama-3.3-70b  ·  genus–differentia, 80–120 words", color=GREY, fontsize=9.2, va="center")
defn = ("A cell of the nervous system classified as an interneuron, located in the striatum, "
        "characterised by its role in the GABA biosynthetic process; expresses GAD1, GAD2 and "
        "PVALB in Homo sapiens.")
ax.text(0.5, 2.95, textwrap.fill(defn, 64), color=INK, fontsize=10.3, va="top", linespacing=1.5)
ax.text(0.5, 1.35, "grounded facts only — the LLM never invents ontology terms", color=GREY, fontsize=9.3, style="italic")

# ---- (4) classify · ELK  (bottom-right) ----
heading(7.9, 3.72, "4 · Classify — ELK", PURPLE)
kv(7.9, 3.3, "places it", "neuron → interneuron → this term", INK, vx=1.5, vbold=False)
kv(7.9, 2.86, "verdict", "coherent · under its genus · no equivalent", INK, vx=1.5, vbold=False)
ax.text(7.9, 2.4, "→", color=RED, fontsize=12, fontweight="bold", va="center")
ax.text(8.35, 2.4, "NOVEL — safe to mint", color=RED, fontsize=11.5, fontweight="bold", va="center")
ax.text(7.9, 1.88, "confidence", color=GREY, fontsize=9.5, va="center")
ax.text(9.4, 1.82, "1.00", color=GREEN, fontsize=17, fontweight="bold", va="center")
kv(7.9, 1.3, "outputs", "KGCL · MIRACL · SSSOM · ROBOT/OWL · GitHub issue", GREY, vx=1.5, vsize=9, vbold=False)

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "example." + ext), bbox_inches="tight", facecolor="white")
print("wrote example.{png,pdf,svg}")
