import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("AI_SERVICE_INTERNAL_KEY", "test-internal-key")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

INTERNAL_KEY = os.environ["AI_SERVICE_INTERNAL_KEY"]


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
