import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"

FORBIDDEN = [
    (re.compile(r"timedelta\(\s*hours\s*=\s*-?\s*3\s*\)"), "offset fixo de 3 horas"),
    (re.compile(r"[-+]03:00"), "offset -03:00 escrito à mão"),
    (re.compile(r"86_?400"), "dia somado em segundos"),
    (re.compile(r"timedelta\(\s*(hours\s*=\s*24|days\s*=\s*1)\s*\)"), "dia somado como 24 horas"),
]


def test_day_boundary_never_uses_fixed_offset_or_24h_arithmetic():
    problems = []
    for path in APP_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern, reason in FORBIDDEN:
            if pattern.search(text):
                problems.append(f"{path.name}: {reason}")
    assert problems == [], "O dia tem que vir de app.clock.local_today: " + "; ".join(problems)
