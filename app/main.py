"""Ponto de entrada do servidor: uvicorn app.main:app --reload"""

import os

from app.api import create_app

app = create_app(os.environ.get("TAREFAS_DB", "tarefas.db"))
