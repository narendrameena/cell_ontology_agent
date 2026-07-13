#!/usr/bin/env python3
"""Render CellScribe's architecture + pipeline diagrams with Graphviz.
   python3 figures/make_diagrams.py   ->  figures/architecture.{png,svg,pdf}, figures/pipeline.{png,svg,pdf}
"""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- shared palette -------------------------------------------------------
INK   = "#1b2733"
AGENT = "#2C6FA6"   # blue   – agent core
TOOL  = "#2F9E8F"   # teal   – tools
API   = "#4C8C4A"   # green  – grounding / evidence APIs
LLM   = "#C6791F"   # amber  – optional LLM
REAS  = "#7E6BB5"   # purple – reasoning
OUT   = "#C25E7C"   # rose   – outputs
ECO   = "#5A6472"   # slate  – ecosystem
BG    = "#FFFFFF"

FONT = "Helvetica"


def render(dot: str, name: str):
    src = os.path.join(HERE, name + ".dot")
    with open(src, "w") as fh:
        fh.write(dot)
    for fmt in ("png", "svg", "pdf"):
        out = os.path.join(HERE, "%s.%s" % (name, fmt))
        args = ["dot", "-T" + fmt, src, "-o", out]
        if fmt == "png":
            args[1:1] = ["-Gdpi=200"]
        subprocess.run(args, check=True)
    print("wrote", name + ".{png,svg,pdf}")


# ===========================================================================
# 1) ARCHITECTURE
# ===========================================================================
ARCH = f"""
digraph CellScribe {{
  bgcolor="{BG}"; rankdir=TB; splines=spline; nodesep=0.35; ranksep=0.55;
  fontname="{FONT}"; compound=true;
  node [fontname="{FONT}", shape=box, style="rounded,filled", color="none",
        fontcolor=white, fontsize=12, margin="0.14,0.09", penwidth=0];
  edge [color="{INK}", arrowsize=0.7, penwidth=1.3];

  label=<<b>CellScribe</b> — a grounded, agentic Cell&nbsp;Ontology curation assistant (Biomni-inspired)>;
  labelloc=t; fontsize=20; fontcolor="{INK}";

  input [label=<<b>INPUT</b><br/>cell-type name · markers<br/>expression matrix · location>,
         fillcolor="{INK}", shape=box, style="filled"];

  // ---- agent core ----
  subgraph cluster_agent {{
    label=<<b>Agent core</b>  (A1-style loop)>; labelloc=t; fontsize=13; fontcolor="{AGENT}";
    style="rounded"; color="{AGENT}"; penwidth=2; margin=12;
    retrieve [label="retrieve", fillcolor="{AGENT}"];
    plan     [label="plan", fillcolor="{AGENT}"];
    execute  [label="execute", fillcolor="{AGENT}"];
    correct  [label="self-correct", fillcolor="{AGENT}"];
    critique [label="critique", fillcolor="{AGENT}"];
    retrieve -> plan -> execute -> correct -> critique
      [color="{AGENT}", penwidth=1.6];
    correct -> execute [style=dashed, color="{AGENT}", constraint=false, label=<<font point-size="9">retry</font>>];
  }}

  // ---- tool registry ----
  subgraph cluster_tools {{
    label=<<b>Tool registry</b>  (declarative ToolSpecs)>; labelloc=t; fontsize=13; fontcolor="{TOOL}";
    style="rounded"; color="{TOOL}"; penwidth=2; margin=10;
    t_ground [label="ols_search\\n(ground CL/Uberon/GO/PR)", fillcolor="{TOOL}"];
    t_lit    [label="literature_search", fillcolor="{TOOL}"];
    t_mark   [label="marker_panel\\n(NS-Forest)", fillcolor="{TOOL}"];
    t_go     [label="go_marker_support", fillcolor="{TOOL}"];
    t_def    [label="draft_definition\\n(genus–differentia)", fillcolor="{TOOL}"];
    t_tax    [label="taxon_constraints", fillcolor="{TOOL}"];
  }}

  // ---- grounding / evidence ----
  subgraph cluster_api {{
    label=<<b>Grounding &amp; evidence</b>>; labelloc=t; fontsize=13; fontcolor="{API}";
    style="rounded"; color="{API}"; penwidth=2; margin=10;
    ols   [label="EBI OLS4", fillcolor="{API}"];
    epmc  [label="Europe PMC", fillcolor="{API}"];
    qgo   [label="QuickGO", fillcolor="{API}"];
    tax   [label="NCBITaxon", fillcolor="{API}"];
  }}

  // ---- reasoning ----
  subgraph cluster_reason {{
    label=<<b>Reasoning</b>>; labelloc=t; fontsize=13; fontcolor="{REAS}";
    style="rounded"; color="{REAS}"; penwidth=2; margin=10;
    elk  [label="ROBOT · ELK", fillcolor="{REAS}"];
    clo  [label="cl-base.owl\\n(whole Cell Ontology)", fillcolor="{REAS}"];
    elk -> clo [color="{REAS}", dir=both, penwidth=1.4];
  }}

  // ---- optional LLM ----
  llm [label=<<b>LLM</b>  (optional)<br/>Groq · OpenAI · Anthropic<br/><font point-size="9">plan · draft · polish — never invents terms</font>>,
       fillcolor="{LLM}"];

  // ---- outputs ----
  subgraph cluster_out {{
    label=<<b>CL-native outputs</b>>; labelloc=t; fontsize=13; fontcolor="{OUT}";
    style="rounded"; color="{OUT}"; penwidth=2; margin=10;
    o1 [label="KGCL · MIRACL · SSSOM", fillcolor="{OUT}"];
    o2 [label="ROBOT template · OWL", fillcolor="{OUT}"];
    o3 [label="GitHub new-term issue", fillcolor="{OUT}"];
  }}

  // ---- ecosystem ----
  subgraph cluster_eco {{
    label=<<b>Ecosystem hand-offs</b>  (detect · defer · fall back)>; labelloc=t; fontsize=12; fontcolor="{ECO}";
    style="rounded,dashed"; color="{ECO}"; penwidth=1.6; margin=8;
    e1 [label="OntoGPT / SPIRES", fillcolor="{ECO}"];
    e2 [label="CurateGPT / DRAGON-AI", fillcolor="{ECO}"];
    e3 [label="Aurelian", fillcolor="{ECO}"];
  }}

  // ---- wiring ----
  input -> retrieve [lhead=cluster_agent];
  execute -> t_ground [lhead=cluster_tools, color="{TOOL}"];
  plan -> llm [color="{LLM}", style=dashed];
  t_def -> llm [color="{LLM}", style=dashed, dir=both];

  t_ground -> ols  [color="{API}"];
  t_lit    -> epmc [color="{API}"];
  t_go     -> qgo  [color="{API}"];
  t_tax    -> tax  [color="{API}"];

  critique -> elk [lhead=cluster_reason, color="{REAS}"];
  critique -> o1  [lhead=cluster_out, color="{OUT}"];
  t_mark -> e1 [ltail=cluster_tools, lhead=cluster_eco, color="{ECO}", style=dashed];

  {{rank=same; ols; epmc; qgo; tax;}}
}}
"""

# ===========================================================================
# 2) PIPELINE  (the real 12-step curate run, LR)
# ===========================================================================
def stage(node, title, sub, color):
    return (f'{node} [label=<<b>{title}</b><br/>'
            f'<font point-size="10" color="#e8eef4">{sub}</font>>, fillcolor="{color}"];')

PIPE = f"""
digraph pipeline {{
  bgcolor="{BG}"; rankdir=LR; splines=spline; nodesep=0.28; ranksep=0.5;
  fontname="{FONT}";
  node [fontname="{FONT}", shape=box, style="rounded,filled", color="none",
        fontcolor=white, fontsize=12, margin="0.16,0.10", penwidth=0];
  edge [color="{INK}", arrowsize=0.75, penwidth=1.5];
  label=<<b>CellScribe pipeline</b> — a live run for “striatal parvalbumin-positive GABAergic interneuron” (LLM = Groq&nbsp;llama-3.3-70b, free tier)>;
  labelloc=t; fontsize=16; fontcolor="{INK}";

  {stage('retrieve','1 · Retrieve','select relevant tools', AGENT)}
  {stage('plan','2 · Plan','LLM orders the tools', LLM)}
  {stage('ground','3 · Ground','genus → interneuron CL:0000099<br/>loc → striatum UBERON:0002435', API)}
  {stage('evidence','4 · Evidence','Europe PMC → 5 papers', API)}
  {stage('markers','5 · Test markers','NS-Forest → GAD2·PVALB·GAD1<br/>F-beta = 1.00', TOOL)}
  {stage('go','6 · GO × marker','QuickGO → GAD1,GAD2 ← GO:0009449', API)}
  {stage('define','7 · Define','LLM drafts genus–differentia<br/>(80–120 w, inline refs)', LLM)}
  {stage('reason','8 · Reason','ELK vs whole CL →<br/>NOVEL, under interneuron', REAS)}
  {stage('critique','9 · Critique','confidence = 1.00', AGENT)}
  {stage('emit','10 · Emit','KGCL · MIRACL · SSSOM<br/>ROBOT/OWL · GitHub issue', OUT)}

  retrieve -> plan -> ground -> evidence -> markers -> go -> define -> reason -> critique -> emit;
  reason -> markers [style=dashed, color="{AGENT}", constraint=false,
                     label=<<font point-size="9">self-correct</font>>];
}}
"""

if __name__ == "__main__":
    render(ARCH, "architecture")
    render(PIPE, "pipeline")
