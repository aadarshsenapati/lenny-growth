# design.md — UI/UX

## Principles
1. **Trust is visible, not assumed.** Every grounded answer shows its
   sources inline; a low-confidence answer is flagged rather than presented
   with the same confidence as a well-grounded one.
2. **The model toggle is a first-class, always-visible control**, not a
   settings-page afterthought — the assignment requires the active provider
   to be visible, and provider choice materially affects answer quality, so
   it lives in the top bar at all times.
3. **The artifact viewer sits beside the chat, not on top of it.** Generating
   an essay or HTML snippet shouldn't interrupt the conversation — both stay
   visible and scrollable independently.
4. **Failure states are specific, not generic.** "Something went wrong" is
   never acceptable when the system knows exactly what failed (Ollama down,
   missing index, DB unreachable) — see Error states below.

## Information architecture
```
App
├── Sidebar            (session list, new chat, delete)
├── Top bar             (title, provider toggle, DB/Ollama status pills)
└── Content split
    ├── Chat window      (messages, citations, composer)
    └── Artifact viewer   (empty state → rendered artifact)
```
Three-pane layout was chosen over a modal/drawer artifact viewer because
artifacts are frequently referenced *while* continuing the conversation
(e.g. "make the takeaway punchier") — keeping both visible avoids
context-switching.

## Key interaction states
- **Empty chat**: example prompts shown (a question, a Ship 30 request, an
  artifact request) so a first-time user immediately understands the three
  skills without reading documentation.
- **Sending**: user message appears immediately (optimistic append); a
  three-dot typing indicator appears in the assistant's turn while awaiting
  the response — the composer stays enabled for editing but Send is disabled
  to prevent duplicate submits.
- **Grounded answer**: citation chips render under the message, each showing
  the episode name (hover reveals the similarity score for a power user who
  wants it, without cluttering the default view).
- **Low-confidence answer**: an inline amber warning line —
  "The transcripts didn't clearly support this answer" — instead of hiding
  the answer or silently softening its tone, so the user can decide whether
  to trust it.
- **Artifact generated**: the viewer auto-populates and the chat shows a
  short pointer message ("Here is your markdown artifact — see the viewer
  panel") rather than dumping raw Markdown/HTML into the chat transcript.
- **Provider unreachable**: a specific inline error banner in the chat
  (e.g. "Ollama isn't reachable. Make sure `ollama serve` is running...")
  rather than a generic failure toast — actionable, not just informative.
- **Empty retrieval**: surfaced through the grounded_qa skill's own answer
  text (it explicitly says the material doesn't cover the topic) rather than
  a UI-level error, since this is expected, normal behavior, not a failure.

## Responsive behavior
- **Desktop (≥1024px)**: full three-pane layout as designed.
- **Tablet (~768–1023px)**: sidebar collapses to an icon rail (session
  titles on hover/tap); chat and artifact panes stack to ~60/40 width.
- **Mobile (<768px)**: single-column stack — sidebar becomes a slide-over
  triggered from the top bar; artifact viewer becomes a full-screen view
  reached via a "View artifact" button that appears once one exists, rather
  than permanently splitting a narrow screen in half.
(Breakpoints implemented as CSS; component structure doesn't change across
breakpoints, only layout — see `styles.css`.)

## Accessibility considerations
- Composer textarea supports `Enter` to send / `Shift+Enter` for a newline,
  matching common chat-UI conventions.
- All interactive elements (session items, delete buttons, provider toggle,
  copy/close buttons) are real `<button>` elements, not styled `<div>`s, so
  they're keyboard-focusable and screen-reader-announced by default.
- Status pills (DB/Ollama) use text labels ("connected"/"unreachable"), not
  color alone, so state isn't conveyed by color contrast alone.
- The sandboxed artifact `<iframe>` has a `title` attribute for
  screen-reader context.
- Color palette targets WCAG AA contrast for body text against the dark
  background (`#e8e9ec` on `#0f1115` / `#171a21`).

## Design decisions worth calling out
- **Dark theme by default**: matches the target user (PM/growth lead doing
  focused reading/writing work) and most reference chat UIs; not a
  requirement, an aesthetic choice documented here rather than left
  unexplained.
- **No streaming responses in v1**: a deliberate scope cut (see `PRD.md`
  "Scope choices") — the loading state uses a typing indicator instead of
  token-by-token rendering.
- **Citations are chips, not footnotes**: chips keep the answer text clean
  and scannable while still making every claim traceable, consistent with
  the "skimmable formatting" principle the Ship 30 skill also encodes.
