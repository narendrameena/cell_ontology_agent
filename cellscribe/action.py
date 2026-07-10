"""Run CellScribe inside a GitHub Action on a CL 'new term' issue (Tan et al. 2026, Fig 7).

Parses a simple `key: value` issue body (name, description, markers, surface_markers,
functions, location, organism, orcid, reference), runs the agent, and writes a Markdown
dossier + a pre-filled CL new-term issue to `dossier.md` (and $GITHUB_STEP_SUMMARY) for
the workflow to post as a comment — draft first, curator reviews and merges.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cellscribe import CuratorAgent, CurationRequest


def parse_issue(body: str) -> dict:
    fields = {}
    for line in (body or "").splitlines():
        m = re.match(r"\s*[-*]?\s*\**([A-Za-z_ ]+?)\**\s*:\s*(.+)", line)
        if m:
            fields[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
    return fields


def _csv(s: str):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def main() -> int:
    f = parse_issue(os.environ.get("ISSUE_BODY", ""))
    name = f.get("name") or f.get("cell_type") or os.environ.get("ISSUE_TITLE", "")
    if not name:
        print("No cell type name found in the issue."); return 1
    req = CurationRequest(
        name=name, description=f.get("description", ""),
        markers=_csv(f.get("markers", "")), surface_markers=_csv(f.get("surface_markers", "")),
        functions=_csv(f.get("functions", "")), location_hint=f.get("location", ""),
        organism=f.get("organism", "Homo sapiens"), orcid=f.get("orcid", ""),
        reference_data=f.get("reference", ""))
    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    dossier = CuratorAgent(use_llm=use_llm, verbose=False).curate(req)
    out = (dossier.to_markdown()
           + "\n\n---\n\n## Pre-filled CL new-term issue\n\n" + dossier.to_github_issue())
    with open("dossier.md", "w") as fh:
        fh.write(out)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
