# Lenny Growth Assistant — Demo Video Project Brief

## 1. Project Overview

The **Lenny Growth Assistant** is a grounded conversational AI application designed to let users interact with knowledge extracted from Lenny's Podcast transcripts.

The core idea is simple:

> Instead of manually searching through hundreds of hours of podcast transcripts, a user can ask a product or growth question and receive an answer grounded in the available transcript corpus.

The application combines:

* Conversational question answering
* Retrieval-Augmented Generation (RAG)
* Transcript ingestion and vector search
* Multiple LLM providers
* Rule-based AI skill routing
* Ship 30 for 30 essay generation
* Markdown/HTML artifact generation
* A sandboxed Artifact Viewer
* Persistent conversations and messages
* Grounding and low-confidence handling

The project is therefore not simply a chatbot. It is an **AI application built around a controlled knowledge source, retrieval pipeline, multiple skills, and safety mechanisms for generated artifacts.**

---

# 2. High-Level AI Pipeline

The overall system can be understood as the following pipeline:

```text
Podcast Transcripts
        │
        ▼
Transcript Ingestion
        │
        ▼
Cleaning + Chunking
        │
        ▼
Embeddings
        │
        ▼
FAISS Vector Index
        │
        │
        ▼
User Question
        │
        ▼
Skill Router
        │
        ├──────────────► Grounded Q&A
        │
        ├──────────────► Ship 30 for 30
        │
        └──────────────► Artifact Generation
        │
        ▼
Relevant Transcript Context
        │
        ▼
LLM Provider
   ┌────┴─────┐
   │          │
 Groq      Ollama
   │          │
   └────┬─────┘
        │
        ▼
Generated Response
        │
        ▼
Grounding / Security / Formatting
        │
        ▼
Chat Response / Essay / Artifact
```

The important concept to explain during the demo is that **the LLM is not expected to answer everything from its general knowledge**.

For grounded questions, the system first retrieves relevant information from the transcript corpus and then uses that retrieved material as context for the LLM.

---

# 3. Transcript and RAG Pipeline

## 3.1 Transcript ingestion

The source material consists of podcast transcripts.

The ingestion process takes the transcript files and prepares them for retrieval.

The pipeline performs:

1. Transcript loading
2. Text processing
3. Chunking
4. Embedding generation
5. Vector indexing

The resulting embeddings are stored in a **FAISS vector index**.

The purpose of this stage is to transform a large collection of text into a structure that allows the system to efficiently find semantically relevant pieces of transcript.

---

## 3.2 Chunking

Large transcripts are not sent directly to the LLM.

Instead, transcripts are divided into smaller chunks.

For example:

```text
Episode transcript
        │
        ├── Chunk 1
        ├── Chunk 2
        ├── Chunk 3
        ├── Chunk 4
        └── ...
```

Each chunk becomes an independently searchable unit.

This makes retrieval more precise and prevents the application from unnecessarily sending an entire episode to the LLM.

---

## 3.3 Embeddings and FAISS

Each transcript chunk is converted into an embedding representation.

Conceptually:

```text
Text
 │
 ▼
Embedding Model
 │
 ▼
Vector Representation
 │
 ▼
FAISS
```

When a user asks a question, the question is also represented in vector space.

The system can then identify transcript chunks that are semantically similar to the question.

For example:

```text
Question:
"What do guests say about pricing PLG products?"

              │
              ▼

        Query Embedding
              │
              ▼
       FAISS Similarity Search
              │
       ┌──────┼──────┐
       ▼      ▼      ▼
    Chunk A Chunk B Chunk C
       │      │      │
       └──────┼──────┘
              ▼
      Retrieved Context
```

This is the retrieval component of the **RAG pipeline**.

---

# 4. Skill Routing

The application does not treat every request as the same type of task.

A **rule-based router** determines which skill should handle the request.

There are three primary skills:

### `grounded_qa`

Used for normal questions about the podcast corpus.

Example:

```text
"What do guests say about pricing PLG products?"
```

The system retrieves relevant transcript material and asks the LLM to answer using that context.

---

### `ship30`

Used when the user asks to transform information into a **Ship 30 for 30-style essay**.

Example:

```text
"Turn that into a Ship 30 for 30 essay."
```

The application takes the relevant conversational context and generates a structured long-form piece containing elements such as:

* Headings
* Bullets
* Bold emphasis
* A clear takeaway

---

### `artifact`

Used when the user asks the system to create a Markdown or HTML artifact.

Example:

```text
"Generate an HTML artifact summarizing this."
```

The generated artifact is then displayed inside the application's **Artifact Viewer**.

---

# 5. LLM Architecture

The application uses a common LLM interface so that the underlying provider can be changed without rewriting the application logic.

There are two primary options:

```text
                LLM Interface
                     │
             ┌───────┴───────┐
             │               │
           Groq            Ollama
             │               │
          Cloud            Local
```

## Groq

Groq provides cloud-based inference.

The exact model is configured through:

```text
GROQ_MODEL
```

The application does not fundamentally depend on one hardcoded model family. The configured model must simply be available to the user's Groq API key.

---

## Ollama

Ollama provides local model execution.

For the demo, the application can use a locally pulled model such as:

```text
llama3.1:8b
```

This demonstrates that the application's architecture is not tied exclusively to a cloud LLM.

The same application workflow can therefore operate through:

```text
Cloud LLM → Groq

or

Local LLM → Ollama
```

---

# 6. Why the LLM Is Not the Whole System

An important point to communicate during the demo is that the LLM is only one component.

The system can be viewed as:

```text
                User
                 │
                 ▼
          Conversational UI
                 │
                 ▼
            Skill Router
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
    Grounded   Ship30   Artifact
       │         │         │
       └─────────┼─────────┘
                 ▼
             Retrieval
                 │
                 ▼
             FAISS/RAG
                 │
                 ▼
              LLM Layer
            ┌────┴────┐
            ▼         ▼
          Groq     Ollama
            │         │
            └────┬────┘
                 ▼
              Response
```

This separation makes the architecture easier to test, replace, and extend.

---

# 7. Grounded Responses and Hallucination Control

One of the most important features to demonstrate is what happens when the system **does not have enough information**.

For example:

```text
"What do the transcripts say about today's weather?"
```

This is outside the knowledge contained in the transcript corpus.

Instead of simply asking the LLM to produce a confident answer, the system evaluates the retrieval results and can identify that there is insufficient supporting material.

The user should see a **low-confidence / insufficient-material response** rather than an invented answer.

This demonstrates the key design principle:

> The assistant should be grounded in the available corpus rather than confidently inventing information.

---

# 8. Conversation Context

The application also supports multi-turn conversations.

For example:

```text
User:
"What do guests say about pricing PLG products?"

Assistant:
[Grounded answer + citations]

User:
"What about for enterprise?"

Assistant:
[Answer using the previous conversation context]
```

The second question does not need to repeat the entire context.

This demonstrates that the application is a **conversational assistant**, rather than simply a collection of independent question-answer requests.

---

# 9. Citations and Traceability

Grounded answers include citation information associated with the retrieved transcript material.

During the demo, the citation chips should be shown clearly.

The purpose is traceability:

```text
User Question
      │
      ▼
Relevant Transcript Chunks
      │
      ▼
LLM Answer
      │
      ▼
Citation Information
```

This allows the user to understand where the answer originated.

The goal is not simply:

> "Here is an answer."

It is:

> "Here is an answer based on these retrieved pieces of the source material."

---

# 10. Ship 30 for 30 Content Skill

The second major AI capability is content transformation.

A grounded answer can be transformed into a longer-form essay.

Example flow:

```text
Grounded Q&A
     │
     ▼
"Turn that into a Ship 30 for 30 essay"
     │
     ▼
Ship30 Skill
     │
     ▼
LLM
     │
     ▼
Structured Essay
```

The generated essay should demonstrate:

* Approximately 1,250 words
* Clear heading structure
* Bullets where appropriate
* Bold emphasis
* A specific ending takeaway

The important point is that the application can move from **information retrieval** to **content creation** without changing the underlying conversation.

---

# 11. Artifact Generation

The third major capability is artifact generation.

The user can request something such as:

```text
"Generate an HTML artifact summarizing this."
```

The system generates the requested artifact and displays it in the Artifact Viewer.

The architecture is approximately:

```text
Conversation Context
        │
        ▼
 Artifact Skill
        │
        ▼
      LLM
        │
        ▼
Generated Markdown / HTML
        │
        ▼
Server-side Sanitization
        │
        ▼
Sandboxed iframe
        │
        ▼
Artifact Viewer
```

This gives the application a second output surface beyond the normal chat response.

---

# 12. Artifact Security

Artifact security is one of the most important technical design decisions in the project.

Generated HTML should be considered **untrusted content**.

The application therefore uses multiple layers of protection.

```text
Generated HTML
      │
      ▼
Prompt-level constraints
      │
      ▼
Server-side sanitization
      │
      ▼
Sandboxed iframe
      │
      ▼
Rendered Artifact
```

The generated content is sanitized to remove unsafe constructs such as scripts, event handlers, and external resources.

The Artifact Viewer then uses a sandboxed iframe, with scripting deliberately restricted.

The design principle is:

> Do not trust the LLM to always generate safe HTML.

Instead, the system uses **defense in depth**.

This is an important example of where conventional application security is used alongside AI.

---

# 13. Local AI Demonstration

The local Ollama demonstration is important because it shows provider independence.

The same application can switch from:

```text
Groq
Cloud inference
```

to:

```text
Ollama
Local inference
```

without changing the core application workflow.

The demo should show:

1. Groq selected.
2. Ask a question.
3. Receive the response.
4. Switch the provider to Ollama.
5. Ask a similar question.
6. Receive a response from the local model.

This demonstrates the abstraction provided by the common LLM interface.

It also shows that the project can operate without depending exclusively on a cloud API.

---

# 14. Error Handling and Resilience

The application also contains explicit error handling around infrastructure components.

For example:

```text
Groq unavailable
        │
        ▼
Typed provider error
        │
        ▼
Actionable response
```

Similarly:

```text
Ollama unavailable
        │
        ▼
Specific provider error
        │
        ▼
User-visible error banner
```

Instead of converting every infrastructure problem into an unexplained generic HTTP 500, the system attempts to expose the actual cause.

This makes the application easier to debug and demonstrate.

---

# 15. Database and Persistence

The backend uses:

* FastAPI
* Async SQLAlchemy
* MySQL
* Alembic migrations

The database stores application state such as conversations and messages.

The conceptual flow is:

```text
React Frontend
      │
      ▼
FastAPI API
      │
      ▼
SQLAlchemy
      │
      ▼
MySQL
```

This allows a user to refresh the application and still have their session and messages available.

---

# 16. Overall Technology Stack

The project can be summarized as:

| Layer            | Technology                     |
| ---------------- | ------------------------------ |
| Frontend         | React + Vite                   |
| Backend          | FastAPI                        |
| Database         | MySQL                          |
| ORM              | Async SQLAlchemy               |
| Migrations       | Alembic                        |
| Vector Search    | FAISS                          |
| Cloud LLM        | Groq                           |
| Local LLM        | Ollama                         |
| AI Skills        | Grounded Q&A, Ship30, Artifact |
| Routing          | Rule-based router              |
| Artifact UI      | Sandboxed iframe               |
| Containerization | Docker + Docker Compose        |
| Testing          | Pytest                         |
| CI               | GitHub Actions                 |

The architecture and project documentation describe the backend, retrieval, security, UI, and deployment structure.

---

# 17. Recommended Demo Flow

The demo should not be treated as a script that has to be memorized.

Instead, demonstrate the system through the following sequence.

### Part 1 — Introduce the problem

Briefly explain:

* Lenny's Podcast contains a large amount of product and growth knowledge.
* Finding a specific answer manually through transcripts is inconvenient.
* This project creates a conversational interface over that knowledge.

---

### Part 2 — Show the application

Show:

* Sidebar
* Chat interface
* Provider toggle
* Artifact Viewer area

Explain the major components rather than reading UI labels.

---

### Part 3 — Demonstrate grounded Q&A

Ask a question covered by the sample transcripts.

Show:

* Retrieved answer
* Citation chips
* Source traceability

Explain that the answer is generated using retrieved transcript context.

---

### Part 4 — Demonstrate conversation context

Ask a follow-up question such as:

```text
"What about for enterprise?"
```

Show that the assistant understands the preceding conversation.

---

### Part 5 — Demonstrate grounding failure

Ask something outside the corpus.

For example:

```text
"What's the weather today?"
```

Show the insufficient-material / low-confidence behavior.

This is important because it demonstrates that the application is designed to **avoid unsupported answers**, rather than simply generating a confident response.

---

### Part 6 — Demonstrate the Ship30 skill

Ask:

```text
"Turn that into a Ship 30 for 30 essay."
```

Show the resulting structured essay.

Point out:

* Headings
* Formatting
* Long-form structure
* Final takeaway

---

### Part 7 — Demonstrate artifact generation

Ask:

```text
"Generate an HTML artifact summarizing this."
```

Show that the Artifact Viewer appears beside the conversation and renders the generated content.

---

### Part 8 — Demonstrate Ollama

Switch:

```text
Groq → Ollama
```

Ask another question and demonstrate that the same application can use a local LLM.

Explain that the LLM provider is abstracted behind a common interface.

---

### Part 9 — Explain one technical decision

The strongest technical topic to explain is **artifact security**.

Explain the three layers:

```text
Prompt constraints
        +
Server-side sanitization
        +
Sandboxed iframe
```

Then explain why this is necessary:

> Generated content is treated as untrusted because an LLM should not be considered a security boundary.

---

# 18. What the Demo Should Communicate

By the end of the demo, the viewer should understand five things:

### 1. It is a RAG application

The system retrieves relevant transcript material before generating grounded answers.

### 2. It is conversational

The assistant maintains context across follow-up questions.

### 3. It has multiple AI skills

The same conversational interface supports:

```text
Grounded Q&A
     ↓
Ship 30 Essay
     ↓
Markdown/HTML Artifact
```

### 4. It is LLM-provider independent

The application can use:

```text
Groq
or
Ollama
```

through the same LLM abstraction.

### 5. It treats AI output as untrusted

Generated artifacts are sanitized and sandboxed rather than being directly trusted.

---

# 19. One-Sentence Project Explanation

If you need a concise explanation during the demo:

> **The Lenny Growth Assistant is a RAG-based conversational AI application that retrieves knowledge from Lenny's Podcast transcripts, routes requests to specialized AI skills, supports both cloud and local LLMs, and safely turns grounded conversations into essays and interactive artifacts.**

---

# 20. Core Architecture to Remember

If you forget everything else during the recording, remember this:

```text
              Lenny Podcast Transcripts
                       │
                       ▼
                Ingestion Pipeline
                       │
                       ▼
              Chunking + Embeddings
                       │
                       ▼
                   FAISS
                       │
                       │
                 User Question
                       │
                       ▼
                 Skill Router
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Grounded      Ship30       Artifact
         Q&A
          │            │            │
          └────────────┼────────────┘
                       ▼
                  LLM Interface
                  ┌────┴────┐
                  ▼         ▼
                Groq      Ollama
                  │         │
                  └────┬────┘
                       ▼
                 Generated Output
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          Chat/Essay          Artifact
                                 │
                                 ▼
                         Sanitization
                                 │
                                 ▼
                         Sandboxed Viewer
```

**The key message of the project is therefore:**

> **Retrieve → Ground → Route → Generate → Securely Render.**

This is the pipeline that should drive the explanation throughout the demo.
