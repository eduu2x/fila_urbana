import os
import sqlite3
from contextlib import contextmanager

ESQUEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS demandas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    celula TEXT NOT NULL,
    categoria TEXT NOT NULL,
    gravidade INTEGER NOT NULL DEFAULT 1,
    centroide_latitude REAL NOT NULL,
    centroide_longitude REAL NOT NULL,
    iniciada_em TEXT NOT NULL,
    ultima_ocorrencia TEXT NOT NULL,
    sla_dias INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'aberta',
    resolvida_em TEXT,
    reaberturas INTEGER NOT NULL DEFAULT 0,
    confirmacoes_validas INTEGER NOT NULL DEFAULT 0,
    relatos_count INTEGER NOT NULL DEFAULT 1,
    entornos_json TEXT NOT NULL DEFAULT '[]',
    regiao TEXT NOT NULL DEFAULT 'Não informada',
    score_atual REAL NOT NULL DEFAULT 0.0,
    componentes_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id INTEGER NOT NULL,
    token_cidadao TEXT NOT NULL,
    categoria_escolhida TEXT NOT NULL,
    categoria_sugerida TEXT NOT NULL,
    confianca_classificacao REAL NOT NULL DEFAULT 0.0,
    gravidade INTEGER NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    regiao TEXT NOT NULL DEFAULT 'Não informada',
    entornos_json TEXT NOT NULL DEFAULT '[]',
    criado_em TEXT NOT NULL,
    revisado INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (demanda_id) REFERENCES demandas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS confirmacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id INTEGER NOT NULL,
    token_cidadao TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    dia TEXT NOT NULL,
    distancia_m REAL NOT NULL,
    FOREIGN KEY (demanda_id) REFERENCES demandas(id) ON DELETE CASCADE,
    UNIQUE (demanda_id, token_cidadao, dia)
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id INTEGER NOT NULL,
    status_anterior TEXT,
    status_novo TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    ator TEXT NOT NULL DEFAULT 'sistema',
    FOREIGN KEY (demanda_id) REFERENCES demandas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS historico_score (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demanda_id INTEGER NOT NULL,
    criado_em TEXT NOT NULL,
    score REAL NOT NULL,
    componentes_json TEXT NOT NULL,
    versao_pesos TEXT NOT NULL DEFAULT '1.0',
    FOREIGN KEY (demanda_id) REFERENCES demandas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_demandas_celula ON demandas (celula, categoria, status);
CREATE INDEX IF NOT EXISTS idx_demandas_status ON demandas (status);
CREATE INDEX IF NOT EXISTS idx_demandas_regiao ON demandas (regiao);
CREATE INDEX IF NOT EXISTS idx_relatos_demanda ON relatos (demanda_id);
CREATE INDEX IF NOT EXISTS idx_relatos_revisao ON relatos (revisado, categoria_sugerida, confianca_classificacao);
CREATE INDEX IF NOT EXISTS idx_confirmacoes_demanda ON confirmacoes (demanda_id);
CREATE INDEX IF NOT EXISTS idx_eventos_demanda ON eventos (demanda_id);
CREATE INDEX IF NOT EXISTS idx_historico_demanda ON historico_score (demanda_id);
"""


def caminho_banco():
    return os.environ.get("FILA_URBANA_DB", "data/fila_urbana.db")


def conectar():
    caminho = caminho_banco()
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    conexao = sqlite3.connect(caminho, timeout=10.0)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 5000")
    return conexao


@contextmanager
def abrir_conexao():
    conexao = conectar()
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def iniciar_banco():
    with abrir_conexao() as conexao:
        conexao.executescript(ESQUEMA)
