def titles(response):
    return [task["title"] for task in response.json()]


def test_create_returns_201_with_defaults(client):
    response = client.post("/tasks", json={"title": "  Estudar SQL  "})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Estudar SQL"
    assert body["priority"] == "medium"
    assert body["done"] is False
    assert body["overdue"] is False
    assert body["due_date"] is None
    assert body["created_at"].startswith("2026-10-02T01:30:00")


def test_blank_title_is_rejected(client):
    assert client.post("/tasks", json={"title": "   "}).status_code == 422


def test_unknown_priority_is_rejected(client):
    assert client.post("/tasks", json={"title": "x", "priority": "urgente"}).status_code == 422


def test_unknown_field_is_rejected(client):
    assert client.post("/tasks", json={"title": "x", "dono": "eu"}).status_code == 422


def test_get_missing_task_returns_404_in_portuguese(client):
    response = client.get("/tasks/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tarefa 99 não encontrada."


def test_list_orders_pending_first_then_due_date_then_priority(client, make_task):
    make_task(title="Depois", due_date="2026-10-20")
    make_task(title="Antes", due_date="2026-10-05")
    make_task(title="Sem prazo alta", priority="high")
    make_task(title="Sem prazo baixa", priority="low")
    finished = make_task(title="Feita", due_date="2026-10-01")
    client.post(f"/tasks/{finished['id']}/complete")

    assert titles(client.get("/tasks")) == ["Antes", "Depois", "Sem prazo alta", "Sem prazo baixa", "Feita"]


def test_filters(client, make_task):
    make_task(title="A", priority="high", due_date="2026-10-03")
    make_task(title="B", priority="low", due_date="2026-10-30")
    c = make_task(title="C", priority="high")
    client.post(f"/tasks/{c['id']}/complete")

    assert titles(client.get("/tasks", params={"status": "pending"})) == ["A", "B"]
    assert titles(client.get("/tasks", params={"status": "done"})) == ["C"]
    assert titles(client.get("/tasks", params={"priority": "high"})) == ["A", "C"]
    assert titles(client.get("/tasks", params={"due_until": "2026-10-10"})) == ["A"]


def test_patch_changes_only_what_was_sent(client, make_task):
    task = make_task(title="Ler capítulo 3", description="Livro de UML", due_date="2026-10-10")

    response = client.patch(f"/tasks/{task['id']}", json={"title": "Ler capítulo 4"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Ler capítulo 4"
    assert body["description"] == "Livro de UML"
    assert body["due_date"] == "2026-10-10"


def test_patch_with_null_due_date_clears_it(client, make_task):
    task = make_task(due_date="2026-10-10")

    assert client.patch(f"/tasks/{task['id']}", json={"due_date": None}).json()["due_date"] is None


def test_patch_rejects_null_title_and_priority(client, make_task):
    task = make_task()

    assert client.patch(f"/tasks/{task['id']}", json={"title": None}).status_code == 422
    assert client.patch(f"/tasks/{task['id']}", json={"priority": None}).status_code == 422


def test_patch_cannot_set_done(client, make_task):
    # Concluir é ação própria (POST /complete): o PATCH não aceita o campo `done`.
    task = make_task()

    response = client.patch(f"/tasks/{task['id']}", json={"done": True})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"
    assert client.get(f"/tasks/{task['id']}").json()["done"] is False


def test_patch_missing_task_returns_404(client):
    assert client.patch("/tasks/42", json={"title": "x"}).status_code == 404


def test_complete_and_reopen(client, make_task):
    task = make_task()

    done = client.post(f"/tasks/{task['id']}/complete").json()
    assert done["done"] is True
    assert done["completed_at"].startswith("2026-10-02T01:30:00")

    reopened = client.post(f"/tasks/{task['id']}/reopen").json()
    assert reopened["done"] is False
    assert reopened["completed_at"] is None


def test_complete_missing_task_returns_404(client):
    assert client.post("/tasks/7/complete").status_code == 404


def test_delete_then_gone(client, make_task):
    task = make_task()

    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404
    assert client.delete(f"/tasks/{task['id']}").status_code == 404


def test_overdue_uses_the_sao_paulo_day(client, make_task):
    # Agora: 22h30 de 01/10 em São Paulo, 01h30 de 02/10 em UTC.
    yesterday = make_task(title="Ontem", due_date="2026-09-30")
    today = make_task(title="Hoje", due_date="2026-10-01")

    assert client.get(f"/tasks/{yesterday['id']}").json()["overdue"] is True
    # Pelo dia do servidor (UTC) esta já estaria atrasada. Em São Paulo ainda é dia 01.
    assert client.get(f"/tasks/{today['id']}").json()["overdue"] is False


def test_done_task_is_never_overdue(client, make_task):
    task = make_task(due_date="2026-09-01")

    assert client.post(f"/tasks/{task['id']}/complete").json()["overdue"] is False


def test_filter_overdue(client, make_task):
    make_task(title="Atrasada", due_date="2026-09-30")
    make_task(title="Em dia", due_date="2026-10-01")
    make_task(title="Sem prazo")

    assert titles(client.get("/tasks", params={"overdue": "true"})) == ["Atrasada"]
    assert titles(client.get("/tasks", params={"overdue": "false"})) == ["Em dia", "Sem prazo"]


def test_docs_are_available(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "Tarefas API"
