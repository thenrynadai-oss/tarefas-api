import sqlite3
from collections.abc import Callable
from datetime import date, datetime, timezone
from enum import Enum

from app.clock import local_today
from app.schemas import Priority, Status, Task, TaskCreate

_COLUMNS = "id, title, description, priority, due_date, done, created_at, completed_at"
_ORDER = (
    "ORDER BY done, due_date IS NULL, due_date, "
    "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id"
)
# Só estes campos podem ser alterados por PATCH. Os nomes de coluna saem daqui, nunca do cliente.
_UPDATABLE = ("title", "description", "priority", "due_date")


class TaskRepository:
    """Todas as consultas da aplicação (o schema fica em database.py).

    Valores sempre por parâmetro (?), nunca concatenados. Cada chamada pública lê o dia de hoje
    uma vez só e usa o mesmo valor no filtro e em todas as linhas devolvidas.
    """

    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], datetime]) -> None:
        self._conn = conn
        self._clock = clock

    def create(self, data: TaskCreate) -> Task:
        today = self._today()
        cursor = self._conn.execute(
            "INSERT INTO tasks (title, description, priority, due_date, created_at) VALUES (?, ?, ?, ?, ?)",
            (data.title, data.description, data.priority.value, _to_db(data.due_date), self._now_iso()),
        )
        self._conn.commit()
        task = self._fetch(cursor.lastrowid, today)
        assert task is not None
        return task

    def get(self, task_id: int) -> Task | None:
        return self._fetch(task_id, self._today())

    def search(
        self,
        status: Status | None = None,
        priority: Priority | None = None,
        due_until: date | None = None,
        overdue: bool | None = None,
    ) -> list[Task]:
        today = self._today()
        clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            clauses.append("done = ?")
            params.append(1 if status is Status.done else 0)
        if priority is not None:
            clauses.append("priority = ?")
            params.append(priority.value)
        if due_until is not None:
            clauses.append("due_date IS NOT NULL AND due_date <= ?")
            params.append(due_until.isoformat())
        if overdue is not None:
            late = "(done = 0 AND due_date IS NOT NULL AND due_date < ?)"
            clauses.append(late if overdue else f"NOT {late}")
            params.append(today.isoformat())
        where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
        rows = self._conn.execute(f"SELECT {_COLUMNS} FROM tasks {where}{_ORDER}", params).fetchall()
        return [self._to_task(row, today) for row in rows]

    def update(self, task_id: int, changes: dict[str, object]) -> Task | None:
        today = self._today()
        if self._fetch(task_id, today) is None:
            return None
        fields = {name: value for name, value in changes.items() if name in _UPDATABLE}
        if fields:
            assignments = ", ".join(f"{name} = ?" for name in fields)
            self._conn.execute(
                f"UPDATE tasks SET {assignments} WHERE id = ?",
                [*(_to_db(value) for value in fields.values()), task_id],
            )
            self._conn.commit()
        return self._fetch(task_id, today)

    def set_done(self, task_id: int, done: bool) -> Task | None:
        today = self._today()
        if done:
            # COALESCE mantém a hora da primeira conclusão se a tarefa já estava feita.
            cursor = self._conn.execute(
                "UPDATE tasks SET done = 1, completed_at = COALESCE(completed_at, ?) WHERE id = ?",
                (self._now_iso(), task_id),
            )
        else:
            cursor = self._conn.execute(
                "UPDATE tasks SET done = 0, completed_at = NULL WHERE id = ?", (task_id,)
            )
        self._conn.commit()
        return self._fetch(task_id, today) if cursor.rowcount else None

    def delete(self, task_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def _today(self) -> date:
        return local_today(self._clock())

    def _now_iso(self) -> str:
        return self._clock().astimezone(timezone.utc).isoformat()

    def _fetch(self, task_id: int, today: date) -> Task | None:
        row = self._conn.execute(f"SELECT {_COLUMNS} FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._to_task(row, today) if row else None

    def _to_task(self, row: sqlite3.Row, today: date) -> Task:
        due = date.fromisoformat(row["due_date"]) if row["due_date"] else None
        done = bool(row["done"])
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=Priority(row["priority"]),
            due_date=due,
            done=done,
            overdue=not done and due is not None and due < today,
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )


def _to_db(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    return value
