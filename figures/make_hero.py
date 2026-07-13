#!/usr/bin/env python3
"""Creative hero / title slide — 'from a cell to a concept': a drawn striatal PV
interneuron, transformed by CellScribe into a grounded ontology-graph node.
Full 13.333x7.5 slide canvas on navy.  -> figures/hero.{png,pdf,svg}
"""
import os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
NAVY="#0F2E44"; WHITE="#FFFFFF"; LIGHT="#C7D5DE"; MUT="#8CA0AE"
TEAL="#3FB6A8"; BLUE="#5B9BD5"; GREEN="#6FBF73"; AMBER="#E0A24B"; ROSE="#E0728C"; EDGE="#5E7482"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(13.333, 7.5), dpi=200)
ax.set_xlim(0, 13.333); ax.set_ylim(0, 7.5); ax.axis("off")
fig.patch.set_facecolor(NAVY); ax.set_facecolor(NAVY)


def neuron(cx, cy, color):
    # dendrites (upper hemisphere), each with two sub-branches
    for a in (118, 142, 165, 192, 214):
        r = math.radians(a)
        x1, y1 = cx + 0.28*math.cos(r), cy + 0.28*math.sin(r)
        x2, y2 = cx + 1.35*math.cos(r), cy + 1.35*math.sin(r)
        ax.plot([x1, x2], [y1, y2], color=color, lw=2.3, solid_capstyle="round", zorder=3)
        for da in (-26, 24):
            r2 = math.radians(a + da)
            ax.plot([x2, x2 + 0.62*math.cos(r2)], [y2, y2 + 0.62*math.sin(r2)],
                    color=color, lw=1.5, solid_capstyle="round", zorder=3)
    # axon (down-right) with terminal
    ar = math.radians(-22)
    xa1, ya1 = cx + 0.28*math.cos(ar), cy + 0.28*math.sin(ar)
    xa2, ya2 = cx + 2.25*math.cos(ar), cy + 2.25*math.sin(ar)
    ax.plot([xa1, xa2], [ya1, ya2], color=color, lw=2.1, solid_capstyle="round", zorder=3)
    for da in (-32, 0, 32):
        r = math.radians(-22 + da)
        ax.plot([xa2, xa2 + 0.42*math.cos(r)], [ya2, ya2 + 0.42*math.sin(r)],
                color=color, lw=1.4, solid_capstyle="round", zorder=3)
    # soma
    ax.add_patch(Ellipse((cx, cy), 0.78, 0.62, fc=color, ec=NAVY, lw=2, zorder=4))
    ax.add_patch(Ellipse((cx, cy), 0.78, 0.62, fc="none", ec=WHITE, lw=1.0, alpha=0.5, zorder=5))


def node(x, y, r, color, label, curie, lx, ly, ha="left"):
    ax.add_patch(Circle((x, y), r, fc=color, ec=WHITE, lw=1.4, zorder=6))
    ax.text(x + lx, y + ly + 0.12, label, color=WHITE, fontsize=11.5, fontweight="bold", ha=ha, va="center")
    ax.text(x + lx, y + ly - 0.16, curie, color=LIGHT, fontsize=9.2, ha=ha, va="center")


def edge(x1, y1, x2, y2, label):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                 color=EDGE, lw=1.6, shrinkA=12, shrinkB=12, zorder=2))
    ax.text((x1+x2)/2, (y1+y2)/2 + 0.16, label, color=MUT, fontsize=8.6, ha="center", va="center", style="italic")


# ---- title block ----
ax.text(0.7, 6.62, "CellScribe", color=WHITE, fontsize=50, fontweight="bold", va="center")
ax.plot([0.75, 3.0], [5.98, 5.98], color=TEAL, lw=4, solid_capstyle="round")
ax.text(0.72, 5.62, "a grounded, agentic assistant for Cell Ontology curation", color=TEAL, fontsize=18, va="center")
ax.text(0.72, 5.18, "GROUNDED  ·  AGENTIC  ·  CURATOR-IN-THE-LOOP  ·  runs on a free LLM", color=LIGHT, fontsize=12, fontweight="bold", va="center")

# ---- hero band: cell -> concept ----
neuron(2.55, 3.1, TEAL)
for mx, my, m in ((1.35, 3.75, "PVALB"), (1.15, 2.9, "GAD1"), (1.55, 2.2, "GAD2")):
    ax.text(mx, my, m, color="#BFE9E2", fontsize=8.6, fontweight="bold", ha="center", va="center")
ax.text(2.7, 1.35, "a cell", color=WHITE, fontsize=12.5, fontweight="bold", ha="center")
ax.text(2.7, 1.05, "striatal PV interneuron", color=LIGHT, fontsize=9.2, ha="center", style="italic")

# bridge arrow
ax.add_patch(FancyArrowPatch((4.55, 3.1), (7.35, 3.1), arrowstyle="-|>", mutation_scale=25,
             color=WHITE, lw=2.6, zorder=2))
ax.text(5.95, 3.5, "CellScribe", color=WHITE, fontsize=15, fontweight="bold", ha="center")
ax.text(5.95, 3.14, "ground · test · define · reason · verify", color=LIGHT, fontsize=9.3, ha="center", style="italic")

# ontology graph (kept clear of the right edge)
node(8.5, 3.1, 0.2, BLUE, "interneuron", "CL:0000099", 0.0, -0.52, ha="center")
node(10.5, 4.2, 0.17, ROSE, "this term", "NEW", 0.32, 0.0)
node(10.8, 3.05, 0.17, GREEN, "striatum", "UBERON:0002435", 0.32, 0.0)
node(10.3, 1.9, 0.17, AMBER, "GABA biosynth.", "GO:0009449", 0.32, 0.0)
edge(10.35, 4.1, 8.68, 3.24, "is a")
edge(8.7, 3.1, 10.65, 3.06, "part of")
edge(8.62, 2.95, 10.2, 2.02, "capable of")
ax.text(9.9, 1.35, "a concept", color=WHITE, fontsize=12.5, fontweight="bold", ha="center")
ax.text(9.9, 1.05, "grounded · reasoner-verified", color=LIGHT, fontsize=9.2, ha="center", style="italic")

# ---- author ----
ax.text(0.72, 0.5, "Narendra Meena — Computational Biologist", color=WHITE, fontsize=13, fontweight="bold", va="center")
ax.text(0.72, 0.22, "Interview · Cellular Semantics Team, Wellcome Sanger Institute", color=MUT, fontsize=10, style="italic", va="center")

fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "hero." + ext), facecolor=NAVY, pad_inches=0)
print("wrote hero.{png,pdf,svg}")
