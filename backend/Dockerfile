# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# LibreOffice headless: converts legacy .ppt -> .pptx for the clean-corpus
# ingest pipeline (backend/scripts/ingest_clean_corpus.py). `libreoffice-impress`
# (not the full `libreoffice` metapackage) + --no-install-recommends is enough
# for headless --convert-to and installs far faster/smaller. DEBIAN_FRONTEND
# must be noninteractive -- one of its transitive deps (tzdata) otherwise
# blocks on a debconf prompt that never comes in a non-interactive build,
# hanging forever instead of failing.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code with its final ownership. Doing this at copy time keeps
# incremental Docker rebuilds fast instead of recursively chowning the tree.
RUN mkdir -p /app/data && chown appuser:appuser /app/data
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser data ./data
# docs/planning/v2/data holds the parsed real-curriculum catalog/chunks that
# src/services/mock/{real_curriculum_service,gate2_demo,demo_data}.py read
# at ROOT.parent (repo root) relative to backend/ -- must exist alongside
# backend/ and data/ inside the image for those lookups to resolve. Only
# `data/` is whitelisted in .dockerignore (the rest of docs/ is planning/eval
# docs, not runtime input).
COPY --chown=appuser:appuser docs/planning/v2/data ./docs/planning/v2/data

USER appuser

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8000') + '/health')"]

# The entrypoint waits for Postgres, applies migrations, seeds the local
# demo dataset when requested, and only then starts Uvicorn. Keeping this in
# the image makes `docker compose up` deterministic on a fresh volume.
ENV PYTHONPATH="/app/backend"
ENTRYPOINT ["python", "backend/scripts/docker_entrypoint.py"]
