from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

TITLE_MAX = 120
DESCRIPTION_MAX = 1000


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Status(str, Enum):
    pending = "pending"
    done = "done"


def _clean_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("o título não pode ficar em branco")
    return stripped


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=TITLE_MAX, examples=["Entregar o trabalho de POO"])
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    priority: Priority = Priority.medium
    due_date: date | None = Field(default=None, examples=["2026-10-15"])

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        return _clean_title(value)


class TaskUpdate(BaseModel):
    """Só os campos enviados mudam. `description` e `due_date` aceitam null para apagar."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=TITLE_MAX)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    priority: Priority | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_null_or_blank(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("o título não pode ser nulo")
        return _clean_title(value)

    @field_validator("priority")
    @classmethod
    def priority_not_null(cls, value: Priority | None) -> Priority:
        if value is None:
            raise ValueError("a prioridade não pode ser nula")
        return value


class Task(BaseModel):
    id: int
    title: str
    description: str | None
    priority: Priority
    due_date: date | None
    done: bool
    overdue: bool
    created_at: datetime
    completed_at: datetime | None
