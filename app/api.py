from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response

from app.clock import utc_now
from app.database import connect, init_schema
from app.repository import TaskRepository
from app.schemas import Priority, Status, Task, TaskCreate, TaskUpdate

DESCRIPTION = """
API de lista de tarefas: crie, liste com filtros, edite, conclua e exclua.

- **Prioridade:** `low`, `medium` (padrão) ou `high`.
- **Prazo:** data no formato `AAAA-MM-DD`.
- **Atrasada** (`overdue`): tarefa pendente com prazo antes de hoje **no horário de São Paulo**.

A lista vem com as pendentes primeiro, depois por prazo (sem prazo por último) e por prioridade.
"""

TAG = "tarefas"


def create_app(db_path: str, clock: Callable[[], datetime] = utc_now) -> FastAPI:
    with closing(connect(db_path)) as conn:
        init_schema(conn)

    app = FastAPI(title="Tarefas API", version="1.0.0", description=DESCRIPTION)

    def get_repository() -> Iterator[TaskRepository]:
        conn = connect(db_path)
        try:
            yield TaskRepository(conn, clock)
        finally:
            conn.close()

    Repo = Annotated[TaskRepository, Depends(get_repository)]

    @app.post("/tasks", status_code=201, summary="Criar tarefa", tags=[TAG])
    def create_task(data: TaskCreate, repo: Repo) -> Task:
        return repo.create(data)

    @app.get("/tasks", summary="Listar tarefas", tags=[TAG])
    def list_tasks(
        repo: Repo,
        status: Annotated[Status | None, Query(description="`pending` ou `done`")] = None,
        priority: Annotated[Priority | None, Query(description="`low`, `medium` ou `high`")] = None,
        due_until: Annotated[date | None, Query(description="Só tarefas com prazo até esta data")] = None,
        overdue: Annotated[bool | None, Query(description="`true` para só as atrasadas")] = None,
    ) -> list[Task]:
        return repo.search(status=status, priority=priority, due_until=due_until, overdue=overdue)

    @app.get("/tasks/{task_id}", summary="Ver uma tarefa", tags=[TAG])
    def get_task(task_id: int, repo: Repo) -> Task:
        return _found(repo.get(task_id), task_id)

    @app.patch("/tasks/{task_id}", summary="Editar tarefa (só os campos enviados)", tags=[TAG])
    def update_task(task_id: int, changes: TaskUpdate, repo: Repo) -> Task:
        return _found(repo.update(task_id, changes.model_dump(exclude_unset=True)), task_id)

    @app.post("/tasks/{task_id}/complete", summary="Concluir tarefa", tags=[TAG])
    def complete_task(task_id: int, repo: Repo) -> Task:
        return _found(repo.set_done(task_id, True), task_id)

    @app.post("/tasks/{task_id}/reopen", summary="Reabrir tarefa", tags=[TAG])
    def reopen_task(task_id: int, repo: Repo) -> Task:
        return _found(repo.set_done(task_id, False), task_id)

    @app.delete("/tasks/{task_id}", status_code=204, response_class=Response, summary="Excluir tarefa", tags=[TAG])
    def delete_task(task_id: int, repo: Repo) -> None:
        if not repo.delete(task_id):
            raise _not_found(task_id)

    return app


def _not_found(task_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Tarefa {task_id} não encontrada.")


def _found(task: Task | None, task_id: int) -> Task:
    if task is None:
        raise _not_found(task_id)
    return task
