"""
Ship 30 for 30-style essay skill.

Encodes the "atomic essay" writing principles as structured skill instructions
(not a one-off prompt), per the assignment requirement. These principles were
read from the public Ship 30 for 30 guide and distilled into reusable rules:

  - One idea per essay ("atomic" essay), not a survey of many ideas.
  - A hook in the first 1-2 lines that creates curiosity or tension --
    earns the next sentence before anything else.
  - Clear narrative progression: setup -> tension/insight -> resolution,
    not a flat list of facts.
  - Skimmable formatting: short paragraphs, headers, bullets, and selective
    **bold** on the single most important phrase per section -- readers
    should be able to skim and still get the point.
  - Ends on a specific, actionable takeaway, not a vague summary.
  - Every claim must be traceable to the grounded transcript material --
    this skill does NOT invent stats, quotes, or anecdotes.
"""
from app.agent.llm_provider import LLMClient
from app.agent.rag_service import format_context_block, retrieve
from app.db.schemas import Citation

SYSTEM_PROMPT = """You are a ghostwriter for the Lenny Growth Assistant, writing in the \
"Ship 30 for 30" atomic-essay style, grounded strictly in Lenny's Podcast transcripts.

Structural rules (apply all of them):
1. ONE idea. Pick the single sharpest, most specific insight from the transcript \
material and build the whole essay around it -- do not survey five ideas.
2. HOOK: open with 1-2 sentences that create curiosity, tension, or a surprising \
claim. Never open with throat-clearing ("In today's competitive landscape...").
3. NARRATIVE PROGRESSION: setup the problem -> build tension or nuance -> deliver \
the insight/resolution -> land the takeaway. Not a flat list of facts.
4. SKIMMABLE FORMATTING: use markdown headings (##), short paragraphs (2-4 sentences), \
bullet lists where they aid scanning, and selective **bold** on the single most \
important phrase per section. Do not bold entire sentences.
5. LENGTH: approximately 1,250 words.
6. TAKEAWAY: end with a specific, usable takeaway the reader can apply this week -- \
not a generic "in conclusion" summary.
7. GROUNDING: every claim, example, or framework mentioned must come from the provided \
transcript excerpts. If the excerpts don't fully support a section, narrow the scope \
of the essay rather than inventing material. Attribute the guest/episode by name where \
it strengthens credibility.

Output ONLY the essay in Markdown, starting with a compelling title as an H1."""


async def run(llm: LLMClient, topic: str, conversation_history: list[dict], temperature: float = 0.6) -> dict:
    chunks, grounded = retrieve(topic, top_k=8)
    context_block = format_context_block(chunks) if chunks else "(no relevant transcript excerpts found)"

    messages = [
        *conversation_history,
        {
            "role": "user",
            "content": (
                f"Transcript excerpts:\n\n{context_block}\n\n"
                f"Write a Ship 30 for 30-style atomic essay about: {topic}\n\n"
                "Follow every structural rule. If the excerpts are too thin to support a "
                "full essay, say so instead of inventing content."
            ),
        },
    ]

    result = await llm.complete(system=SYSTEM_PROMPT, messages=messages, temperature=temperature)

    citations = [
        Citation(source=c["source"], episode=c["episode"], chunk_id=c["chunk_id"], score=c["score"])
        for c in chunks
        if c["score"] >= 0.15
    ]

    return {
        "content": result.text,
        "citations": [c.model_dump() for c in citations],
        "grounded": grounded,
        "llm_result": result,
        "artifact_kind": "markdown",
        "artifact_title": topic[:120],
    }
