# HH Goa 2026 — Voice-Enabled RAG System
## Implementation Plan (5 Phases)

**Team:** TechTadkaa
**Dataset:** `ai4bharat/MSMARCO-XI`
**Deadline:** August 22, 2026, 11:59 PM

---

## ⚠️ Latency Target Interpretation (Read First)

The task asks for the full pipeline — **chunking + vector DB retrieval + everything through to final output** — under 200ms, and we're pushing for **80–100ms**.

Important scoping note we're locking in as a team:

- **STT (Sarvam/ElevenLabs) is an external network call** — typically 300ms–1.5s depending on audio length. This is outside our control and outside the "chunking → retrieval → output" leg described in the spec.
- **LLM generation (Groq/etc.)** is also an external call, typically 200ms–800ms even on fast inference providers.
- The **80–100ms target applies to**: query embedding → vector DB retrieval → context assembly → guardrail grounding check → structured response packaging (pre-generation). This is the leg that's actually engineerable to that speed.

We will report **four separate latency numbers** (STT / Retrieval-leg / Generation / Total end-to-end), each with P50/P70/P100, so the 80-100ms claim is defensible and not misleading. This is the honest and technically credible way to hit the spirit of the requirement — reviewers will trust a broken-down number far more than a single suspiciously-fast end-to-end figure.

---

## Phase 1 — Dataset, Environment & Architecture Setup

**Goal:** Everything provisioned, repo skeleton ready, low-latency architecture decisions locked in.

- [ ] Pull `ai4bharat/MSMARCO-XI` from Hugging Face; inspect schema (queries, passages, language splits)
- [ ] Decide language scope (Hindi + English subset recommended for demo clarity and speed)
- [ ] Repo structure:
  - `backend/` — FastAPI + LangGraph orchestration
  - `ingestion/` — chunking + embedding + indexing scripts
  - `frontend/` — Next.js voice UI
  - `eval/` — latency benchmarking harness
  - `docs/` — architecture diagrams, README
- [ ] Provision free-tier services:
  - **Vector DB:** Qdrant Cloud free tier (in-memory HNSW index, low-latency ANN search)
  - **Embeddings:** local `sentence-transformers` model (e.g. `multilingual-e5-small` or `bge-small-en`) — small model chosen specifically for embedding-speed, not just quality
  - **LLM:** Groq free tier (Llama 3.1/3.3 — fastest inference available free)
  - **STT:** Sarvam AI (strong Indic support)
- [ ] Set up `.env` + secrets management, shared Pydantic schemas for all service contracts
- [ ] **Latency-first architecture decisions (lock these in now):**
  - Vector DB deployed in the **same region** as backend host (network hop kills latency budget)
  - Use **async/non-blocking I/O** throughout (FastAPI async endpoints, async Qdrant client)
  - Keep embedding model loaded **in-memory at startup**, never reloaded per-request
  - Warm connection pools to Qdrant (avoid TCP/TLS handshake cost per query)

---

## Phase 2 — Multi-Strategy Chunking & Indexing

**Goal:** Rich, defensible chunking strategy (not naive fixed-size) + pre-computed index so retrieval-time cost is minimal.

- [ ] Implement 3+ chunking strategies as swappable modules:
  1. **Fixed-size with overlap** (baseline — e.g. 256 tokens, 20% overlap)
  2. **Semantic chunking** (sentence-embedding similarity drop-off to find natural boundaries)
  3. **Metadata-aware chunking** (preserve MSMARCO's native query-passage structure; attach `{source_id, language, position, doc_type}` metadata for filtered retrieval)
- [ ] Run a small recall@k evaluation across strategies using MSMARCO's query-passage ground truth pairs; pick the best-performing as default, keep others as a config toggle (this is what "real thought" in the spec is asking for — show the comparison in the README)
- [ ] **All embedding computation happens offline, at indexing time** — this is the single biggest lever for hitting 80-100ms retrieval, since nothing expensive happens at query time except embedding the (short) query itself
- [ ] Bulk upsert to Qdrant with payload indexing on metadata fields used for filtering
- [ ] Tune HNSW index params (`ef_construct`, `m`) for the speed/recall tradeoff — err toward speed given the latency target
- [ ] Benchmark raw Qdrant query latency in isolation before integrating (establish a floor)

---

## Phase 3 — Retrieval + Harnessed Generation Pipeline

**Goal:** Structured orchestration (not a raw prompt-in/text-out call) with retries and error recovery.

- [ ] Build orchestration with **LangGraph**: `embed_query → retrieve → grade_context → generate → validate_grounding → respond`
- [ ] Every node takes/returns **Pydantic-typed** structured objects — no raw string passing
- [ ] Retry logic: low-confidence retrieval (score below threshold) triggers query rewrite or fallback strategy, capped at N retries
- [ ] Error recovery: timeouts on any external call (Qdrant, Groq, Sarvam) fall back to a graceful degraded response, never a crash
- [ ] Instrument every node with timing hooks (`time.perf_counter()` around each stage) — this instrumentation *is* what feeds Phase 5's latency report, so build it in now, not bolted on later
- [ ] Document the graph structure with a diagram in README

---

## Phase 4 — Voice Integration + Guardrails

**Goal:** Voice in, grounded/safe answer out — with explicit "knows when not to answer" behavior.

- [ ] Wire Sarvam STT as pipeline entry node (audio → text → LangGraph)
- [ ] Guardrail nodes (each a first-class graph node, each logged/timed):
  - **Off-topic detector** — fast check (small classifier or lightweight prompt) on whether query is in-domain for MSMARCO-XI content
  - **Unsafe/inappropriate input filter** — basic moderation pass before the query touches the LLM
  - **Grounding/hallucination check** — after generation, verify the answer is entailed by retrieved chunks (NLI-style check or strict LLM-as-judge prompt); if not grounded, respond with an explicit "insufficient context" message rather than guessing
- [ ] Build minimal React/Next.js frontend: mic button → record → send audio → display answer + show retrieved chunks (transparency for demo + judges)
- [ ] Test guardrails with adversarial queries (off-topic, unsafe, out-of-corpus) — capture in demo video

---

## Phase 5 — Deployment, Latency Benchmarking & Submission

**Goal:** Live deployed system, defensible latency numbers, all submission requirements met.

- [ ] Deploy:
  - Backend (FastAPI + LangGraph) → Render/Railway free tier, **same region as Qdrant**
  - Frontend → Vercel free tier
  - Vector DB → Qdrant Cloud (already hosted from Phase 1)
  - Keep backend warm (avoid free-tier cold starts skewing latency numbers — use a lightweight keep-alive ping if needed)
- [ ] Build latency test harness (`eval/benchmark.py`):
  - Run 50–100 varied test queries (not cherry-picked) against the **deployed** (not local) endpoint
  - Log per-stage timestamps: STT complete, query embedded, retrieval complete, guardrails complete, generation complete
  - Compute **P50 / P70 / P100** separately for:
    1. Retrieval leg (embed → retrieve → grounding check) — **target 80-100ms**
    2. STT
    3. Generation
    4. Full end-to-end
  - Export as a table + simple chart for the submission
- [ ] If P100 retrieval leg exceeds target on some queries, document *why* (e.g. cold cache, long query) rather than hiding outliers — this is more credible for judges than a suspiciously clean number
- [ ] Final README: architecture diagram, chunking strategy comparison + recall numbers, full latency breakdown table, guardrail examples with sample adversarial queries
- [ ] Record Video 1 (90s team/process video) and Video 2 (end-to-end demo)
- [ ] Post both videos on Instagram, X, and LinkedIn — **every team member individually**, each post tagged `#RAGInGoa`, at least one public Instagram account
- [ ] Submit: form (https://forms.gle/MNvCjcv23Hn2Eeu58) + GitHub repo + live link — before Aug 22, 11:59 PM, no resubmissions

---

## Quick Reference — Why 80-100ms Is Achievable for the Retrieval Leg

| Lever | Effect |
|---|---|
| Small local embedding model, loaded once | No cold-load or network cost per query |
| Offline pre-computed passage embeddings | Query-time cost is just 1 embedding + 1 ANN search |
| Qdrant same-region as backend | Removes cross-region network latency |
| Tuned HNSW params | Trades a little recall for speed, deliberately |
| Async I/O + warm connection pools | No handshake/connection overhead per request |
| Guardrail checks kept lightweight (rule-based / small model, not a full LLM call) | Avoids adding a second LLM round-trip inside the "retrieval leg" |