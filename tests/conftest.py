from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import create_app

# 22h30 de 01/10/2026 em São Paulo, mas já 02/10 em UTC: pega quem usar o dia do servidor.
FIXED_NOW = datetime(2026, 10, 2, 1, 30, tzinfo=timezone.utc)


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "tarefas.db"), clock=lambda: FIXED_NOW)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_task(client):
    def _make(**fields):
        body = {"title": "Tarefa", **fields}
        response = client.post("/tasks", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
