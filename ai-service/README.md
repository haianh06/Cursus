# Cursus AI Service

Private service for all generative intelligence. `backend/` owns identity,
authorization, persistence and business writes; this service owns prompts,
model routing, guardrails, RAG response composition and streamed generation.

## Layout

- `app/api/`: internal HTTP endpoints only
- `app/core/`: settings, provider clients and observability
- `app/domains/`: chat, planning, reflection, practice and risk policies
- `app/safety/`: academic-integrity and wellbeing safety checks

No browser may call this service directly. Every request needs the internal
service key and carries already-authorized, minimum necessary context.
