"""Verification / self-critique.

This is the component the whole design is really about: an agent must hand a
curator *evidence and its own doubts*, not a confident answer.  The critic runs
grounding, duplication and support checks, produces a calibrated confidence, and
decides whether the draft is safe to auto-suggest or must be flagged for review.
"""
from __future__ import annotations

from typing import List, Optional

from ..models import Critique, MarkerPanel, Paper, TermMatch

# weights sum to 1.0
WEIGHTS = {
    "parent_grounded": 0.22,
    "location_grounded": 0.13,
    "markers_tested": 0.25,
    "literature_support": 0.20,
    "not_duplicate": 0.20,
}
REVIEW_THRESHOLD = 0.80
DUP_SCORE = 0.90


def critique(name: str,
             existing: Optional[TermMatch],
             parent: Optional[TermMatch],
             location: Optional[TermMatch],
             panel: Optional[MarkerPanel],
             papers: List[Paper]) -> Critique:
    is_dup = bool(existing and existing.score >= DUP_SCORE)
    marker_ok = bool(panel and panel.markers and panel.score >= 0.60)

    checks = {
        "parent_grounded": bool(parent and parent.curie.startswith("CL:")),
        "location_grounded": bool(location and location.curie.startswith("UBERON:")),
        "markers_tested": marker_ok,
        "literature_support": len(papers) >= 2,
        "not_duplicate": not is_dup,
    }
    confidence = round(sum(WEIGHTS[k] for k, v in checks.items() if v), 3)

    issues: List[str] = []
    recs: List[str] = []
    if is_dup:
        issues.append("Likely already in CL as %s (%s, match %.2f) — do not create a duplicate."
                      % (existing.label, existing.curie, existing.score))
        recs.append("Align this cluster to %s and add markers/synonyms instead of a new term."
                    % existing.curie)
    if not checks["parent_grounded"]:
        issues.append("Parent (genus) did not ground to a CL term — logical definition is unsafe.")
        recs.append("Provide/curate a valid CL parent before asserting is_a.")
    if not checks["location_grounded"] and location is not None:
        issues.append("Anatomical location did not ground to Uberon.")
    if not checks["markers_tested"]:
        issues.append("Marker panel weak or untested (no expression matrix, or low specificity).")
        recs.append("Run the marker test on the reference matrix (NS-Forest) to confirm specificity.")
    if not checks["literature_support"]:
        issues.append("Thin literature support (<2 papers) for this type + markers.")

    # naming heuristic: transferred/positional names that may not reflect properties
    lname = name.lower()
    if any(tok in lname for tok in ["l2/3", "l4", "l5", "l6", " it ", "layer"]):
        issues.append("Name looks layer/transfer-derived — verify it reflects real properties "
                      "(cf. 'L4 IT' used where there is no layer 4).")
        recs.append("Confirm the positional name against anatomy before adopting the label.")

    needs_review = confidence < REVIEW_THRESHOLD or is_dup or not checks["parent_grounded"]

    # Recommended action. Note: a PROPOSE_NEW disposition still requires curator
    # approval — CLARA never writes to CL. "needs_expert_review" flags *blocking*
    # problems, not the routine human-in-the-loop sign-off every draft receives.
    if is_dup:
        disposition = "ALIGN to existing term — do not create a duplicate"
    elif not checks["parent_grounded"] or confidence < 0.5:
        disposition = "INSUFFICIENT evidence — gather more before proposing"
    else:
        disposition = "PROPOSE new term for curator approval"

    if not issues:
        recs.append("No blocking issues — route to a curator for approval (human-in-the-loop).")
    return Critique(confidence=confidence, needs_expert_review=needs_review,
                    disposition=disposition, checks=checks, issues=issues,
                    recommendations=recs)
