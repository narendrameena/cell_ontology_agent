#!/usr/bin/env python3
"""An honest 'failure modes & limitations' figure — two REAL wrong-genus cases
(Purkinje cell, hepatic stellate cell) + root causes + guardrails.
   python3 figures/make_limitations.py -> figures/limitations.{png,pdf,svg}
"""
import os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#1b2733"; MUT="#5A6472"
RED="#C0392B"; GREEN="#4C8C4A"; AMBER="#C6791F"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off"); fig.patch.set_facecolor("white")


def card(x, y, w, h, color, title):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.14",
                 fc="white", ec=color, lw=2.2))
    ax.add_patch(FancyBboxPatch((x+0.22, y+h-0.62), min(0.27*len(title)+0.35, w-0.44), 0.46,
                 boxstyle="round,pad=0.02,rounding_size=0.12", fc=color, ec="none"))
    ax.text(x+0.4, y+h-0.39, title, color="white", fontsize=12.5, fontweight="bold", va="center")


def genus_chip(x, y, w, text, mark, color):
    ax.add_patch(FancyBboxPatch((x, y), w, 0.48, boxstyle="round,pad=0.02,rounding_size=0.1", fc=color, ec="none"))
    ax.text(x+0.18, y+0.24, text, color="white", fontsize=10.5, fontweight="bold", va="center")
    ax.text(x+w-0.26, y+0.24, mark, color="white", fontsize=14, fontweight="bold", va="center", ha="center")


def bullets(x, y_top, items, accent):
    yy = y_top
    for head, body in items:
        ax.add_patch(FancyBboxPatch((x, yy-0.04), 0.16, 0.16, boxstyle="round,pad=0,rounding_size=0.03", fc=accent, ec="none"))
        ax.text(x+0.34, yy+0.04, head, color=INK, fontsize=10.6, fontweight="bold", va="center")
        ax.text(x+0.34, yy-0.26, body, color=MUT, fontsize=9.4, va="center")
        yy -= 0.62


# ---------------- header ----------------
ax.add_patch(FancyBboxPatch((0.35, 8.15), 15.3, 0.72, boxstyle="round,pad=0.02,rounding_size=0.12", fc=INK, ec="none"))
ax.text(0.65, 8.6, "CellScribe · failure modes & limitations", color="white", fontsize=17, fontweight="bold", va="center")
ax.text(0.65, 8.3, "an honest look at where the heuristic genus breaks — and the guardrails that keep it safe",
        color="#e6b8b0", fontsize=10.5, style="italic", va="center")


def failure(x, title, inp, wrong, wrong_mark, right, why):
    card(x, 4.7, 7.4, 3.1, RED, title)
    ax.text(x+0.3, 6.95, inp, color=MUT, fontsize=9.2, style="italic")
    ax.text(x+0.3, 6.5, "CellScribe genus:", color=INK, fontsize=9.8, va="center")
    genus_chip(x+2.85, 6.26, 4.3, wrong, "✗", RED)
    ax.text(x+0.3, 5.72, "should be:", color=INK, fontsize=9.8, va="center")
    genus_chip(x+2.85, 5.48, 4.3, right, "✓", GREEN)
    ax.text(x+0.3, 5.12, textwrap.fill(why, 76), color=INK, fontsize=9.2, va="top", linespacing=1.3)


failure(0.35, "✗  case A · Purkinje cell",
        "input:  “a large GABAergic neuron of the cerebellar cortex”",
        "interneuron · CL:0000099", "✗", "GABAergic neuron · CL:0000617",
        "Why: the string heuristic grabbed “GABAergic” — but Purkinje cells are projection neurons, not interneurons.")
failure(8.05, "✗  case B · hepatic stellate cell",
        "input:  “a pericyte of the liver perisinusoidal space”",
        "cell · CL:0000000 (too general)", "✗", "pericyte · CL:0000669",
        "Why: no groundable genus word in the name, so it falls back to the ontology root, not a specific parent.")

# ---------------- root causes ----------------
card(0.35, 0.5, 7.4, 3.9, AMBER, "root causes")
bullets(0.75, 3.4, [
    ("Genus derivation is a string heuristic", "hierarchically-valid for only ~51% of terms (benchmark B2)."),
    ("ELK checks logic, not biology", "a coherent-but-wrong genus still passes the reasoner."),
    ("The LLM only phrases", "it inherits upstream errors; it won’t fix a wrong parent."),
    ("Markers need real expression data", "no matrix → specificity is prior-based, not measured."),
    ("Surface-marker → PRO grounding ≈ 83%", "gene-symbol / protein-name mismatches are missed."),
], AMBER)

# ---------------- guardrails & roadmap ----------------
card(8.05, 0.5, 7.4, 3.9, GREEN, "guardrails & roadmap")
bullets(8.45, 3.4, [
    ("Curator-in-the-loop by design", "every dossier is a PROPOSAL — never auto-committed."),
    ("It shows its work", "grounded CURIEs + evidence → catch a wrong genus in seconds."),
    ("Duplicate detection worked here", "both cases correctly flagged ALIGN (no redundant term)."),
    ("Confidence flags uncertainty", "both scored a moderate 0.55, not a false 1.00."),
    ("Roadmap: reasoner-derived genus", "take ELK’s inferred parent + DRAGON-AI / CurateGPT RAG."),
], GREEN)

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "limitations." + ext), bbox_inches="tight", facecolor="white")
print("wrote limitations.{png,pdf,svg}")
