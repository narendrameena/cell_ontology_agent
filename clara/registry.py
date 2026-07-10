"""Tool registry with declarative schemas.

Mirrors Biomni's separation of an *environment* (a catalogue of tools described
by declarative schemas) from the *agent* that retrieves and composes them.
Here the catalogue is small and domain-specific (Cell Ontology curation), but
the mechanism is the same: tools advertise a schema + tags, and the agent
retrieves a relevant subset for a goal before planning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class ToolSpec:
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    input_schema: Dict[str, str] = field(default_factory=dict)
    returns: str = ""


class Tool:
    """Base class: a callable with a declarative :class:`ToolSpec`."""
    spec: ToolSpec

    def __call__(self, *args, **kwargs):  # pragma: no cover - overridden
        raise NotImplementedError


_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _WORD.findall((text or "").lower())


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.spec.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def select(self, goal: str, k: int = 6) -> List[Tool]:
        """Retrieve the k tools most relevant to a free-text goal.

        A deliberately transparent lexical scorer over each tool's
        name/description/tags — the point is to *show* the retrieval step, the
        same way Biomni-A1 narrows ~150 tools to a task-specific subset before
        planning. With so few tools this returns most of them, but the ranking
        is real and the mechanism scales.
        """
        gtok = set(_tokens(goal))
        scored = []
        for tool in self._tools.values():
            ttok = set(_tokens(tool.spec.name + " " + tool.spec.description
                              + " " + " ".join(tool.spec.tags)))
            overlap = len(gtok & ttok)
            scored.append((overlap, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:k]]
