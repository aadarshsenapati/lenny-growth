"""
Agent routing.

Simple, explainable intent routing rather than a black-box classifier --
appropriate for three well-defined skills with distinct trigger phrases.
If ambiguous, default to grounded_qa (the safest, most conservative skill).

Routing table (documented so an evaluator can reason about failure modes):
  - "ship30" / "essay" / "atomic essay" / "write an essay"  -> ship30 skill
  - "artifact" / "markdown doc" / "html" / "generate a doc" -> artifact skill
  - everything else                                          -> grounded_qa skill
"""
import re

SHIP30_PATTERNS = [r"\bship\s*30\b", r"\batomic essay\b", r"\bwrite (an|the) essay\b", r"\bturn (this|that) into an essay\b"]
ARTIFACT_PATTERNS = [
    r"\bartifact\b",
    r"\bmarkdown (doc|document|file)\b",
    r"\bhtml (snippet|page|artifact)\b",
    r"\bgenerate (a|the) (doc|document|page)\b",
    r"\brender (this|that|it) as\b",
]


def route(user_message: str) -> str:
    text = user_message.lower()
    for pattern in SHIP30_PATTERNS:
        if re.search(pattern, text):
            return "ship30"
    for pattern in ARTIFACT_PATTERNS:
        if re.search(pattern, text):
            return "artifact"
    return "grounded_qa"


def detect_artifact_kind(user_message: str) -> str:
    text = user_message.lower()
    if "html" in text:
        return "html"
    return "markdown"
