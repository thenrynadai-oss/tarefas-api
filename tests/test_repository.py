from datetime import date, datetime, timedelta, timezone

import pytest

from app.database import connect, init_schema
from app.repository import TaskRepository
from app.schemas import Priority, Status, TaskCreate

NOW = datetime(2026, 10, 2, 1, 30, tzinfo=timezone.utc)  # 22h30 de 01/10 em São Paulo


@pytest.fixture
def repo(tmp_path):
    conn = connect(str(tmp_path / "repo.db"))
    init_schema(conn)
    yield TaskRepository(conn, clock=lambda: NOW)
    conn.close()


def test_create_and_get(repo):
    task = repo.create(TaskCreate(title="Estudar SQL", priority=Priority.high, due_date=date(2026, 10, 5)))

    assert task.id == 1
    assert repo.get(task.id) == task
    assert task.created_at == NOW
    assert task.done is False


def test_get_missing_returns_none(repo):
    assert repo.get(42) is None


def test_update_only_changes_given_fields(repo):
    task = repo.create(TaskCreate(title="Ler", description="Capítulo 3"))

    updated = repo.update(task.id, {"title": "Ler capítulo 4", "priority": Priority.low})

    assert updated.title == "Ler capítulo 4"
    assert updated.priority is Priority.low
    assert updated.description == "Capítulo 3"


def test_update_ignores_fields_outside_allow_list(repo):
    task = repo.create(TaskCreate(title="Ler"))

    updated = repo.update(task.id, {"done": True, "id": 99})

    assert updated.id == task.id
    assert updated.done is False


def test_set_done_keeps_first_completion_time(repo):
    task = repo.create(TaskCreate(title="Ler"))

    done = repo.set_done(task.id, True)
    again = repo.set_done(task.id, True)
    reopened = repo.set_done(task.id, False)

    assert done.completed_at == NOW
    assert again.completed_at == NOW
    assert reopened.done is False
    assert reopened.completed_at is None


def test_set_done_on_missing_returns_none(repo):
    assert repo.set_done(5, True) is None


def test_delete(repo):
    task = repo.create(TaskCreate(title="Ler"))

    assert repo.delete(task.id) is True
    assert repo.delete(task.id) is False


def test_search_filters(repo):
    repo.create(TaskCreate(title="A", priority=Priority.high, due_date=date(2026, 9, 30)))
    repo.create(TaskCreate(title="B", priority=Priority.low, due_date=date(2026, 10, 1)))
    c = repo.create(TaskCreate(title="C", priority=Priority.high))
    repo.set_done(c.id, True)

    assert [t.title for t in repo.search(status=Status.pending)] == ["A", "B"]
    assert [t.title for t in repo.search(priority=Priority.high)] == ["A", "C"]
    assert [t.title for t in repo.search(due_until=date(2026, 9, 30))] == ["A"]
    assert [t.title for t in repo.search(overdue=True)] == ["A"]


def test_sql_injection_attempt_is_just_text(repo):
    repo.create(TaskCreate(title="x'); DROP TABLE tasks; --"))

    assert [t.title for t in repo.search()] == ["x'); DROP TABLE tasks; --"]


class AdvancingClock:
    """Cada leitura anda 10 minutos. A primeira cai às 23h55 de 01/10 em São Paulo e a
    segunda já cai depois da meia-noite, em 02/10: uma requisição que cruza a virada do dia."""

    def __init__(self):
        self._now = datetime(2026, 10, 2, 2, 55, tzinfo=timezone.utc)

    def __call__(self):
        current = self._now
        self._now += timedelta(minutes=10)
        return current


@pytest.fixture
def midnight_tasks(tmp_path):
    """Banco com duas tarefas e uma função que devolve um repositório com relógio novo."""
    conn = connect(str(tmp_path / "midnight.db"))
    init_schema(conn)
    seeder = TaskRepository(conn, clock=lambda: NOW)
    seeder.create(TaskCreate(title="Venceu antes", due_date=date(2026, 9, 30)))
    seeder.create(TaskCreate(title="Vence na virada", due_date=date(2026, 10, 1)))
    seeder.create(TaskCreate(title="Também vence na virada", due_date=date(2026, 10, 1)))
    yield lambda: TaskRepository(conn, clock=AdvancingClock())
    conn.close()


def test_search_overdue_true_uses_one_today_for_filter_and_rows(midnight_tasks):
    tasks = midnight_tasks().search(overdue=True)

    assert [t.title for t in tasks] == ["Venceu antes"]
    assert all(t.overdue for t in tasks)


def test_search_overdue_false_uses_one_today_for_filter_and_rows(midnight_tasks):
    # O filtro enxerga 23h55 de 01/10, então "Vence na virada" ainda não está atrasada.
    # Se cada linha lesse o relógio de novo, já seria 02/10 e ela voltaria com overdue=True.
    tasks = midnight_tasks().search(overdue=False)

    assert [t.title for t in tasks] == ["Vence na virada", "Também vence na virada"]
    assert not any(t.overdue for t in tasks)


def test_search_without_filter_uses_one_today_for_every_row(midnight_tasks):
    # Sem filtro, nenhuma leitura do relógio vem antes das linhas. Se cada linha lesse o relógio,
    # a primeira veria 01/10 e as outras, 02/10: as duas tarefas com prazo em 01/10 discordariam.
    tasks = midnight_tasks().search()

    assert [t.title for t in tasks] == ["Venceu antes", "Vence na virada", "Também vence na virada"]
    assert [t.overdue for t in tasks] == [True, False, False]
