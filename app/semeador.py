import json
import random
from datetime import timedelta

from app.banco import abrir_conexao, iniciar_banco
from app.classificacao import classificar_descricao
from app.config import CATEGORIAS, REGIOES, RISCOS_ENTORNO
from app.servicos import _atualizar_pontuacao_demanda
from app.utilidades import (
    agora_utc,
    calcular_celula,
    distancia_metros,
    para_iso,
)

DESCRICOES = {
    "buraco": [
        "Buraco fundo na pista",
        "Cratera no asfalto",
        "Remendo solto na via",
    ],
    "iluminacao": [
        "Poste apagado deixa rua escura",
        "Lâmpada queimada na praça",
        "Falta iluminação na viela",
    ],
    "lixo": [
        "Descarte irregular de lixo na calçada",
        "Entulho jogado no terreno",
        "Coleta não passou e lixo acumulou",
    ],
    "sinalizacao": [
        "Placa de sinalização caída",
        "Semáforo apagado no cruzamento",
        "Faixa de pedestre apagada",
    ],
    "drenagem": [
        "Alagamento após a chuva",
        "Bueiro entupido e água parada",
        "Vazamento de esgoto na rua",
    ],
    "outros": [
        "Problema urbano observado no local",
        "Ocorrência sem categoria definida",
    ],
}

CENTROS_REGIOES = {
    "Centro": (-23.5505, -46.6333),
    "Zona Norte": (-23.5010, -46.6250),
    "Zona Sul": (-23.6100, -46.6400),
    "Zona Leste": (-23.5450, -46.5400),
    "Zona Oeste": (-23.5550, -46.7200),
}

CATEGORIAS_SORTEIO = [
    ("buraco", 30),
    ("iluminacao", 20),
    ("lixo", 20),
    ("sinalizacao", 15),
    ("drenagem", 10),
    ("outros", 5),
]


def _gerar_ponto(randomizador, centro, pontos_usados):
    latitude = centro[0]
    longitude = centro[1]
    for _ in range(30):
        latitude = centro[0] + randomizador.uniform(-0.018, 0.018)
        longitude = centro[1] + randomizador.uniform(-0.018, 0.018)
        if all(
            distancia_metros(
                latitude,
                longitude,
                usado[0],
                usado[1],
            ) > 60.0
            for usado in pontos_usados
        ):
            return latitude, longitude
    return latitude, longitude


def _sortear_status(randomizador):
    sorteio = randomizador.random()
    if sorteio < 0.72:
        return "aberta"
    if sorteio < 0.82:
        return "em_analise"
    if sorteio < 0.90:
        return "em_execucao"
    return "resolvida"


def _inserir_evento(conexao, demanda_id, anterior, novo, momento, ator):
    conexao.execute(
        """
        INSERT INTO eventos (
            demanda_id, status_anterior, status_novo, criado_em, ator
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (demanda_id, anterior, novo, momento, ator),
    )


def _inserir_demanda_completa(
    conexao,
    agora,
    randomizador,
    categoria,
    gravidade,
    latitude,
    longitude,
    regiao,
    idade_dias,
    status,
    confirmacoes,
    relatos_count,
    entornos,
    reaberturas,
    hora_inicial=0,
    descricao_forcada=None,
):
    iniciada_em = agora - timedelta(days=idade_dias, hours=hora_inicial)
    ultima_ocorrencia = agora - timedelta(
        days=randomizador.randint(0, idade_dias)
    )
    resolvida_em = None
    if status == "resolvida":
        dias_resolucao = randomizador.randint(0, max(0, idade_dias // 2))
        resolvida_em = agora - timedelta(days=dias_resolucao)
    sla_dias = CATEGORIAS[categoria]["sla_dias"]
    celula = calcular_celula(latitude, longitude, categoria)
    cursor = conexao.execute(
        """
        INSERT INTO demandas (
            celula, categoria, gravidade, centroide_latitude,
            centroide_longitude, iniciada_em, ultima_ocorrencia,
            sla_dias, status, resolvida_em, reaberturas,
            confirmacoes_validas, relatos_count, entornos_json,
            regiao, score_atual, componentes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, '{}')
        """,
        (
            celula,
            categoria,
            gravidade,
            latitude,
            longitude,
            para_iso(iniciada_em),
            para_iso(ultima_ocorrencia),
            sla_dias,
            status,
            para_iso(resolvida_em) if resolvida_em is not None else None,
            reaberturas,
            confirmacoes,
            relatos_count,
            json.dumps(entornos, ensure_ascii=False),
            regiao,
        ),
    )
    demanda_id = cursor.lastrowid
    intervalo = max(
        0.0,
        (ultima_ocorrencia - iniciada_em).total_seconds(),
    )
    for indice in range(relatos_count):
        descricao = descricao_forcada or randomizador.choice(
            DESCRICOES[categoria]
        )
        categoria_sugerida, confianca = classificar_descricao(descricao)
        momento = iniciada_em + timedelta(
            seconds=randomizador.uniform(0.0, intervalo)
        )
        latitude_relato = latitude + randomizador.uniform(-0.0003, 0.0003)
        longitude_relato = longitude + randomizador.uniform(-0.0003, 0.0003)
        conexao.execute(
            """
            INSERT INTO relatos (
                demanda_id, token_cidadao, categoria_escolhida,
                categoria_sugerida, confianca_classificacao, gravidade,
                descricao, latitude, longitude, regiao, entornos_json,
                criado_em, revisado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                demanda_id,
                f"seed-relato-{demanda_id}-{indice}",
                categoria,
                categoria_sugerida,
                confianca,
                gravidade,
                descricao,
                latitude_relato,
                longitude_relato,
                regiao,
                json.dumps(entornos, ensure_ascii=False),
                para_iso(momento),
            ),
        )
    for indice in range(confirmacoes):
        dias_atras = randomizador.randint(0, min(28, max(0, idade_dias)))
        momento = agora - timedelta(
            days=dias_atras,
            hours=randomizador.randint(0, 23),
        )
        conexao.execute(
            """
            INSERT INTO confirmacoes (
                demanda_id, token_cidadao, criado_em, dia, distancia_m
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                demanda_id,
                f"seed-confirmacao-{demanda_id}-{indice}",
                para_iso(momento),
                momento.date().isoformat(),
                randomizador.uniform(0.0, 150.0),
            ),
        )
    _inserir_evento(
        conexao,
        demanda_id,
        None,
        "aberta",
        para_iso(iniciada_em),
        "seed",
    )
    if status != "aberta":
        momento_status = resolvida_em or ultima_ocorrencia
        _inserir_evento(
            conexao,
            demanda_id,
            "aberta",
            status,
            para_iso(momento_status),
            "seed",
        )
    return demanda_id


def _gerar_dados(conexao, agora):
    randomizador = random.Random(20261118)
    pontos_usados = []
    identificadores = []
    for _ in range(180):
        categoria = randomizador.choices(
            [item[0] for item in CATEGORIAS_SORTEIO],
            weights=[item[1] for item in CATEGORIAS_SORTEIO],
            k=1,
        )[0]
        regiao = randomizador.choice(REGIOES)
        centro = CENTROS_REGIOES[regiao]
        latitude, longitude = _gerar_ponto(
            randomizador,
            centro,
            pontos_usados,
        )
        idade_dias = randomizador.randint(0, 75)
        if categoria == "lixo" and randomizador.random() < 0.20:
            idade_dias = randomizador.randint(15, 40)
        status = _sortear_status(randomizador)
        limite_confirmacoes = 20 if idade_dias > 5 else 5
        confirmacoes = randomizador.randint(0, limite_confirmacoes)
        relatos_count = randomizador.randint(1, 4)
        entornos = randomizador.sample(
            list(RISCOS_ENTORNO.keys()),
            randomizador.randint(0, 3),
        )
        reaberturas = (
            0 if status == "resolvida" else randomizador.randint(0, 2)
        )
        gravidade = randomizador.randint(1, 5)
        if categoria in ("buraco", "drenagem") and randomizador.random() < 0.30:
            gravidade = max(gravidade, 4)
        descricao_forcada = None
        if randomizador.random() < 0.10:
            descricao_forcada = "Problema urbano observado no local"
        demanda_id = _inserir_demanda_completa(
            conexao,
            agora,
            randomizador,
            categoria,
            gravidade,
            latitude,
            longitude,
            regiao,
            idade_dias,
            status,
            confirmacoes,
            relatos_count,
            entornos,
            reaberturas,
            hora_inicial=randomizador.randint(0, 23),
            descricao_forcada=descricao_forcada,
        )
        identificadores.append(demanda_id)
        pontos_usados.append((latitude, longitude))
    casos = [
        (
            "lixo",
            2,
            -23.4600,
            -46.5800,
            "Centro",
            30,
            "aberta",
            0,
            1,
            [],
            0,
            "Lixo acumulado na calçada",
        ),
        (
            "lixo",
            2,
            -23.6400,
            -46.5000,
            "Zona Sul",
            30,
            "aberta",
            0,
            1,
            [],
            0,
            "Lixo acumulado na calçada",
        ),
        (
            "lixo",
            2,
            -23.5200,
            -46.7500,
            "Zona Oeste",
            30,
            "aberta",
            0,
            1,
            [],
            0,
            "Lixo acumulado na calçada",
        ),
        (
            "sinalizacao",
            3,
            -23.4700,
            -46.6800,
            "Zona Oeste",
            20,
            "aberta",
            0,
            1,
            [],
            0,
            "Placa de sinalização caída",
        ),
        (
            "sinalizacao",
            3,
            -23.6600,
            -46.5900,
            "Zona Sul",
            20,
            "aberta",
            0,
            1,
            [],
            0,
            "Placa de sinalização caída",
        ),
    ]
    for caso in casos:
        demanda_id = _inserir_demanda_completa(
            conexao,
            agora,
            randomizador,
            caso[0],
            caso[1],
            caso[2],
            caso[3],
            caso[4],
            caso[5],
            caso[6],
            caso[7],
            caso[8],
            caso[9],
            caso[10],
            hora_inicial=0,
            descricao_forcada=caso[11],
        )
        identificadores.append(demanda_id)
    for demanda_id in identificadores:
        _atualizar_pontuacao_demanda(conexao, demanda_id, agora)


def semear_banco(limpar=False):
    iniciar_banco()
    with abrir_conexao() as conexao:
        if limpar:
            conexao.execute("DELETE FROM historico_score")
            conexao.execute("DELETE FROM eventos")
            conexao.execute("DELETE FROM confirmacoes")
            conexao.execute("DELETE FROM relatos")
            conexao.execute("DELETE FROM demandas")
            conexao.execute("DELETE FROM sqlite_sequence")
        total = conexao.execute(
            "SELECT COUNT(*) AS total FROM demandas"
        ).fetchone()["total"]
        if total > 0:
            return {
                "mensagem": "Banco já possui dados.",
                "total_demandas": total,
            }
        agora = agora_utc()
        _gerar_dados(conexao, agora)
        total_demandas = conexao.execute(
            "SELECT COUNT(*) AS total FROM demandas"
        ).fetchone()["total"]
        total_relatos = conexao.execute(
            "SELECT COUNT(*) AS total FROM relatos"
        ).fetchone()["total"]
    return {
        "mensagem": "Dados semeados.",
        "total_demandas": total_demandas,
        "total_relatos": total_relatos,
    }


def semear_se_vazio():
    return semear_banco(limpar=False)
