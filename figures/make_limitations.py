#!/usr/bin/env python3
"""'Failure modes & limitations' — editorial style (flat, typographic, restrained).
Two REAL wrong-genus runs + root causes + guardrails.
   python3 figures/make_limitations.py -> figures/limitations.{png,pdf,svg}
"""
import os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#24303A"; GREY="#6B7580"; RED="#B0463A"; GREEN="#4E7A4E"; RULE="#D3D8DD"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(15, 8.4), dpi=200)
ax.set_xlim(0, 15); ax.set_ylim(0, 8.4); ax.axis("off"); fig.patch.set_facecolor("white")


def rule(x1, x2, y, lw=1.1, color=RULE):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, solid_capstyle="round")


def vrule(x, y1, y2, lw=1.0, color=RULE):
    ax.plot([x, x], [y1, y2], color=color, lw=lw, solid_capstyle="round")


def case(x, name, inp, wrong, right, why):
    ax.text(x, 7.05, name, color=INK, fontsize=14.5, fontweight="bold")
    ax.text(x, 6.68, inp, color=GREY, fontsize=10, style="italic")
    ax.text(x, 6.22, "picked", color=GREY, fontsize=9.5, va="center")
    ax.text(x+1.5, 6.22, wrong, color=RED, fontsize=11.5, fontweight="bold", va="center")
    ax.text(x, 5.78, "should be", color=GREY, fontsize=9.5, va="center")
    ax.text(x+1.5, 5.78, right, color=GREEN, fontsize=11.5, fontweight="bold", va="center")
    ax.text(x, 5.32, textwrap.fill(why, 60), color=INK, fontsize=9.7, va="top", linespacing=1.4)


def col(x, heading, accent, items):
    ax.text(x, 3.75, heading, color=INK, fontsize=13, fontweight="bold")
    rule(x, x+1.7, 3.55, lw=2.6, color=accent)
    yy = 3.12
    for head, body in items:
        ax.text(x, yy, "–", color=accent, fontsize=11, fontweight="bold", va="center")
        ax.text(x+0.3, yy, head, color=INK, fontsize=10.6, fontweight="bold", va="center")
        ax.text(x+0.3, yy-0.28, body, color=GREY, fontsize=9.5, va="center")
        yy -= 0.63


# ---- title ----
ax.text(0.5, 7.95, "Failure modes & limitations", color=INK, fontsize=22, fontweight="bold")
ax.text(0.5, 7.55, "an honest look at where the heuristic genus breaks — and the guardrails that keep it safe",
        color=GREY, fontsize=11.5, style="italic")
rule(0.5, 14.5, 7.32, lw=1.3, color="#C3C9CF")

# ---- two failure cases (top) ----
vrule(7.5, 5.05, 7.15)
case(0.5, "Purkinje cell",
     "input:  “a large GABAergic neuron of the cerebellar cortex”",
     "interneuron · CL:0000099", "GABAergic neuron · CL:0000617",
     "The heuristic grabbed “GABAergic” — but Purkinje cells are projection neurons, not interneurons.")
case(7.9, "hepatic stellate cell",
     "input:  “a pericyte of the liver perisinusoidal space”",
     "cell · CL:0000000  (root)", "pericyte · CL:0000669",
     "No groundable genus word in the name, so it falls back to the ontology root, not a specific parent.")

# ---- divider ----
rule(0.5, 14.5, 4.15, lw=1.3, color="#C3C9CF")
vrule(7.5, 0.55, 3.85)

# ---- root causes | guardrails (bottom) ----
col(0.5, "Root causes", RED, [
    ("Genus derivation is a string heuristic", "hierarchically valid for only ~51% of terms (benchmark B2)."),
    ("ELK checks logic, not biology", "a coherent-but-wrong genus still passes the reasoner."),
    ("The LLM only phrases", "it inherits upstream errors; it won’t fix a wrong parent."),
    ("Markers need real expression data", "no matrix → specificity is prior-based, not measured."),
    ("Surface-marker → PRO grounding ≈ 83%", "gene-symbol / protein-name mismatches are missed."),
])
col(7.9, "Guardrails & roadmap", GREEN, [
    ("Curator-in-the-loop by design", "every dossier is a proposal — never auto-committed."),
    ("It shows its work", "grounded CURIEs + evidence → catch a wrong genus in seconds."),
    ("Duplicate detection worked here", "both cases were correctly flagged ALIGN to the existing term."),
    ("Confidence flags uncertainty", "both scored a moderate 0.55, not a false 1.00."),
    ("Roadmap: reasoner-derived genus", "take ELK’s inferred parent + DRAGON-AI / CurateGPT RAG."),
])

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "limitations." + ext), bbox_inches="tight", facecolor="white")
print("wrote limitations.{png,pdf,svg}")
