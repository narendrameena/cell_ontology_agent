#!/usr/bin/env python3
"""How information flows — one datum ("striatum") transformed end to end, plus the
control loop and provenance that surround it. Editorial style.
   python3 figures/make_dataflow.py -> figures/dataflow.{png,pdf,svg}
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#24303A"; GREY="#6B7580"; RULE="#D3D8DD"
BLUE="#3A6B96"; GREEN="#4E7A4E"; AMBER="#B07A2E"; TEAL="#2F7F77"; PURPLE="#6E5F94"; ROSE="#B0463A"; SLATE="#5A6472"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(15, 8.4), dpi=200)
ax.set_xlim(0, 15); ax.set_ylim(0, 8.4); ax.axis("off"); fig.patch.set_facecolor("white")


def rule(x1, x2, y, lw=1.1, color=RULE):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, solid_capstyle="round")

# ---- title ----
ax.text(0.5, 7.95, "How information flows", color=INK, fontsize=22, fontweight="bold")
ax.text(0.5, 7.55, "one value — “striatum” — transformed into a grounded, reasoner-verified, computable axiom",
        color=GREY, fontsize=11.5, style="italic")
rule(0.5, 14.5, 7.3, lw=1.3, color="#C3C9CF")

# ---- the data trace (vertical) ----
# (stage, value, what-it-is, colour), transform label sits below each row
ROWS = [
    ("INPUT",    "“striatum”", "a raw string in the CurationRequest (location_hint)", SLATE),
    ("GROUNDED", "UBERON:0002435", "a TermMatch — label ‘striatum’, score 1.00, source EBI OLS4", GREEN),
    ("AXIOM",    "part of  some  UBERON:0002435", "a differentia in the OWL class expression  (BFO:0000050)", PURPLE),
    ("VERIFIED", "NOVEL — under interneuron", "ELK over the whole CL: coherent, subsumes its genus, no duplicate", TEAL),
    ("OUTPUT",   "KGCL · ROBOT/OWL · SSSOM · KG triples", "every emitted format carries UBERON:0002435", ROSE),
]
TRANSFORMS = ["ground  ·  ols_search → EBI OLS4  (cache-first)",
              "assemble  ·  draft_definition",
              "verify  ·  ROBOT · ELK  vs  cl-base.owl",
              "emit  ·  dossier renderers"]

xdot, xtxt = 1.05, 1.55
ys = [6.55, 5.35, 4.15, 2.95, 1.75]
ax.plot([xdot, xdot], [ys[0], ys[-1]], color=RULE, lw=1.6, solid_capstyle="round", zorder=1)
for i, ((stage, val, desc, col), y) in enumerate(zip(ROWS, ys)):
    ax.add_patch(Circle((xdot, y), 0.12, fc=col, ec="white", lw=1.5, zorder=3))
    ax.text(xtxt, y + 0.26, stage, color=col, fontsize=9, fontweight="bold", va="center")
    ax.text(xtxt, y + 0.0, val, color=INK, fontsize=13, fontweight="bold", va="center")
    ax.text(xtxt, y - 0.28, desc, color=GREY, fontsize=9.4, va="center")
    if i < len(TRANSFORMS):
        ax.text(xtxt + 0.15, (y + ys[i+1]) / 2 - 0.02, "↓  " + TRANSFORMS[i],
                color=GREY, fontsize=8.8, style="italic", va="center")

# ---- right rail: the two flows that surround the data ----
RX = 9.6
rule(RX - 0.25, RX - 0.25, 1.5, lw=0)      # noop
ax.plot([RX - 0.35, RX - 0.35], [1.6, 6.7], color=RULE, lw=1.0)

ax.text(RX, 6.55, "CONTROL", color=BLUE, fontsize=11, fontweight="bold")
rule(RX, RX + 1.35, 6.35, lw=2.4, color=BLUE)
ax.text(RX, 5.95, "the A1-style agent loop decides the order and", color=INK, fontsize=9.6, va="center")
ax.text(RX, 5.66, "self-corrects:", color=INK, fontsize=9.6, va="center")
ax.text(RX + 1.15, 5.66, "retrieve → plan → execute", color=BLUE, fontsize=9.6, fontweight="bold", va="center")
ax.text(RX, 5.37, "→ self-correct → critique", color=BLUE, fontsize=9.6, fontweight="bold", va="center")
ax.text(RX, 5.0, "(if the genus doesn’t ground, it re-derives", color=GREY, fontsize=8.9, style="italic", va="center")
ax.text(RX, 4.74, "from the description and retries once).", color=GREY, fontsize=8.9, style="italic", va="center")

ax.text(RX, 4.15, "PROVENANCE", color=AMBER, fontsize=11, fontweight="bold")
rule(RX, RX + 1.85, 3.95, lw=2.4, color=AMBER)
ax.text(RX, 3.55, "every hop is auditable:", color=INK, fontsize=9.6, va="center")
for j, t in enumerate([
        "• each object is a dataclass carrying its source",
        "• each step is logged as a Step (inputs +",
        "   output summary) in dossier.trace",
        "• the LLM (optional) only PLANS + PHRASES —",
        "   it never mints an identifier"]):
    ax.text(RX, 3.2 - j * 0.34, t, color=GREY, fontsize=9.2, va="center")

fig.text(0.5, 0.02, "Three flows run together: CONTROL chooses what runs, DATA is grounded then verified, PROVENANCE is carried at every step.",
         ha="center", color=GREY, fontsize=9.5, style="italic")

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "dataflow." + ext), bbox_inches="tight", facecolor="white")
print("wrote dataflow.{png,pdf,svg}")
