import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

os.environ["FILA_URBANA_TOKEN_GESTOR"] = "gestor"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def banco_temporario(tmp_path, monkeypatch):
    caminho = tmp_path / "fila_urbana_teste.db"
    monkeypatch.setenv("FILA_URBANA_DB", str(caminho))
    monkeypatch.delenv("AUTO_SEED", raising=False)
    return caminho


@pytest.fixture()
def cliente(banco_temporario):
    with TestClient(app) as cliente_teste:
        yield cliente_teste
