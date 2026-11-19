import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.banco import iniciar_banco
from app.config import TOKEN_GESTOR
from app.modelos import (
    ConfirmacaoEntrada,
    RelatoEntrada,
    SimulacaoEntrada,
    StatusEntrada,
)
from app.semeador import semear_se_vazio
from app.servicos import (
    concluir_revisao,
    confirmar,
    criar_relato,
    listar_agenda,
    listar_demandas,
    listar_garantia,
    listar_mapa,
    listar_revisoes,
    listar_top,
    mudar_status,
    obter_categorias,
    obter_demanda,
    obter_estatisticas,
    simular,
)

PASTA_STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(aplicacao):
    iniciar_banco()
    if os.environ.get("AUTO_SEED", "").strip().lower() in (
        "1",
        "true",
        "sim",
    ):
        semear_se_vazio()
    yield


app = FastAPI(
    title="Fila Urbana",
    description="Mapa colaborativo de problemas urbanos com fila de prioridade.",
    version="0.1.0",
    lifespan=lifespan,
)


def verificar_gestor(x_token_gestor: str = Header(default="")):
    if x_token_gestor != TOKEN_GESTOR:
        raise HTTPException(
            status_code=401,
            detail="Token de gestor inválido.",
        )


@app.get("/api/saude")
def saude():
    return {"status": "ok", "versao": "0.1.0"}


@app.get("/api/categorias")
def categorias():
    return obter_categorias()


@app.post("/api/relatos")
def post_relato(dados: RelatoEntrada):
    return criar_relato(dados)


@app.get("/api/demandas")
def get_demandas(
    status: str | None = None,
    categoria: str | None = None,
    regiao: str | None = None,
    limite: int = 50,
    deslocamento: int = 0,
):
    return listar_demandas(
        status=status,
        categoria=categoria,
        regiao=regiao,
        limite=limite,
        deslocamento=deslocamento,
    )


@app.get("/api/demandas/top")
def get_top(limite: int = 10, regiao: str | None = None):
    return listar_top(limite=limite, regiao=regiao)


@app.get("/api/demandas/{identificador}")
def get_demanda(identificador: int):
    return obter_demanda(identificador)


@app.post("/api/demandas/{identificador}/confirmacoes")
def post_confirmacao(
    identificador: int,
    dados: ConfirmacaoEntrada,
):
    return confirmar(identificador, dados)


@app.patch(
    "/api/demandas/{identificador}/status",
    dependencies=[Depends(verificar_gestor)],
)
def patch_status(
    identificador: int,
    dados: StatusEntrada,
):
    return mudar_status(identificador, dados)


@app.get("/api/mapa")
def get_mapa(
    limite: int = 500,
    oeste: float | None = None,
    sul: float | None = None,
    leste: float | None = None,
    norte: float | None = None,
):
    return listar_mapa(
        limite=limite,
        oeste=oeste,
        sul=sul,
        leste=leste,
        norte=norte,
    )


@app.get("/api/agenda")
def get_agenda(dias: int = 7, limite: int = 50):
    return listar_agenda(dias=dias, limite=limite)


@app.get("/api/garantia")
def get_garantia(limite: int = 50):
    return listar_garantia(limite=limite)


@app.get("/api/estatisticas")
def get_estatisticas():
    return obter_estatisticas()


@app.get("/api/revisoes")
def get_revisoes(limite: int = 100):
    return listar_revisoes(limite=limite)


@app.post(
    "/api/revisoes/{identificador}/concluir",
    dependencies=[Depends(verificar_gestor)],
)
def post_concluir_revisao(identificador: int):
    return concluir_revisao(identificador)


@app.post("/api/simulacao")
def post_simulacao(dados: SimulacaoEntrada):
    return simular(dados.pesos)


@app.get("/")
def raiz():
    return FileResponse(PASTA_STATIC / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def icone():
    return FileResponse(
        PASTA_STATIC / "favicon.svg",
        media_type="image/svg+xml",
    )


app.mount(
    "/static",
    StaticFiles(directory=str(PASTA_STATIC)),
    name="static",
)
