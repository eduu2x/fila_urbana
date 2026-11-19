import pytest

from app.config import MAXIMO_CONFIRMACOES

LATITUDE = -23.5505
LONGITUDE = -46.6333
CABECALHO_GESTOR = {"X-Token-Gestor": "gestor"}


def montar_relato(**alteracoes):
    dados = {
        "token_cidadao": "cidadao-1",
        "categoria": "buraco",
        "gravidade": 3,
        "descricao": "Buraco fundo na pista",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "regiao": "Centro",
        "entornos": ["escola"],
    }
    dados.update(alteracoes)
    return dados


def criar(cliente, **alteracoes):
    return cliente.post("/api/relatos", json=montar_relato(**alteracoes))


def criar_identificador(cliente, **alteracoes):
    return criar(cliente, **alteracoes).json()["demanda"]["identificador"]


def test_saude(cliente):
    resposta = cliente.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_categorias(cliente):
    dados = cliente.get("/api/categorias").json()
    assert len(dados["categorias"]) == 6
    assert len(dados["regioes"]) == 5
    assert len(dados["entornos"]) == 4
    assert dados["versao_pesos"] == "1.0"
    assert dados["exige_token_gestor"] is True
    assert dados["centro_mapa"]["latitude"] == pytest.approx(LATITUDE)


def test_criar_relato(cliente):
    resposta = criar(cliente)
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["acao"] == "demanda_criada"
    assert dados["token_cidadao"] == "cidadao-1"
    assert dados["classificacao"]["categoria_sugerida"] == "buraco"
    demanda = dados["demanda"]
    assert demanda["identificador"] > 0
    assert demanda["status"] == "aberta"
    assert demanda["relatos_count"] == 1
    assert demanda["entornos"] == ["escola"]
    assert 0.0 <= demanda["score"] <= 100.0
    assert len(demanda["relatos"]) == 1
    assert len(demanda["eventos"]) == 1
    assert len(demanda["historico"]) == 1


def test_relato_sem_token_gera_token(cliente):
    dados = criar(cliente, token_cidadao=None).json()
    assert len(dados["token_cidadao"]) > 0
    assert dados["demanda"]["relatos"][0].get("token_cidadao") is None


def test_relato_proximo_reaproveita_demanda(cliente):
    primeira = criar_identificador(cliente)
    segunda = criar(
        cliente,
        token_cidadao="cidadao-2",
        gravidade=5,
        entornos=["hospital"],
        latitude=LATITUDE + 0.0002,
        longitude=LONGITUDE + 0.0002,
    ).json()
    assert segunda["acao"] == "relato_adicionado"
    assert segunda["demanda"]["identificador"] == primeira
    assert segunda["demanda"]["relatos_count"] == 2
    assert segunda["demanda"]["gravidade"] == 5
    assert segunda["demanda"]["entornos"] == ["escola", "hospital"]


def test_categoria_diferente_cria_outra_demanda(cliente):
    primeira = criar_identificador(cliente)
    segunda = criar(
        cliente,
        categoria="iluminacao",
        descricao="Poste apagado",
    ).json()
    assert segunda["acao"] == "demanda_criada"
    assert segunda["demanda"]["identificador"] != primeira


def test_relato_distante_cria_outra_demanda(cliente):
    primeira = criar_identificador(cliente)
    segunda = criar(
        cliente,
        latitude=LATITUDE + 0.002,
    ).json()
    assert segunda["acao"] == "demanda_criada"
    assert segunda["demanda"]["identificador"] != primeira


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"latitude": 999.0},
        {"longitude": 999.0},
        {"gravidade": 0},
        {"gravidade": 6},
        {"descricao": "x" * 501},
    ],
)
def test_entrada_invalida(cliente, alteracoes):
    assert criar(cliente, **alteracoes).status_code == 422


def test_coordenada_fora_da_area_piloto(cliente):
    resposta = criar(cliente, latitude=0.0, longitude=0.0)
    assert resposta.status_code == 400
    assert "área piloto" in resposta.json()["detail"]


def test_categoria_invalida(cliente):
    assert criar(cliente, categoria="inundacao").status_code == 400


def test_regiao_invalida(cliente):
    assert criar(cliente, regiao="Zona Central").status_code == 400


def test_confirmacao(cliente):
    identificador = criar_identificador(cliente)
    resposta = cliente.post(
        f"/api/demandas/{identificador}/confirmacoes",
        json={
            "token_cidadao": "confirma-1",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
    )
    assert resposta.status_code == 200
    assert resposta.json()["demanda"]["confirmacoes_validas"] == 1


def test_confirmacao_repetida_no_dia(cliente):
    identificador = criar_identificador(cliente)
    corpo = {
        "token_cidadao": "confirma-1",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
    }
    assert cliente.post(
        f"/api/demandas/{identificador}/confirmacoes",
        json=corpo,
    ).status_code == 200
    assert cliente.post(
        f"/api/demandas/{identificador}/confirmacoes",
        json=corpo,
    ).status_code == 409


def test_confirmacao_fora_do_raio(cliente):
    identificador = criar_identificador(cliente)
    resposta = cliente.post(
        f"/api/demandas/{identificador}/confirmacoes",
        json={
            "token_cidadao": "confirma-1",
            "latitude": LATITUDE + 0.01,
            "longitude": LONGITUDE,
        },
    )
    assert resposta.status_code == 400
    assert "raio" in resposta.json()["detail"]


def test_confirmacao_em_demanda_inexistente(cliente):
    resposta = cliente.post(
        "/api/demandas/999999/confirmacoes",
        json={
            "token_cidadao": "confirma-1",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
    )
    assert resposta.status_code == 404


def test_limite_de_confirmacoes(cliente):
    identificador = criar_identificador(cliente)
    for indice in range(MAXIMO_CONFIRMACOES):
        resposta = cliente.post(
            f"/api/demandas/{identificador}/confirmacoes",
            json={
                "token_cidadao": f"confirma-{indice}",
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
            },
        )
        assert resposta.status_code == 200
    excedente = cliente.post(
        f"/api/demandas/{identificador}/confirmacoes",
        json={
            "token_cidadao": "confirma-excedente",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
    )
    assert excedente.status_code == 409


def test_status_exige_token(cliente):
    identificador = criar_identificador(cliente)
    corpo = {"status": "em_analise"}
    assert cliente.patch(
        f"/api/demandas/{identificador}/status",
        json=corpo,
    ).status_code == 401
    assert cliente.patch(
        f"/api/demandas/{identificador}/status",
        json=corpo,
        headers={"X-Token-Gestor": ""},
    ).status_code == 401
    assert cliente.patch(
        f"/api/demandas/{identificador}/status",
        json=corpo,
        headers={"X-Token-Gestor": "errado"},
    ).status_code == 401


def test_token_configurado_vazio_bloqueia(monkeypatch):
    from fastapi import HTTPException

    import app.main as modulo

    monkeypatch.setattr(modulo, "TOKEN_GESTOR", "")
    with pytest.raises(HTTPException):
        modulo.verificar_gestor("")


def test_fluxo_de_status(cliente):
    identificador = criar_identificador(cliente)
    caminho = f"/api/demandas/{identificador}/status"
    resposta = cliente.patch(
        caminho,
        json={"status": "em_analise"},
        headers=CABECALHO_GESTOR,
    )
    assert resposta.status_code == 200
    assert resposta.json()["demanda"]["status"] == "em_analise"
    assert cliente.patch(
        caminho,
        json={"status": "em_execucao"},
        headers=CABECALHO_GESTOR,
    ).status_code == 200
    resolvida = cliente.patch(
        caminho,
        json={"status": "resolvida"},
        headers=CABECALHO_GESTOR,
    )
    assert resolvida.status_code == 200
    assert resolvida.json()["demanda"]["resolvida_em"] is not None
    confirmacao = cliente.post(
        f"/api/demandas/{identificador}/confirmacoes",
        json={
            "token_cidadao": "confirma-1",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
    )
    assert confirmacao.status_code == 400
    reaberta = cliente.patch(
        caminho,
        json={"status": "aberta"},
        headers=CABECALHO_GESTOR,
    )
    assert reaberta.status_code == 200
    assert reaberta.json()["demanda"]["reaberturas"] == 1
    assert reaberta.json()["demanda"]["resolvida_em"] is None


def test_transicoes_invalidas_de_status(cliente):
    identificador = criar_identificador(cliente)
    caminho = f"/api/demandas/{identificador}/status"
    assert cliente.patch(
        caminho,
        json={"status": "em_execucao"},
        headers=CABECALHO_GESTOR,
    ).status_code == 400
    assert cliente.patch(
        caminho,
        json={"status": "aberta"},
        headers=CABECALHO_GESTOR,
    ).status_code == 400
    assert cliente.patch(
        caminho,
        json={"status": "arquivada"},
        headers=CABECALHO_GESTOR,
    ).status_code == 400
    assert cliente.patch(
        "/api/demandas/999999/status",
        json={"status": "em_analise"},
        headers=CABECALHO_GESTOR,
    ).status_code == 404


def test_listagem_filtros_e_paginacao(cliente):
    criar(cliente, categoria="buraco", descricao="Buraco na pista")
    criar(
        cliente,
        categoria="lixo",
        descricao="Lixo na calçada",
        latitude=LATITUDE + 0.01,
    )
    criar(
        cliente,
        categoria="iluminacao",
        descricao="Poste apagado",
        latitude=LATITUDE + 0.02,
    )
    todas = cliente.get("/api/demandas?status=todas").json()
    assert todas["total"] == 3
    assert len(todas["itens"]) == 3
    pagina = cliente.get("/api/demandas?limite=2").json()
    assert pagina["total"] == 3
    assert len(pagina["itens"]) == 2
    segunda_pagina = cliente.get(
        "/api/demandas?limite=2&deslocamento=2"
    ).json()
    assert len(segunda_pagina["itens"]) == 1
    por_categoria = cliente.get("/api/demandas?categoria=lixo").json()
    assert por_categoria["total"] == 1
    por_regiao = cliente.get("/api/demandas?regiao=Centro").json()
    assert por_regiao["total"] == 3


def test_listagem_parametros_invalidos(cliente):
    assert cliente.get("/api/demandas?status=arquivada").status_code == 400
    assert cliente.get("/api/demandas?categoria=xyz").status_code == 400
    assert cliente.get("/api/demandas?regiao=xyz").status_code == 400


def test_top_ordenado_e_limitado(cliente):
    criar(cliente, gravidade=1)
    criar(cliente, gravidade=5, latitude=LATITUDE + 0.01)
    criar(cliente, gravidade=3, latitude=LATITUDE + 0.02)
    top = cliente.get("/api/demandas/top?limite=2").json()
    assert top["total"] == 3
    assert len(top["itens"]) == 2
    pontuacoes = [item["score"] for item in top["itens"]]
    assert pontuacoes == sorted(pontuacoes, reverse=True)
    todos = cliente.get("/api/demandas/top?limite=10").json()["itens"]
    assert len(todos) == 3
    assert todos[0]["gravidade"] == 5
    assert all(item["status"] != "resolvida" for item in todos)


def test_detalhe(cliente):
    criado = criar(cliente).json()
    identificador = criado["demanda"]["identificador"]
    dados = cliente.get(f"/api/demandas/{identificador}").json()
    assert dados["identificador"] == identificador
    assert len(dados["relatos"]) == 1
    assert "token_cidadao" not in dados["relatos"][0]
    assert len(dados["eventos"]) == 1
    assert len(dados["historico"]) == 1
    assert cliente.get("/api/demandas/999999").status_code == 404


def test_mapa(cliente):
    identificador = criar_identificador(cliente)
    dados = cliente.get("/api/mapa").json()
    assert dados["total"] == 1
    item = dados["itens"][0]
    assert item["identificador"] == identificador
    assert item["latitude"] == pytest.approx(LATITUDE, abs=0.001)
    assert item["longitude"] == pytest.approx(LONGITUDE, abs=0.001)
    filtrado = cliente.get(
        "/api/mapa",
        params={
            "oeste": LONGITUDE - 0.01,
            "sul": LATITUDE - 0.01,
            "leste": LONGITUDE + 0.01,
            "norte": LATITUDE + 0.01,
        },
    ).json()
    assert filtrado["total"] == 1
    vazio = cliente.get(
        "/api/mapa",
        params={
            "oeste": LONGITUDE + 1.0,
            "sul": LATITUDE + 1.0,
            "leste": LONGITUDE + 2.0,
            "norte": LATITUDE + 2.0,
        },
    ).json()
    assert vazio["total"] == 0


def test_mapa_bbox_invalida(cliente):
    assert cliente.get(
        "/api/mapa",
        params={
            "oeste": LONGITUDE + 1.0,
            "sul": LATITUDE,
            "leste": LONGITUDE,
            "norte": LATITUDE + 1.0,
        },
    ).status_code == 400
    assert cliente.get(
        "/api/mapa",
        params={"oeste": LONGITUDE},
    ).status_code == 400
    assert cliente.get(
        "/api/mapa",
        params={
            "oeste": -200.0,
            "sul": LATITUDE,
            "leste": LONGITUDE,
            "norte": LATITUDE + 1.0,
        },
    ).status_code == 400


def test_agenda(cliente):
    identificador = criar_identificador(cliente)
    dados = cliente.get("/api/agenda?dias=30").json()
    assert dados["dias"] == 30
    assert dados["total"] == 1
    assert dados["total_atrasadas"] == 0
    assert dados["atrasadas"] == []
    assert len(dados["proximas"]) == 1
    assert dados["proximas"][0]["identificador"] == identificador
    assert dados["alem_do_periodo"] == 0


def test_garantia(cliente):
    criar(cliente)
    dados = cliente.get("/api/garantia").json()
    assert dados["total"] == 0
    assert dados["itens"] == []


def test_estatisticas(cliente):
    criar(cliente)
    criar(
        cliente,
        categoria="lixo",
        descricao="Lixo na calçada",
        latitude=LATITUDE + 0.01,
    )
    dados = cliente.get("/api/estatisticas").json()
    assert dados["total_demandas"] == 2
    assert dados["demandas_abertas"] == 2
    assert dados["demandas_resolvidas"] == 0
    assert dados["total_relatos"] == 2
    assert dados["total_confirmacoes"] == 0
    assert sum(item["total"] for item in dados["por_categoria"]) == 2
    assert sum(item["total"] for item in dados["por_regiao"]) == 2


def test_revisoes(cliente):
    criado = criar(
        cliente,
        descricao="Problema urbano sem palavra chave",
    ).json()
    relato_id = criado["demanda"]["relatos"][0]["id"]
    dados = cliente.get("/api/revisoes").json()
    assert dados["total"] == 1
    item = dados["itens"][0]
    assert item["id"] == relato_id
    assert item["categoria_sugerida"] == "outros"
    assert item["confianca_classificacao"] == 0.0
    assert cliente.post(
        f"/api/revisoes/{relato_id}/concluir"
    ).status_code == 401
    assert cliente.post(
        f"/api/revisoes/{relato_id}/concluir",
        headers=CABECALHO_GESTOR,
    ).status_code == 200
    assert cliente.get("/api/revisoes").json()["total"] == 0
    assert cliente.post(
        "/api/revisoes/999999/concluir",
        headers=CABECALHO_GESTOR,
    ).status_code == 404


def test_simulacao(cliente):
    criar(cliente, gravidade=5)
    criar(
        cliente,
        categoria="lixo",
        descricao="Lixo na calçada",
        latitude=LATITUDE + 0.01,
    )
    resposta = cliente.post(
        "/api/simulacao",
        json={"pesos": {"gravidade": 3, "risco": 1}},
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["pesos"]["gravidade"] == pytest.approx(0.75)
    assert dados["pesos"]["risco"] == pytest.approx(0.25)
    assert sum(dados["pesos"].values()) == pytest.approx(1.0)
    assert len(dados["itens"]) == 2
    assert dados["itens"][0]["gravidade"] == 5


def test_pagina_inicial(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert "Fila Urbana" in resposta.text


def test_arquivos_estaticos(cliente):
    estilo = cliente.get("/static/estilo.css")
    aplicacao = cliente.get("/static/app.js")
    icone = cliente.get("/static/favicon.svg")
    assert estilo.status_code == 200
    assert "text/css" in estilo.headers["content-type"]
    assert aplicacao.status_code == 200
    assert "javascript" in aplicacao.headers["content-type"]
    assert icone.status_code == 200
    assert "image/svg+xml" in icone.headers["content-type"]


def test_favicon(cliente):
    resposta = cliente.get("/favicon.ico")
    assert resposta.status_code == 200
    assert "image/svg+xml" in resposta.headers["content-type"]
