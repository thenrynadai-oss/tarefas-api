"""O único lugar que decide em que dia estamos.

Fuso horário aqui é regra de negócio: "atrasada" significa prazo antes de hoje em São Paulo,
não antes de hoje no relógio do servidor. Nada de offset fixo nem de somar 24 horas: o Brasil
já teve horário de verão, e o banco de fusos (tzdata) conhece essa história.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("America/Sao_Paulo")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_today(now: datetime) -> date:
    if now.tzinfo is None:
        raise ValueError("now precisa ter fuso horário")
    return now.astimezone(BUSINESS_TZ).date()
