import pytest
from sqlalchemy import inspect

from app.core.config import settings
from app.core.db import engine


def test_list_rejected_central_superuser(client, superuser_token_headers) -> None:
    if not inspect(engine).has_table("rejectedcentralsender"):
        pytest.skip("Ingestion tables missing; run: alembic upgrade head")
    r = client.get(
        f"{settings.API_V1_STR}/ingestion/rejected-central",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "count" in body
    assert isinstance(body["data"], list)
