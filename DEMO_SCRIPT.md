# Demo video script (target: 2:30–3:00)

Camera on, per the assignment requirement. Suggested beats and rough timing:

## 0:00–0:25 — The problem (camera + you talking)
"Lenny's Podcast has hundreds of hours of product and growth advice, but
finding what a specific guest said about a specific problem means scrubbing
through transcripts by hand. This is the Lenny Growth Assistant — a grounded
chat assistant over the transcripts, plus two content skills: turning an
answer into a Ship 30 for 30-style essay, and generating a Markdown/HTML
artifact you can view right in the app."

## 0:25–1:10 — Product walkthrough (screen share)
1. Show the app: sidebar, provider toggle in the top bar (**point at it
   explicitly** — "this is the model toggle, cloud vs local").
2. New chat → ask a question the sample transcripts cover (e.g. "What do
   guests say about pricing PLG products?").
3. Point at the citation chips under the answer — "every claim traces back
   to a specific episode."
4. Ask a follow-up ("what about for enterprise?") — show it uses
   conversation context.
5. Ask something outside the corpus (e.g. "what's the weather today?") —
   show the low-confidence warning instead of a hallucinated answer. **This
   beat matters** — it's the clearest demonstration of "grounded, not just
   confident."

## 1:10–1:40 — Content skills
6. "Turn that into a Ship 30 for 30 essay" — let it generate, then scroll
   to show heading structure / bullets / bold emphasis / the ending
   takeaway.
7. "Generate an HTML artifact summarizing this" — show the Artifact Viewer
   panel populate beside the chat, not replacing it.

## 1:40–2:10 — Local Ollama demo (REQUIRED per the brief)
8. Toggle the provider to **Ollama** in the UI.
9. Ask the same or a similar question — show it works, and call out the
   response is now coming from a local model with no API key/cost.
10. Optionally: stop `ollama serve` beforehand and show the specific error
    banner ("Ollama isn't reachable...") to demonstrate the resilience
    story in one shot.

## 2:10–2:45 — One technical trade-off (REQUIRED per the brief)
Pick ONE and explain it briefly, on camera:

**Suggested: artifact security.** "Generated HTML is treated as untrusted —
it's constrained by the prompt, stripped of scripts/event handlers/external
resources server-side, and then rendered in a sandboxed iframe with
`allow-scripts` deliberately left out, so even if something slipped through
the first two layers, it can't execute. That's the trade-off: more
engineering upfront for defense-in-depth, instead of trusting the model to
never emit anything unsafe."

Alternative trade-offs you could pick instead, if more natural to show:
- **Rule-based skill routing** vs. an LLM-based classifier — simpler, fully
  auditable, but less flexible for oddly-phrased requests.
- **Flat FAISS index (exact search)** vs. an ANN index — simpler and exact
  at this corpus size, would need revisiting at much larger scale.
- **No streaming responses** — a deliberate scope cut in favor of spending
  the time budget on grounding/architecture/security instead of UX polish.

## 2:45–3:00 — Close
"Everything here — the schema, the ingestion pipeline, the routing logic,
and the security model — is documented in the README, PRD, architecture,
and design docs in the repo. Thanks for watching."

## Recording checklist
- [ ] Camera visibly on for the whole video (assignment requirement)
- [ ] Model toggle shown and explained
- [ ] Local Ollama demonstrated live, not just mentioned
- [ ] At least one grounded answer with visible citations
- [ ] At least one "insufficient material" / low-confidence example
- [ ] Ship 30 essay generation shown
- [ ] Artifact viewer shown rendering beside the chat
- [ ] One technical trade-off explained out loud
- [ ] Uploaded to YouTube (unlisted is fine), link included in submission form
