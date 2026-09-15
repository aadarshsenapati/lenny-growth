"""Default skill: answers product/growth questions strictly from retrieved
Lenny's Podcast transcript chunks, with follow-up context and an explicit
"insufficient material" path instead of hallucinating."""
from app.agent.llm_provider import LLMClient
from app.agent.rag_service import format_context_block, retrieve
from app.db.schemas import Citation

SYSTEM_PROMPT = """You are the Lenny Growth Assistant, an assistant grounded strictly in \
transcripts from Lenny's Podcast (a product/growth interview show).

Rules:
1. Answer ONLY using the provided transcript excerpts. Do not use outside knowledge.
2. If the excerpts do not contain enough information to answer confidently, say so \
plainly and suggest what the user could ask instead. Do not guess.
3. When you make a claim, mention which guest/episode it came from (by the episode \
label given in the context), so the user can trace it.
4. Preserve conversational context: use the prior turns to resolve follow-up questions \
("what about for B2B?" etc.).
5. Be concise and structured. Use short paragraphs or bullets, not walls of text."""


async def run(
    llm: LLMClient,
    user_message: str,
    conversation_history: list[dict],
    temperature: float = 0.3,
) -> dict:
    chunks, grounded = retrieve(user_message)
    context_block = format_context_block(chunks) if chunks else "(no relevant transcript excerpts found)"

    messages = [
        *conversation_history,
        {
            "role": "user",
            "content": (
                f"Transcript excerpts:\n\n{context_block}\n\n"
                f"User question: {user_message}\n\n"
                "Answer using only the excerpts above. If they're insufficient, say so."
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
    }
