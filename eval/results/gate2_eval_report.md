# Cursus Gate-2 evaluation report

> **Nguồn/backup** — số liệu ở file này đã được merge vào [`eval/results/report.md`](report.md)
> (bản BTC-mandated, nộp chính thức). File này giữ lại nguyên vẹn làm nguồn/tham chiếu.

Generated: 2026-08-12T20:02:33.575161+00:00

Both suites run against the real services with no network and no `GOOGLE_API_KEY`, i.e. the deterministic path the demo uses.

### Guardrail

**30/30 passed (100%)**

No failures.

### RAG / retrieval citation

**24/25 passed (96%)**

| case | expected | actual | note |
|---|---|---|---|
| rag_019 | SSA101-CLO4 | SSA101-session-7,SSA101-session-8,SSA101-session-10 | expected chunk not in top-k |
