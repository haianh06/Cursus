# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code with its final ownership. Doing this at copy time keeps
# incremental Docker rebuilds fast instead of recursively chowning the tree.
RUN mkdir -p /app/data && chown appuser:appuser /app/data
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# The entrypoint waits for Postgres, applies migrations, seeds the local
# demo dataset when requested, and only then starts Uvicorn. Keeping this in
# the image makes `docker compose up` deterministic on a fresh volume.
ENTRYPOINT ["python", "scripts/docker_entrypoint.py"]
