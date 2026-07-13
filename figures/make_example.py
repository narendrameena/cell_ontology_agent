#!/usr/bin/env python3
"""A clean 'curation dossier' infographic of one real CellScribe run
(striatal parvalbumin-positive GABAergic interneuron, LLM = Groq llama-3.3-70b).
2x2 grid, generous spacing.   python3 figures/make_example.py -> figures/example.{png,pdf,svg}
"""
import os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Wedge

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#1b2733"; MUT="#5A6472"
BLUE="#2C6FA6"; TEAL="#2F9E8F"; GREEN="#4C8C4A"; AMBER="#C6791F"; PURPLE="#7E6BB5"; ROSE="#C25E7C"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off"); fig.patch.set_facecolor("white")


def card(x, y, w, h, color, title):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.14",
                 fc="white", ec=color, lw=2.2))
    ax.add_patch(FancyBboxPatch((x+0.22, y+h-0.66), min(0.26*len(title)+0.35, w-0.44), 0.5,
                 boxstyle="round,pad=0.02,rounding_size=0.12", fc=color, ec="none"))
    ax.text(x+0.4, y+h-0.41, title, color="white", fontsize=13, fontweight="bold", va="center")


def chip(x, y, w, h, big, small, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.1", fc=color, ec="none"))
    ax.text(x+0.2, y+h*0.62, big, color="white", fontsize=11.5, fontweight="bold", va="center")
    ax.text(x+0.2, y+h*0.26, small, color="#edf3f7", fontsize=8.6, va="center")


def arrow(x1, y1, x2, y2, color=MUT, lw=1.8):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
                 color=color, lw=lw, shrinkA=1, shrinkB=1))


# ---------- header ----------
ax.add_patch(FancyBboxPatch((0.35, 8.15), 15.3, 0.72, boxstyle="round,pad=0.02,rounding_size=0.12", fc=INK, ec="none"))
ax.text(0.65, 8.6, "CellScribe · curation dossier", color="white", fontsize=17, fontweight="bold", va="center")
ax.text(0.65, 8.3, "striatal parvalbumin-positive GABAergic interneuron", color="#9fd0e8", fontsize=11, style="italic", va="center")
ax.add_patch(FancyBboxPatch((11.55, 8.28), 3.9, 0.46, boxstyle="round,pad=0.02,rounding_size=0.12", fc=GREEN, ec="none"))
ax.text(13.5, 8.51, "PROPOSE new term  ·  confidence 1.00", color="white", fontsize=10.5, fontweight="bold", va="center", ha="center")

# geometry: 2 columns, 2 rows
LX, RX, CW = 0.35, 8.05, 7.4
TY, BY, CH = 4.35, 0.55, 3.4

# ---------- (1) GROUND  top-left ----------
card(LX, TY, CW, CH, BLUE, "①  ground")
ax.text(LX+0.3, TY+2.55, "INPUT markers", color=INK, fontsize=10, fontweight="bold")
for i, m in enumerate(["GAD1", "GAD2", "PVALB"]):
    ax.add_patch(FancyBboxPatch((LX+0.3+i*1.45, TY+1.95), 1.3, 0.42, boxstyle="round,pad=0.02,rounding_size=0.1",
                 fc="#eef3f8", ec=BLUE, lw=1.3))
    ax.text(LX+0.95+i*1.45, TY+2.16, m, color=BLUE, fontsize=10, fontweight="bold", ha="center", va="center")
ax.text(LX+4.9, TY+2.16, "striatum · human", color=MUT, fontsize=9, va="center")
ax.text(LX+0.3, TY+1.72, "↓  grounded to real ontology terms", color=MUT, fontsize=8.6, style="italic")
chip(LX+0.3, TY+0.85, 3.35, 0.68, "CL:0000099", "interneuron (genus)", BLUE)
chip(LX+3.75, TY+0.85, 3.35, 0.68, "UBERON:0002435", "striatum", GREEN)
chip(LX+0.3, TY+0.12, 3.35, 0.68, "GO:0009449", "GABA biosynthetic process", AMBER)
chip(LX+3.75, TY+0.12, 3.35, 0.68, "NCBITaxon:9606", "Homo sapiens", TEAL)

# ---------- (2) TEST  top-right ----------
card(RX, TY, CW, CH, TEAL, "②  test + evidence")
ax.text(RX+0.3, TY+2.6, "NS-Forest marker panel", color=INK, fontsize=10, fontweight="bold")
for i, g in enumerate(["GAD2", "PVALB", "GAD1"]):
    yy = TY+2.2 - i*0.32
    ax.text(RX+0.35, yy, g, color=INK, fontsize=9.4, va="center")
    ax.add_patch(FancyBboxPatch((RX+1.55, yy-0.11), 4.6, 0.22, boxstyle="round,pad=0,rounding_size=0.05", fc=TEAL, ec="none"))
    ax.text(RX+6.3, yy, "1.0", color=TEAL, fontsize=9, fontweight="bold", va="center")
ax.text(RX+0.3, TY+1.05, "F-beta = 1.00", color=TEAL, fontsize=12.5, fontweight="bold", va="center")
ax.text(RX+2.3, TY+1.05, "precision 1.0 · recall 1.0", color=MUT, fontsize=9, va="center")
ax.text(RX+0.3, TY+0.6, "Europe PMC", color=INK, fontsize=9.4, fontweight="bold", va="center")
for i in range(5):
    ax.add_patch(FancyBboxPatch((RX+2.05+i*0.32, TY+0.48), 0.24, 0.26, boxstyle="round,pad=0,rounding_size=0.03", fc=GREEN, ec="none"))
ax.text(RX+3.75, TY+0.6, "5 papers", color=MUT, fontsize=9, va="center")
ax.text(RX+0.3, TY+0.15, "GO × marker (QuickGO):  GAD1, GAD2 ← GO:0009449",
        color=AMBER, fontsize=9.2, fontweight="bold", va="center")

# ---------- (3) DEFINE  bottom-left ----------
card(LX, BY, CW, CH, AMBER, "③  define · Groq")
ax.text(LX+0.3, BY+2.62, "llama-3.3-70b  ·  genus–differentia, 80–120 words", color=MUT, fontsize=8.8, va="center")
defn = ("A cell of the nervous system classified as an interneuron, located in the "
        "striatum, characterised by its role in the GABA biosynthetic process; "
        "expresses GAD1, GAD2 and PVALB in Homo sapiens.")
ax.add_patch(FancyBboxPatch((LX+0.3, BY+0.8), CW-0.6, 1.5, boxstyle="round,pad=0.08,rounding_size=0.1",
             fc="#fbf4ea", ec=AMBER, lw=1.1))
ax.text(LX+0.5, BY+2.12, textwrap.fill(defn, 58), color=INK, fontsize=10, va="top", linespacing=1.4)
ax.text(LX+0.3, BY+0.55, "grounded facts only — the LLM never invents ontology terms",
        color=MUT, fontsize=8.8, style="italic")

# ---------- (4) CLASSIFY  bottom-right ----------
card(RX, BY, CW, CH, PURPLE, "④  classify · ELK")
hx = [RX+0.9, RX+2.75, RX+4.6]
hl = [("CL:0000540", "neuron"), ("CL:0000099", "interneuron"), ("NEW", "this term")]
hc = [MUT, BLUE, ROSE]
for i, ((cur, lab), c) in enumerate(zip(hl, hc)):
    ax.add_patch(FancyBboxPatch((hx[i]-0.8, BY+2.05), 1.6, 0.72, boxstyle="round,pad=0.02,rounding_size=0.1", fc=c, ec="none"))
    ax.text(hx[i], BY+2.55, lab, color="white", fontsize=9.4, fontweight="bold", ha="center", va="center")
    ax.text(hx[i], BY+2.26, cur, color="#eef1f6", fontsize=7.6, ha="center", va="center")
    if i < 2:
        arrow(hx[i]+0.8, BY+2.41, hx[i+1]-0.8, BY+2.41, MUT, 1.6)
ax.text(RX+0.3, BY+1.55, "under its genus, no existing equivalent →", color=INK, fontsize=9.8, va="center")
ax.add_patch(FancyBboxPatch((RX+0.3, BY+0.7), 2.9, 0.6, boxstyle="round,pad=0.02,rounding_size=0.1", fc=ROSE, ec="none"))
ax.text(RX+1.75, BY+1.0, "NOVEL — safe to mint", color="white", fontsize=10.5, fontweight="bold", ha="center", va="center")
ax.text(RX+0.3, BY+0.32, "coherent = True · no duplicate in CL v2026-06-08", color=MUT, fontsize=8.6, va="center")
# compact confidence donut, right
cx, cy, r = RX+5.9, BY+1.15, 0.72
ax.add_patch(Wedge((cx, cy), r, 0, 360, width=0.2, fc="#e7e2f0", ec="none"))
ax.add_patch(Wedge((cx, cy), r, 90, 450, width=0.2, fc=GREEN, ec="none"))
ax.text(cx, cy, "1.00", color=INK, fontsize=15, fontweight="bold", ha="center", va="center")
ax.text(cx, cy-1.0, "critic confidence", color=MUT, fontsize=8.6, ha="center", va="center")

fig.text(0.5, 0.02, "Every ontology ID is grounded via EBI OLS4 / QuickGO / NCBITaxon and verified by ELK — the LLM only plans and phrases.",
         ha="center", color=MUT, fontsize=9.5, style="italic")

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "example." + ext), bbox_inches="tight", facecolor="white")
print("wrote example.{png,pdf,svg}")
