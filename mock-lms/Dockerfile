# Build the human-facing EduSync SPA first.
FROM node:22-alpine AS web-builder
WORKDIR /web
COPY mock-lms/frontend/package.json mock-lms/frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci
COPY mock-lms/frontend ./frontend
RUN cd frontend && npm run build

# Package the standalone Mock LMS API, SQLite datastore, and built SPA.
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MOCK_LMS_DB_PATH=/app/data/mock_lms.db

COPY mock-lms/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home appuser \
    && mkdir -p /app/data /app/mock-lms/app/static/dist \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser mock-lms/app ./mock-lms/app
COPY --chown=appuser:appuser mock-lms/scripts ./mock-lms/scripts
COPY --chown=appuser:appuser docs/planning/v2/data ./docs/planning/v2/data
COPY --from=web-builder --chown=appuser:appuser /web/app/static/dist ./mock-lms/app/static/dist

USER appuser
EXPOSE 9000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/health')" || exit 1

ENTRYPOINT ["sh", "mock-lms/scripts/docker_entrypoint.sh"]
