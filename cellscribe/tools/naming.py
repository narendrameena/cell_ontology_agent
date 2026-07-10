"""T-type naming policy (Tan et al. 2026, "T-type hierarchy and naming").

For transcriptomic types the paper generates official names from the parent cell
type + NS-Forest marker genes, keeps the source-dataset name as a synonym, and
flags positional/transfer names whose asserted properties may not hold (e.g.
'L4 IT' used where there is no layer 4; 'VIP' where VIP is not elevated).
"""
from __future__ import annotations

import re
from typing import List

# tokens that signal a positional / annotation-transfer name
_TRANSFER = [r"\bL[1-6](/[1-6])?\b", r"\bIT\b", r"\bET\b", r"\bNP\b", r"\bCT\b",
             r"\blayer\b"]


def suggest_official_name(parent_label: str, markers: List[str],
                          location_label: str = "") -> str:
    """parent + top markers (NS-Forest style), optionally scoped by location."""
    genus = parent_label or "cell"
    loc = (" of the %s" % location_label) if location_label else ""
    mk = "/".join(markers[:3]) if markers else ""
    if mk:
        return "%s%s, %s-expressing" % (genus, loc, mk)
    return "%s%s" % (genus, loc)


def is_transfer_name(name: str) -> bool:
    n = name or ""
    return any(re.search(p, n) for p in _TRANSFER)
