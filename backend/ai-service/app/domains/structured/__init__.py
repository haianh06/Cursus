"""Generic structured-generation domain — shared by Plan, Reflection, and
Practice, whose backend orchestration (DB reads, retrieval, retry heuristics)
stays in `backend`; only the actual LLM call moves here."""
