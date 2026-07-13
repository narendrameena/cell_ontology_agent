#!/usr/bin/env python3
"""CellScribe architecture — editorial style (flat, typographic).
   python3 figures/make_architecture.py -> figures/architecture.{png,pdf,svg}
"""
import os, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
INK="#24303A"; GREY="#6B7580"; RULE="#D3D8DD"
BLUE="#3A6B96"; GREEN="#4E7A4E"; AMBER="#B07A2E"; TEAL="#2F7F77"; PURPLE="#6E5F94"; ROSE="#B0463A"; SLATE="#5A6472"
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(15, 8.4), dpi=200)
ax.set_xlim(0, 15); ax.set_ylim(0, 8.4); ax.axis("off"); fig.patch.set_facecolor("white")


def rule(x1, x2, y, lw=1.1, color=RULE):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, solid_capstyle="round")


def group(x, y, heading, accent, body, wrapw=52):
    ax.text(x, y, heading, color=INK, fontsize=12.5, fontweight="bold")
    rule(x, x + 0.083 * len(heading) + 0.2, y - 0.2, lw=2.5, color=accent)
    ax.text(x, y - 0.55, textwrap.fill(body, wrapw), color=INK, fontsize=10, va="top", linespacing=1.42)


# ---- title ----
ax.text(0.5, 7.95, "Architecture", color=INK, fontsize=22, fontweight="bold")
ax.text(0.5, 7.55, "a Biomni-inspired tool registry driven by an A1-style agent loop — grounded, reasoner-verified, curator-in-the-loop",
        color=GREY, fontsize=10.8, style="italic")
rule(0.5, 14.5, 7.3, lw=1.3, color="#C3C9CF")

# ---- input + agent loop ----
ax.text(0.5, 6.95, "input", color=GREY, fontsize=9.5, va="center")
ax.text(1.7, 6.95, "cell-type name  ·  markers  ·  expression matrix  ·  location", color=INK, fontsize=10.5, va="center")
ax.text(0.5, 6.42, "agent loop", color=GREY, fontsize=9.5, va="center")
ax.text(1.7, 6.42, "retrieve  →  plan  →  execute  →  self-correct  →  critique", color=INK, fontsize=12.5, fontweight="bold", va="center")
ax.text(1.7, 6.05, "self-correct loops back to execute on failure; plan + define call the optional LLM", color=GREY, fontsize=8.9, style="italic", va="center")
rule(0.5, 14.5, 5.75, lw=1.1)

# ---- component groups (2 cols x 3 rows) ----
LX, RX = 0.5, 8.0
vrule_y = (0.55, 5.6)
ax.plot([7.55, 7.55], vrule_y, color=RULE, lw=1.0, solid_capstyle="round")

group(LX, 5.35, "Tool registry", TEAL,
      "ols_search · literature_search · marker_panel (NS-Forest) · go_marker_support · draft_definition · taxon_constraints  — declarative ToolSpecs")
group(RX, 5.35, "Grounding & evidence", GREEN,
      "EBI OLS4 · Europe PMC · QuickGO · NCBITaxon — every identifier resolved to a real ontology term")

group(LX, 3.6, "Reasoning", PURPLE,
      "ROBOT · ELK — classifies the draft against cl-base.owl (the whole Cell Ontology) and flags duplicates of existing terms")
group(RX, 3.6, "LLM — optional", AMBER,
      "Groq (free) · OpenAI · Anthropic — plans the tool order and phrases the definition; never invents ontology terms")

group(LX, 1.85, "CL-native outputs", ROSE,
      "KGCL · MIRACL · SSSOM · ROBOT template / OWL · GitHub new-term issue")
group(RX, 1.85, "Ecosystem hand-offs", SLATE,
      "OntoGPT / SPIRES · CurateGPT / DRAGON-AI · Aurelian — detect, defer, fall back")

for ext in ("png", "pdf", "svg"):
    fig.savefig(os.path.join(HERE, "architecture." + ext), bbox_inches="tight", facecolor="white")
print("wrote architecture.{png,pdf,svg}")
