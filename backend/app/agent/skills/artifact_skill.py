"""
Artifact generation skill.

Produces either a Markdown document or a self-contained HTML/CSS snippet
based on the conversation so far, for display in the frontend Artifact
Viewer. HTML is treated as untrusted at every layer:

  - The model is instructed to produce a single self-contained fragment
    with no <script> tags and no external resource loads.
  - The API strips <script>, inline event handlers (onClick=...), and
    javascript: URLs server-side before ever storing/returning it
    (see core/sanitize.py).
  - The frontend renders HTML artifacts inside a sandboxed <iframe
    sandbox="allow-same-origin"> with no "allow-scripts", so even if
    something slipped through, it cannot execute.

This defense-in-depth (prompt + server-side strip + sandboxed render) is
documented in architecture.md under "Artifact security".
"""
import re

from app.agent.llm_provider import LLMClient
from app.core.exceptions import ArtifactRenderingError

MARKDOWN_SYSTEM_PROMPT = """You produce a clean, well-structured Markdown document \
based on the conversation so far. Use headings, bullet lists, and tables where useful. \
Output ONLY the Markdown content, no commentary before or after."""

HTML_SYSTEM_PROMPT = """You produce a single self-contained HTML/CSS snippet based on the \
conversation so far, to be rendered inside a sandboxed viewer.

Hard constraints:
- No <script> tags, no inline event handlers (onclick, onload, etc.), no javascript: URLs.
- No external resource loading (no <img src="http...">, no @import, no external fonts/CDNs).
- All CSS must be inline <style> within the snippet -- no external stylesheets.
- Keep it a single <div>...</div> root with embedded <style>, not a full <html>/<head>/<body> document.

Output ONLY the HTML, no commentary before or after, no markdown code fences."""

_SCRIPT_TAG_RE = re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL)
_EVENT_ATTR_RE = re.compile(r'\son\w+\s*=\s*("[^"]*"|\'[^\']*\')', re.IGNORECASE)
_JS_URL_RE = re.compile(r'javascript:', re.IGNORECASE)
_EXTERNAL_SRC_RE = re.compile(r'(src|href)\s*=\s*"(https?:)?//[^"]*"', re.IGNORECASE)


def sanitize_html(raw: str) -> str:
    """Defense-in-depth server-side strip. Not a substitute for sandboxed
    rendering -- belt AND suspenders."""
    cleaned = _SCRIPT_TAG_RE.sub("", raw)
    cleaned = _EVENT_ATTR_RE.sub("", cleaned)
    cleaned = _JS_URL_RE.sub("blocked:", cleaned)
    cleaned = _EXTERNAL_SRC_RE.sub('data-blocked-external="true"', cleaned)
    return cleaned.strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


async def run(
    llm: LLMClient,
    conversation_history: list[dict],
    kind: str,
    title: str,
    temperature: float = 0.4,
) -> dict:
    if kind not in ("markdown", "html"):
        raise ArtifactRenderingError(f"Unsupported artifact kind: {kind}")

    system = MARKDOWN_SYSTEM_PROMPT if kind == "markdown" else HTML_SYSTEM_PROMPT
    messages = [
        *conversation_history,
        {"role": "user", "content": f"Generate the {kind} artifact now. Title/topic: {title}"},
    ]

    result = await llm.complete(system=system, messages=messages, temperature=temperature)
    content = _strip_code_fences(result.text)

    if kind == "html":
        content = sanitize_html(content)

    return {
        "content": content,
        "kind": kind,
        "title": title,
        "llm_result": result,
    }
