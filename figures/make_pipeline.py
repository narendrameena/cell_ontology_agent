#!/usr/bin/env python3
"""The pipeline of one live run — editorial style (flat, typographic).
   python3 figures/make_pipeline.py -> figures/pipeline.{png,pdf,svg}
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#24303A"; GREY="#6B7580"; RULE="#D3D8DD"
BLUE="#3A6B96"; GREEN="#4E7A4E"; AMBER="#B07A2E"; TEAL="#2F7F77"; PURPLE="#6E5F94"; ROSE="#B0463A"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(15, 8.4), dpi=200)
ax.set_xlim(0, 15); ax.set_ylim(0, 8.4); ax.axis("off"); fig.patch.set_facecolor("white")


def rule(x1, x2, y, lw=1.1, color=RULE):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, solid_capstyle="round")


# steps: (n, name, result, accent)
LEFT = [
    ("1", "Retrieve", "select the relevant tools", BLUE),
    ("2", "Plan", "the LLM orders the tools", BLUE),
    ("3", "Ground", "interneuron · CL:0000099   ·   striatum · UBERON:0002435", GREEN),
    ("4", "Evidence", "5 Europe PMC papers", GREEN),
    ("5", "Test markers", "NS-Forest  →  F-beta 1.00", TEAL),
]
RIGHT = [
    ("6", "GO × marker", "GAD1, GAD2 ← GO:0009449", TEAL),
    ("7", "Define", "the LLM drafts a genus–differentia definition", AMBER),
    ("8", "Reason", "ELK vs the whole CL  →  NOVEL, under interneuron", PURPLE),
    ("9", "Critique", "confidence 1.00", BLUE),
    ("10", "Emit", "KGCL · MIRACL · SSSOM · ROBOT/OWL · GitHub issue", ROSE),
]


def column(x, steps):
    ys = [6.55, 5.35, 4.15, 2.95, 1.75]
    # connecting hairline down the number gutter
    rule(x, x, ys[0], lw=0)  # noop to keep signature; draw line below
    ax.plot([x, x], [ys[0], ys[-1]], color=RULE, lw=1.4, solid_capstyle="round", zorder=1)
    for (n, name, result, accent), y in zip(steps, ys):
        ax.add_patch(Circle((x, y), 0.2, fc=accent, ec="white", lw=1.5, zorder=2))
        ax.text(x, y, n, color="white", fontsize=9.5, fontweight="bold", ha="center", va="center", zorder=3)
        ax.text(x + 0.5, y + 0.02, name, color=INK, fontsize=12.5, fontweight="bold", va="center")
        ax.text(x + 0.5, y - 0.42, result, color=GREY, fontsize=9.7, va="center")


# ---- title ----
ax.text(0.5, 7.95, "The pipeline — one live run, end to end", color=INK, fontsize=22, fontweight="bold")
ax.text(0.5, 7.55, "striatal PV interneuron  ·  Groq llama-3.3-70b (free tier)  ·  every step is a real tool call — the LLM only plans and phrases",
        color=GREY, fontsize=10.8, style="italic")
rule(0.5, 14.5, 7.3, lw=1.3, color="#C3C9CF")

column(1.0, LEFT)
column(8.1, RIGHT)

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "pipeline." + ext), bbox_inches="tight", facecolor="white")
print("wrote pipeline.{png,pdf,svg}")
