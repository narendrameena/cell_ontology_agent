#!/usr/bin/env python3
"""A creative 'curation dossier' infographic of one real CellScribe run
(striatal parvalbumin-positive GABAergic interneuron, LLM = Groq llama-3.3-70b).
   python3 figures/make_example.py  ->  figures/example.{png,pdf}
"""
import os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Wedge

HERE = os.path.dirname(os.path.abspath(__file__))

INK="#1b2733"; MUT="#5A6472"; PAPER="#f4f6f9"
BLUE="#2C6FA6"; TEAL="#2F9E8F"; GREEN="#4C8C4A"; AMBER="#C6791F"; PURPLE="#7E6BB5"; ROSE="#C25E7C"
plt.rcParams["font.family"]="DejaVu Sans"

fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
fig.patch.set_facecolor("white")


def card(x, y, w, h, color, title=None, fc="white", lw=2.2, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.16",
                 fc=fc, ec=color, lw=lw, alpha=alpha, mutation_aspect=1))
    if title:
        ax.add_patch(FancyBboxPatch((x+0.15, y+h-0.62), min(0.55*len(title)+0.2, w-0.3), 0.5,
                     boxstyle="round,pad=0.02,rounding_size=0.12", fc=color, ec="none"))
        ax.text(x+0.28, y+h-0.37, title, color="white", fontsize=12.5, fontweight="bold", va="center")


def chip(x, y, w, text, sub, color):
    ax.add_patch(FancyBboxPatch((x, y), w, 0.72, boxstyle="round,pad=0.02,rounding_size=0.12",
                 fc=color, ec="none"))
    ax.text(x+0.18, y+0.46, text, color="white", fontsize=11.5, fontweight="bold", va="center")
    ax.text(x+0.18, y+0.20, sub, color="#eaf1f6", fontsize=8.6, va="center")


def arrow(x1, y1, x2, y2, color=MUT, lw=2.0, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                 color=color, lw=lw, shrinkA=2, shrinkB=2))


# ---------------- header ----------------
ax.add_patch(FancyBboxPatch((0.2, 8.05), 15.6, 0.82, boxstyle="round,pad=0.02,rounding_size=0.14",
             fc=INK, ec="none"))
ax.text(0.5, 8.46, "CellScribe · curation dossier", color="white", fontsize=17, fontweight="bold", va="center")
ax.text(0.5, 8.16, "striatal parvalbumin-positive GABAergic interneuron", color="#9fd0e8",
        fontsize=11.5, style="italic", va="center")
# verdict badge
ax.add_patch(FancyBboxPatch((11.35, 8.16), 4.3, 0.58, boxstyle="round,pad=0.02,rounding_size=0.14",
             fc=GREEN, ec="none"))
ax.text(13.5, 8.45, "PROPOSE new term  ·  confidence 1.00", color="white", fontsize=10.5,
        fontweight="bold", va="center", ha="center")

# ============ ① INPUT → GROUND ============
card(0.2, 4.35, 5.05, 3.4, BLUE, "① ground")
ax.text(0.45, 6.95, "INPUT", color=INK, fontsize=10, fontweight="bold")
for i, m in enumerate(["GAD1", "GAD2", "PVALB"]):
    ax.add_patch(FancyBboxPatch((0.45+i*1.15, 6.35), 1.02, 0.42, boxstyle="round,pad=0.02,rounding_size=0.1",
                 fc="#eef3f8", ec=BLUE, lw=1.3))
    ax.text(0.96+i*1.15, 6.56, m, color=BLUE, fontsize=10, fontweight="bold", ha="center", va="center")
ax.text(0.45, 6.08, "location: striatum   ·   organism: human", color=MUT, fontsize=9)
chip(0.45, 5.3, 2.25, "CL:0000099", "interneuron (genus)", BLUE)
chip(2.85, 5.3, 2.25, "UBERON:0002435", "striatum", GREEN)
chip(0.45, 4.5, 2.25, "GO:0009449", "GABA biosynth. process", AMBER)
chip(2.85, 4.5, 2.25, "NCBITaxon:9606", "Homo sapiens", TEAL)

# ============ ② EVIDENCE & TEST ============
card(5.45, 4.35, 5.05, 3.4, TEAL, "② evidence + test")
# NS-Forest panel
ax.text(5.7, 6.95, "NS-Forest marker panel", color=INK, fontsize=10, fontweight="bold")
for i, g in enumerate(["GAD2", "PVALB", "GAD1"]):
    y = 6.55 - i*0.34
    ax.text(5.72, y, g, color=INK, fontsize=9.2, va="center")
    ax.add_patch(FancyBboxPatch((6.7, y-0.11), 2.9, 0.22, boxstyle="round,pad=0.0,rounding_size=0.05",
                 fc="#e5efe9", ec="none"))
    ax.add_patch(FancyBboxPatch((6.7, y-0.11), 2.9, 0.22, boxstyle="round,pad=0.0,rounding_size=0.05",
                 fc=TEAL, ec="none"))
    ax.text(9.72, y, "1.0", color=TEAL, fontsize=8.6, va="center", fontweight="bold")
ax.text(5.7, 5.52, "F-beta = 1.00", color=TEAL, fontsize=12, fontweight="bold")
ax.text(7.3, 5.52, "(precision 1.0 · recall 1.0)", color=MUT, fontsize=8.8, va="center")
# evidence
ax.text(5.7, 5.14, "Europe PMC", color=INK, fontsize=9.6, fontweight="bold")
for i in range(5):
    ax.add_patch(FancyBboxPatch((7.05+i*0.34, 5.0), 0.26, 0.3, boxstyle="round,pad=0.0,rounding_size=0.04",
                 fc=GREEN, ec="none", alpha=0.85))
ax.text(8.9, 5.14, "5 papers", color=MUT, fontsize=9, va="center")
ax.text(5.7, 4.78, "GO × marker (QuickGO)", color=INK, fontsize=9.2, fontweight="bold")
ax.text(5.7, 4.5, "GAD1, GAD2  ←  GO:0009449", color=AMBER, fontsize=9.4, fontweight="bold")

# ============ ③ DEFINE & CLASSIFY ============
card(10.7, 4.35, 5.1, 3.4, AMBER, "③ define + classify")
ax.text(10.95, 6.95, "LLM-drafted definition  ·  Groq llama-3.3-70b", color=INK, fontsize=9.6, fontweight="bold")
defn = ("A cell of the nervous system classified as an interneuron, located in the "
        "striatum, characterised by its role in the GABA biosynthetic process; expresses "
        "GAD1, GAD2 and PVALB in Homo sapiens.")
ax.add_patch(FancyBboxPatch((10.95, 5.35), 4.6, 1.45, boxstyle="round,pad=0.06,rounding_size=0.1",
             fc="#fbf4ea", ec=AMBER, lw=1.2))
ax.text(11.12, 6.6, textwrap.fill(defn, 52), color=INK, fontsize=8.7, va="top")
ax.text(10.95, 5.05, "grounded facts only — the LLM never invents ontology terms", color=MUT,
        fontsize=8.0, style="italic")

# ============ ELK verdict strip ============
card(0.2, 0.35, 15.6, 3.75, PURPLE, "④ ELK reasons over the whole Cell Ontology")
# mini hierarchy
xs = [1.4, 3.3, 5.2, 7.1]
labels = [("CL:0000000", "cell"), ("CL:0000540", "neuron"), ("CL:0000099", "interneuron"), ("NEW", "this term")]
cols = [MUT, MUT, BLUE, ROSE]
for i, ((cur, lab), c) in enumerate(zip(labels, cols)):
    ax.add_patch(FancyBboxPatch((xs[i]-0.85, 2.7), 1.7, 0.78, boxstyle="round,pad=0.02,rounding_size=0.12",
                 fc=c, ec="none"))
    ax.text(xs[i], 3.24, lab, color="white", fontsize=9.6, fontweight="bold", ha="center", va="center")
    ax.text(xs[i], 2.95, cur, color="#eef1f6", fontsize=7.8, ha="center", va="center")
    if i < 3:
        arrow(xs[i]+0.85, 3.09, xs[i+1]-0.85, 3.09, MUT, 1.8)
ax.text(1.4, 2.25, "ELK places the candidate under its genus and finds NO existing equivalent →",
        color=INK, fontsize=10.5, va="center")
ax.add_patch(FancyBboxPatch((1.4, 1.35), 3.0, 0.62, boxstyle="round,pad=0.02,rounding_size=0.12",
             fc=ROSE, ec="none"))
ax.text(2.9, 1.66, "NOVEL — safe to mint", color="white", fontsize=11, fontweight="bold", ha="center", va="center")
ax.text(4.7, 1.66, "coherent = True   ·   no duplicate in CL v2026-06-08", color=MUT, fontsize=9.4, va="center")

# confidence gauge (right side of strip)
cx, cy, r = 12.9, 2.35, 1.05
ax.add_patch(Wedge((cx, cy), r, 0, 360, width=0.26, fc="#e7e2f0", ec="none"))
ax.add_patch(Wedge((cx, cy), r, 90, 90+360*1.0, width=0.26, fc=GREEN, ec="none"))
ax.text(cx, cy+0.05, "1.00", color=INK, fontsize=20, fontweight="bold", ha="center", va="center")
ax.text(cx, 1.02, "critic confidence", color=MUT, fontsize=9.5, ha="center", va="center")
ax.text(cx, 0.6, "8 CL-native outputs emitted:\nKGCL · MIRACL · SSSOM · ROBOT/OWL · GitHub issue",
        color=MUT, fontsize=8.6, ha="center", va="center")

fig.text(0.5, 0.012, "Every ontology ID is grounded via EBI OLS4 / QuickGO / NCBITaxon and verified by ELK — "
         "the LLM only plans and phrases.", ha="center", color=MUT, fontsize=9, style="italic")

fig.savefig(os.path.join(HERE, "example.png"), bbox_inches="tight", facecolor="white")
fig.savefig(os.path.join(HERE, "example.pdf"), bbox_inches="tight", facecolor="white")
print("wrote example.{png,pdf}")
