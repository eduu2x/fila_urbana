import json
import uuid
from datetime import timedelta

from fastapi import HTTPException

from app.banco import abrir_conexao
from app.classificacao import classificar_descricao
from app.config import (
    CATEGORIAS,
    CENTRO_MAPA,
    JANELA_DEDUPLICACAO_DIAS,
    JANELA_RECORRENCIA_DIAS,
    LIMIAR_CONFIANCA,
    MAXIMO_CONFIRMACOES,
    NOMES_ENTORNOS,
    PALAVRAS_CHAVE,
    PESOS_PADRAO,
    RAIO_CONFIRMACAO_METROS,
    RAIO_DEDUPLICACAO_METROS,
    RAIO_PILOTO_KM,
    REGIOES,
    RISCOS_ENTORNO,
    STATUS_VALIDOS,
    TRANSICOES_STATUS,
    VERSAO_PESOS,
)
from app.estruturas import Fila, FilaPrioridade, busca_binaria, ordenar_por_intercalacao
from app.prioridade import calcular_componentes, normalizar_pesos
from app.utilidades import (
    adicionar_dias,
    agora_utc,
    calcular_celula,
    celulas_vizinhas,
    de_iso,
    dias_desde,
    distancia_metros,
    para_iso,
)


def _json_lista(texto):
    try:
        valor = json.loads(texto or "[]")
        if isinstance(valor, list):
            return valor
    except json.JSONDecodeError:
        return []
    return []


def _json_dicionario(texto):
    try:
        valor = json.loads(texto or "{}")
        if isinstance(valor, dict):
            return valor
    except json.JSONDecodeError:
        return {}
    return {}


def _validar_coordenada(latitude, longitude):
    distancia = distancia_metros(
        latitude,
        longitude,
        CENTRO_MAPA[0],
        CENTRO_MAPA[1],
    )
    if distancia > RAIO_PILOTO_KM * 1000.0:
        raise HTTPException(
            status_code=400,
            detail="Coordenada fora da área piloto.",
        )


def _contar_recorrencia(conexao, celula, agora):
    limite = para_iso(agora - timedelta(days=JANELA_RECORRENCIA_DIAS))
    linha = conexao.execute(
        """
        SELECT COUNT(*) AS total, COALESCE(SUM(reaberturas), 0) AS reaberturas
        FROM demandas
        WHERE celula = ? AND iniciada_em >= ?
        """,
        (celula, limite),
    ).fetchone()
    return int(linha["total"]) + int(linha["reaberturas"])


def _linha_para_demanda(linha, agora, contagens, pesos=None):
    categoria = linha["categoria"]
    dados_categoria = CATEGORIAS.get(categoria, CATEGORIAS["outros"])
    entornos = _json_lista(linha["entornos_json"])
    ocorrencias = contagens.get(linha["celula"], 1)
    demanda_base = {
        "gravidade": linha["gravidade"],
        "categoria": categoria,
        "sla_dias": linha["sla_dias"],
        "iniciada_em": linha["iniciada_em"],
        "confirmacoes_validas": linha["confirmacoes_validas"],
        "ocorrencias_90_dias": ocorrencias,
        "entornos": entornos,
    }
    pontuacao, componentes = calcular_componentes(demanda_base, agora, pesos)
    prazo = adicionar_dias(linha["iniciada_em"], linha["sla_dias"])
    dias_em_aberto = dias_desde(linha["iniciada_em"], agora)
    atrasada = linha["status"] != "resolvida" and de_iso(prazo) < agora
    return {
        "identificador": linha["id"],
        "categoria": categoria,
        "nome_categoria": dados_categoria["nome"],
        "gravidade": linha["gravidade"],
        "centroide_latitude": round(linha["centroide_latitude"], 3),
        "centroide_longitude": round(linha["centroide_longitude"], 3),
        "iniciada_em": linha["iniciada_em"],
        "ultima_ocorrencia": linha["ultima_ocorrencia"],
        "sla_dias": linha["sla_dias"],
        "prazo": prazo,
        "status": linha["status"],
        "resolvida_em": linha["resolvida_em"],
        "reaberturas": linha["reaberturas"],
        "confirmacoes_validas": linha["confirmacoes_validas"],
        "relatos_count": linha["relatos_count"],
        "entornos": entornos,
        "regiao": linha["regiao"],
        "score": pontuacao,
        "componentes": {
            nome: round(valor, 4) for nome, valor in componentes.items()
        },
        "dias_em_aberto": round(dias_em_aberto, 1),
        "atrasada": atrasada,
    }


def _carregar_demandas(conexao, status=None, pesos=None):
    if status is None:
        linhas = conexao.execute(
            "SELECT * FROM demandas WHERE status != 'resolvida' ORDER BY id DESC"
        ).fetchall()
    elif status == "todas":
        linhas = conexao.execute(
            "SELECT * FROM demandas ORDER BY id DESC"
        ).fetchall()
    else:
        linhas = conexao.execute(
            "SELECT * FROM demandas WHERE status = ? ORDER BY id DESC",
            (status,),
        ).fetchall()
    agora = agora_utc()
    limite = agora - timedelta(days=JANELA_RECORRENCIA_DIAS)
    contagens = {}
    for linha in linhas:
        if de_iso(linha["iniciada_em"]) >= limite:
            celula = linha["celula"]
            contagens[celula] = (
                contagens.get(celula, 0)
                + 1
                + int(linha["reaberturas"])
            )
    return [
        _linha_para_demanda(linha, agora, contagens, pesos)
        for linha in linhas
    ]


def _chave_prioridade(demanda):
    return (
        demanda["score"],
        -de_iso(demanda["prazo"]).timestamp(),
        -demanda["identificador"],
    )


def _ordenar_por_prioridade(demandas, limite=None):
    fila = FilaPrioridade()
    itens = []
    for demanda in demandas:
        itens.append(
            (
                _chave_prioridade(demanda),
                demanda["identificador"],
            )
        )
    fila.construir(itens)
    por_identificador = {
        demanda["identificador"]: demanda for demanda in demandas
    }
    resultado = []
    while not fila.vazia():
        if limite is not None and len(resultado) >= limite:
            break
        _, identificador = fila.remover_maximo()
        resultado.append(por_identificador[identificador])
    return resultado


def _buscar_demanda_duplicada(conexao, latitude, longitude, categoria, agora):
    chaves = celulas_vizinhas(latitude, longitude, categoria)
    marcadores = ",".join("?" for _ in chaves)
    limite = para_iso(agora - timedelta(days=JANELA_DEDUPLICACAO_DIAS))
    linhas = conexao.execute(
        f"""
        SELECT * FROM demandas
        WHERE celula IN ({marcadores})
          AND status != 'resolvida'
          AND ultima_ocorrencia >= ?
        """,
        (*chaves, limite),
    ).fetchall()
    melhor_linha = None
    melhor_distancia = None
    for linha in linhas:
        distancia = distancia_metros(
            latitude,
            longitude,
            linha["centroide_latitude"],
            linha["centroide_longitude"],
        )
        if (
            distancia <= RAIO_DEDUPLICACAO_METROS
            and (melhor_distancia is None or distancia < melhor_distancia)
        ):
            melhor_linha = linha
            melhor_distancia = distancia
    return melhor_linha


def _registrar_evento(
    conexao,
    demanda_id,
    status_anterior,
    status_novo,
    agora,
    ator,
):
    conexao.execute(
        """
        INSERT INTO eventos (
            demanda_id, status_anterior, status_novo, criado_em, ator
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            demanda_id,
            status_anterior,
            status_novo,
            para_iso(agora),
            ator,
        ),
    )


def _registrar_historico(conexao, demanda_id, pontuacao, componentes, agora):
    conexao.execute(
        """
        INSERT INTO historico_score (
            demanda_id, criado_em, score, componentes_json, versao_pesos
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            demanda_id,
            para_iso(agora),
            pontuacao,
            json.dumps(componentes, ensure_ascii=False),
            VERSAO_PESOS,
        ),
    )


def _atualizar_pontuacao_demanda(conexao, demanda_id, agora):
    linha = conexao.execute(
        "SELECT * FROM demandas WHERE id = ?",
        (demanda_id,),
    ).fetchone()
    if linha is None:
        return None
    ocorrencias = _contar_recorrencia(conexao, linha["celula"], agora)
    demanda_base = {
        "gravidade": linha["gravidade"],
        "categoria": linha["categoria"],
        "sla_dias": linha["sla_dias"],
        "iniciada_em": linha["iniciada_em"],
        "confirmacoes_validas": linha["confirmacoes_validas"],
        "ocorrencias_90_dias": ocorrencias,
        "entornos": _json_lista(linha["entornos_json"]),
    }
    pontuacao, componentes = calcular_componentes(demanda_base, agora)
    conexao.execute(
        """
        UPDATE demandas
        SET score_atual = ?, componentes_json = ?
        WHERE id = ?
        """,
        (
            pontuacao,
            json.dumps(componentes, ensure_ascii=False),
            demanda_id,
        ),
    )
    _registrar_historico(conexao, demanda_id, pontuacao, componentes, agora)
    return pontuacao, componentes


def _criar_demanda(conexao, dados, categoria, entornos, regiao, agora):
    celula = calcular_celula(dados.latitude, dados.longitude, categoria)
    sla_dias = CATEGORIAS[categoria]["sla_dias"]
    momento = para_iso(agora)
    cursor = conexao.execute(
        """
        INSERT INTO demandas (
            celula, categoria, gravidade, centroide_latitude,
            centroide_longitude, iniciada_em, ultima_ocorrencia,
            sla_dias, status, resolvida_em, reaberturas,
            confirmacoes_validas, relatos_count, entornos_json,
            regiao, score_atual, componentes_json
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, 'aberta', NULL, 0,
            0, 1, ?, ?, 0.0, '{}'
        )
        """,
        (
            celula,
            categoria,
            dados.gravidade,
            dados.latitude,
            dados.longitude,
            momento,
            momento,
            sla_dias,
            json.dumps(entornos, ensure_ascii=False),
            regiao,
        ),
    )
    demanda_id = cursor.lastrowid
    _registrar_evento(
        conexao,
        demanda_id,
        None,
        "aberta",
        agora,
        "cidadão",
    )
    return demanda_id


def _atualizar_demanda_com_relato(
    conexao,
    linha,
    dados,
    entornos,
    regiao,
    agora,
):
    total = int(linha["relatos_count"]) + 1
    centroide_latitude = (
        linha["centroide_latitude"] * linha["relatos_count"]
        + dados.latitude
    ) / total
    centroide_longitude = (
        linha["centroide_longitude"] * linha["relatos_count"]
        + dados.longitude
    ) / total
    entornos_finais = sorted(
        set(_json_lista(linha["entornos_json"])) | set(entornos)
    )
    regiao_final = linha["regiao"]
    if regiao_final == "Não informada" and regiao != "Não informada":
        regiao_final = regiao
    gravidade = max(int(linha["gravidade"]), int(dados.gravidade))
    celula = calcular_celula(
        centroide_latitude,
        centroide_longitude,
        linha["categoria"],
    )
    conexao.execute(
        """
        UPDATE demandas
        SET celula = ?, gravidade = ?, centroide_latitude = ?,
            centroide_longitude = ?, ultima_ocorrencia = ?,
            relatos_count = ?, entornos_json = ?, regiao = ?
        WHERE id = ?
        """,
        (
            celula,
            gravidade,
            centroide_latitude,
            centroide_longitude,
            para_iso(agora),
            total,
            json.dumps(entornos_finais, ensure_ascii=False),
            regiao_final,
            linha["id"],
        ),
    )
    return int(linha["id"])


def _registrar_relato(
    conexao,
    demanda_id,
    token,
    categoria_escolhida,
    categoria_sugerida,
    confianca,
    dados,
    entornos,
    regiao,
    agora,
):
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
            token,
            categoria_escolhida,
            categoria_sugerida,
            confianca,
            dados.gravidade,
            dados.descricao,
            dados.latitude,
            dados.longitude,
            regiao,
            json.dumps(entornos, ensure_ascii=False),
            para_iso(agora),
        ),
    )


def _obter_demanda_por_id(conexao, demanda_id, agora):
    linha = conexao.execute(
        "SELECT * FROM demandas WHERE id = ?",
        (demanda_id,),
    ).fetchone()
    if linha is None:
        raise HTTPException(
            status_code=404,
            detail="Demanda não encontrada.",
        )
    ocorrencias = _contar_recorrencia(conexao, linha["celula"], agora)
    demanda = _linha_para_demanda(
        linha,
        agora,
        {linha["celula"]: ocorrencias},
    )
    relatos = []
    for relato in conexao.execute(
        """
        SELECT * FROM relatos
        WHERE demanda_id = ?
        ORDER BY criado_em DESC
        """,
        (demanda_id,),
    ).fetchall():
        item = dict(relato)
        item.pop("token_cidadao", None)
        item["latitude"] = round(item["latitude"], 3)
        item["longitude"] = round(item["longitude"], 3)
        item["entornos"] = _json_lista(item.pop("entornos_json"))
        relatos.append(item)
    eventos = [
        dict(evento)
        for evento in conexao.execute(
            """
            SELECT * FROM eventos
            WHERE demanda_id = ?
            ORDER BY criado_em DESC
            """,
            (demanda_id,),
        ).fetchall()
    ]
    historico = []
    for registro in conexao.execute(
        """
        SELECT * FROM historico_score
        WHERE demanda_id = ?
        ORDER BY criado_em DESC
        LIMIT 20
        """,
        (demanda_id,),
    ).fetchall():
        item = dict(registro)
        item["componentes"] = _json_dicionario(
            item.pop("componentes_json")
        )
        historico.append(item)
    demanda["relatos"] = relatos
    demanda["eventos"] = eventos
    demanda["historico"] = historico
    return demanda


def criar_relato(dados):
    _validar_coordenada(dados.latitude, dados.longitude)
    agora = agora_utc()
    token = (dados.token_cidadao or "").strip()
    if not token:
        token = uuid.uuid4().hex
    categoria_informada = (dados.categoria or "").strip()
    categoria_sugerida, confianca = classificar_descricao(dados.descricao)
    categoria_escolhida = categoria_informada or categoria_sugerida
    if categoria_escolhida not in CATEGORIAS:
        raise HTTPException(
            status_code=400,
            detail="Categoria inválida.",
        )
    regiao_informada = (dados.regiao or "").strip()
    if regiao_informada and regiao_informada not in REGIOES:
        raise HTTPException(
            status_code=400,
            detail="Região inválida.",
        )
    regiao = regiao_informada or "Não informada"
    entornos = sorted(
        {
            entorno
            for entorno in dados.entornos
            if entorno in RISCOS_ENTORNO
        }
    )
    with abrir_conexao() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        candidato = _buscar_demanda_duplicada(
            conexao,
            dados.latitude,
            dados.longitude,
            categoria_escolhida,
            agora,
        )
        if candidato is None:
            demanda_id = _criar_demanda(
                conexao,
                dados,
                categoria_escolhida,
                entornos,
                regiao,
                agora,
            )
            acao = "demanda_criada"
            mensagem = "Nova demanda criada."
        else:
            demanda_id = _atualizar_demanda_com_relato(
                conexao,
                candidato,
                dados,
                entornos,
                regiao,
                agora,
            )
            acao = "relato_adicionado"
            mensagem = "Relato adicionado à demanda existente."
        _registrar_relato(
            conexao,
            demanda_id,
            token,
            categoria_escolhida,
            categoria_sugerida,
            confianca,
            dados,
            entornos,
            regiao,
            agora,
        )
        _atualizar_pontuacao_demanda(conexao, demanda_id, agora)
        demanda = _obter_demanda_por_id(conexao, demanda_id, agora)
    return {
        "acao": acao,
        "mensagem": mensagem,
        "token_cidadao": token,
        "classificacao": {
            "categoria_sugerida": categoria_sugerida,
            "confianca": round(confianca, 4),
            "categoria_escolhida": categoria_escolhida,
        },
        "demanda": demanda,
    }


def listar_demandas(
    status=None,
    categoria=None,
    regiao=None,
    limite=50,
    deslocamento=0,
):
    if status is not None and status not in STATUS_VALIDOS and status != "todas":
        raise HTTPException(status_code=400, detail="Status inválido.")
    if categoria is not None and categoria not in CATEGORIAS:
        raise HTTPException(status_code=400, detail="Categoria inválida.")
    if regiao is not None and regiao not in REGIOES:
        raise HTTPException(status_code=400, detail="Região inválida.")
    limite = max(1, min(200, int(limite)))
    deslocamento = max(0, int(deslocamento))
    with abrir_conexao() as conexao:
        demandas = _carregar_demandas(conexao, status=status)
    if categoria is not None:
        demandas = [
            demanda
            for demanda in demandas
            if demanda["categoria"] == categoria
        ]
    if regiao is not None:
        demandas = [
            demanda
            for demanda in demandas
            if demanda["regiao"] == regiao
        ]
    demandas = _ordenar_por_prioridade(demandas)
    total = len(demandas)
    return {
        "total": total,
        "itens": demandas[deslocamento:deslocamento + limite],
    }


def listar_top(limite=10, regiao=None):
    if regiao is not None and regiao not in REGIOES:
        raise HTTPException(status_code=400, detail="Região inválida.")
    limite = max(1, min(50, int(limite)))
    with abrir_conexao() as conexao:
        demandas = _carregar_demandas(conexao)
    if regiao is not None:
        demandas = [
            demanda
            for demanda in demandas
            if demanda["regiao"] == regiao
        ]
    total = len(demandas)
    itens = _ordenar_por_prioridade(demandas, limite)
    return {"total": total, "itens": itens}


def listar_mapa(
    limite=500,
    oeste=None,
    sul=None,
    leste=None,
    norte=None,
):
    limite = max(1, min(1000, int(limite)))
    limites = (oeste, sul, leste, norte)
    if any(valor is not None for valor in limites) and None in limites:
        raise HTTPException(
            status_code=400,
            detail="Bounding box incompleta.",
        )
    with abrir_conexao() as conexao:
        demandas = _carregar_demandas(conexao)
    if None not in limites:
        if (
            not -180.0 <= oeste <= 180.0
            or not -180.0 <= leste <= 180.0
            or not -90.0 <= sul <= 90.0
            or not -90.0 <= norte <= 90.0
        ):
            raise HTTPException(
                status_code=400,
                detail="Coordenadas da bounding box inválidas.",
            )
        if oeste >= leste or sul >= norte:
            raise HTTPException(
                status_code=400,
                detail="Bounding box inválida.",
            )
        demandas = [
            demanda
            for demanda in demandas
            if oeste <= demanda["centroide_longitude"] <= leste
            and sul <= demanda["centroide_latitude"] <= norte
        ]
    total = len(demandas)
    selecionadas = _ordenar_por_prioridade(demandas, limite)
    itens = []
    for demanda in selecionadas:
        itens.append(
            {
                "identificador": demanda["identificador"],
                "categoria": demanda["categoria"],
                "nome_categoria": demanda["nome_categoria"],
                "latitude": demanda["centroide_latitude"],
                "longitude": demanda["centroide_longitude"],
                "score": demanda["score"],
                "relatos_count": demanda["relatos_count"],
                "status": demanda["status"],
                "regiao": demanda["regiao"],
                "atrasada": demanda["atrasada"],
            }
        )
    return {"total": total, "itens": itens}


def listar_agenda(dias=7, limite=50):
    dias = max(1, min(90, int(dias)))
    limite = max(1, min(200, int(limite)))
    agora = agora_utc()
    with abrir_conexao() as conexao:
        demandas = _carregar_demandas(conexao)
    ordenadas = ordenar_por_intercalacao(
        demandas,
        lambda demanda: demanda["prazo"],
    )
    referencia_inicio = para_iso(agora)
    referencia_fim = para_iso(agora + timedelta(days=dias))
    indice_inicio = busca_binaria(
        ordenadas,
        referencia_inicio,
        lambda demanda: demanda["prazo"],
    )
    indice_fim = busca_binaria(
        ordenadas,
        referencia_fim,
        lambda demanda: demanda["prazo"],
    )
    return {
        "total": len(ordenadas),
        "dias": dias,
        "total_atrasadas": indice_inicio,
        "atrasadas": ordenadas[:indice_inicio][:limite],
        "proximas": ordenadas[
            indice_inicio:min(indice_fim, indice_inicio + limite)
        ],
        "alem_do_periodo": len(ordenadas) - indice_fim,
    }


def listar_garantia(limite=50):
    limite = max(1, min(200, int(limite)))
    with abrir_conexao() as conexao:
        demandas = _carregar_demandas(conexao)
    em_garantia = [
        demanda
        for demanda in demandas
        if demanda["dias_em_aberto"] > 2 * demanda["sla_dias"]
    ]
    ordenadas = ordenar_por_intercalacao(
        em_garantia,
        lambda demanda: -demanda["dias_em_aberto"],
    )
    return {
        "total": len(ordenadas),
        "itens": ordenadas[:limite],
    }


def obter_estatisticas():
    with abrir_conexao() as conexao:
        total_demandas = conexao.execute(
            "SELECT COUNT(*) AS total FROM demandas"
        ).fetchone()["total"]
        demandas_resolvidas = conexao.execute(
            "SELECT COUNT(*) AS total FROM demandas WHERE status = 'resolvida'"
        ).fetchone()["total"]
        total_confirmacoes = conexao.execute(
            "SELECT COUNT(*) AS total FROM confirmacoes"
        ).fetchone()["total"]
        total_relatos = conexao.execute(
            "SELECT COUNT(*) AS total FROM relatos"
        ).fetchone()["total"]
        por_categoria = [
            dict(linha)
            for linha in conexao.execute(
                """
                SELECT categoria, COUNT(*) AS total
                FROM demandas
                GROUP BY categoria
                ORDER BY total DESC
                """
            ).fetchall()
        ]
        por_regiao = [
            dict(linha)
            for linha in conexao.execute(
                """
                SELECT regiao, COUNT(*) AS total
                FROM demandas
                GROUP BY regiao
                ORDER BY total DESC
                """
            ).fetchall()
        ]
        por_status = [
            dict(linha)
            for linha in conexao.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM demandas
                GROUP BY status
                """
            ).fetchall()
        ]
        abertas = _carregar_demandas(conexao)
    return {
        "total_demandas": total_demandas,
        "demandas_abertas": len(abertas),
        "demandas_resolvidas": demandas_resolvidas,
        "demandas_atrasadas": len(
            [demanda for demanda in abertas if demanda["atrasada"]]
        ),
        "total_confirmacoes": total_confirmacoes,
        "total_relatos": total_relatos,
        "por_categoria": por_categoria,
        "por_regiao": por_regiao,
        "por_status": por_status,
        "categoria_mais_frequente": (
            por_categoria[0]["categoria"] if por_categoria else None
        ),
    }


def listar_revisoes(limite=100):
    limite = max(1, min(200, int(limite)))
    with abrir_conexao() as conexao:
        total = conexao.execute(
            """
            SELECT COUNT(*) AS total
            FROM relatos
            WHERE revisado = 0
              AND (
                categoria_sugerida = 'outros'
                OR confianca_classificacao < ?
              )
            """,
            (LIMIAR_CONFIANCA,),
        ).fetchone()["total"]
        linhas = conexao.execute(
            """
            SELECT r.id, r.demanda_id, r.categoria_escolhida,
                   r.categoria_sugerida, r.confianca_classificacao,
                   r.gravidade, r.descricao, r.latitude, r.longitude,
                   r.regiao, r.criado_em, d.categoria AS categoria_demanda,
                   d.regiao AS regiao_demanda
            FROM relatos r
            JOIN demandas d ON d.id = r.demanda_id
            WHERE r.revisado = 0
              AND (
                r.categoria_sugerida = 'outros'
                OR r.confianca_classificacao < ?
              )
            ORDER BY r.criado_em ASC
            LIMIT ?
            """,
            (LIMIAR_CONFIANCA, limite),
        ).fetchall()
    fila = Fila()
    for linha in linhas:
        fila.enfileirar(linha)
    itens = []
    while not fila.vazia():
        item = dict(fila.desenfileirar())
        item["latitude"] = round(item["latitude"], 3)
        item["longitude"] = round(item["longitude"], 3)
        itens.append(item)
    return {"total": total, "itens": itens}


def concluir_revisao(relato_id):
    with abrir_conexao() as conexao:
        cursor = conexao.execute(
            "UPDATE relatos SET revisado = 1 WHERE id = ?",
            (relato_id,),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Relato não encontrado.",
            )
    return {"mensagem": "Revisão concluída."}


def simular(pesos):
    pesos_normalizados = normalizar_pesos(pesos)
    with abrir_conexao() as conexao:
        demandas = _carregar_demandas(
            conexao,
            pesos=pesos_normalizados,
        )
    itens = _ordenar_por_prioridade(demandas, 10)
    return {
        "pesos": pesos_normalizados,
        "itens": itens,
    }


def obter_categorias():
    categorias = []
    for chave, dados in CATEGORIAS.items():
        categorias.append(
            {
                "chave": chave,
                "nome": dados["nome"],
                "sla_dias": dados["sla_dias"],
                "prioridade": dados["prioridade"],
                "risco": dados["risco"],
                "palavras": PALAVRAS_CHAVE.get(chave, []),
            }
        )
    entornos = [
        {
            "chave": chave,
            "nome": NOMES_ENTORNOS.get(chave, chave),
            "risco": valor,
        }
        for chave, valor in RISCOS_ENTORNO.items()
    ]
    return {
        "categorias": categorias,
        "regioes": REGIOES,
        "entornos": entornos,
        "pesos_padrao": PESOS_PADRAO,
        "centro_mapa": {
            "latitude": CENTRO_MAPA[0],
            "longitude": CENTRO_MAPA[1],
        },
        "raio_piloto_km": RAIO_PILOTO_KM,
        "versao_pesos": VERSAO_PESOS,
        "exige_token_gestor": True,
    }


def confirmar(demanda_id, dados):
    agora = agora_utc()
    with abrir_conexao() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        linha = conexao.execute(
            "SELECT * FROM demandas WHERE id = ?",
            (demanda_id,),
        ).fetchone()
        if linha is None:
            raise HTTPException(
                status_code=404,
                detail="Demanda não encontrada.",
            )
        if linha["status"] == "resolvida":
            raise HTTPException(
                status_code=400,
                detail="Demanda já resolvida.",
            )
        distancia = distancia_metros(
            dados.latitude,
            dados.longitude,
            linha["centroide_latitude"],
            linha["centroide_longitude"],
        )
        if distancia > RAIO_CONFIRMACAO_METROS:
            raise HTTPException(
                status_code=400,
                detail="Confirmação fora do raio permitido.",
            )
        if int(linha["confirmacoes_validas"]) >= MAXIMO_CONFIRMACOES:
            raise HTTPException(
                status_code=409,
                detail="Limite de confirmações atingido.",
            )
        dia = agora.date().isoformat()
        existente = conexao.execute(
            """
            SELECT id FROM confirmacoes
            WHERE demanda_id = ? AND token_cidadao = ? AND dia = ?
            """,
            (demanda_id, dados.token_cidadao, dia),
        ).fetchone()
        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail="Confirmação já registrada hoje.",
            )
        conexao.execute(
            """
            INSERT INTO confirmacoes (
                demanda_id, token_cidadao, criado_em, dia, distancia_m
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                demanda_id,
                dados.token_cidadao,
                para_iso(agora),
                dia,
                distancia,
            ),
        )
        conexao.execute(
            """
            UPDATE demandas
            SET confirmacoes_validas = confirmacoes_validas + 1
            WHERE id = ?
            """,
            (demanda_id,),
        )
        _atualizar_pontuacao_demanda(conexao, demanda_id, agora)
        demanda = _obter_demanda_por_id(conexao, demanda_id, agora)
    return {
        "mensagem": "Confirmação registrada.",
        "demanda": demanda,
    }


def mudar_status(demanda_id, dados):
    if dados.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="Status inválido.")
    agora = agora_utc()
    with abrir_conexao() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        linha = conexao.execute(
            "SELECT * FROM demandas WHERE id = ?",
            (demanda_id,),
        ).fetchone()
        if linha is None:
            raise HTTPException(
                status_code=404,
                detail="Demanda não encontrada.",
            )
        status_atual = linha["status"]
        if dados.status == status_atual:
            raise HTTPException(
                status_code=400,
                detail="A demanda já está neste status.",
            )
        if dados.status not in TRANSICOES_STATUS.get(status_atual, []):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transição de {status_atual} para "
                    f"{dados.status} não permitida."
                ),
            )
        resolvida_em = linha["resolvida_em"]
        reaberturas = int(linha["reaberturas"])
        ultima_ocorrencia = linha["ultima_ocorrencia"]
        if dados.status == "resolvida":
            resolvida_em = para_iso(agora)
        if status_atual == "resolvida" and dados.status == "aberta":
            resolvida_em = None
            reaberturas += 1
            ultima_ocorrencia = para_iso(agora)
        conexao.execute(
            """
            UPDATE demandas
            SET status = ?, resolvida_em = ?, reaberturas = ?,
                ultima_ocorrencia = ?
            WHERE id = ?
            """,
            (
                dados.status,
                resolvida_em,
                reaberturas,
                ultima_ocorrencia,
                demanda_id,
            ),
        )
        _registrar_evento(
            conexao,
            demanda_id,
            status_atual,
            dados.status,
            agora,
            dados.ator,
        )
        _atualizar_pontuacao_demanda(conexao, demanda_id, agora)
        demanda = _obter_demanda_por_id(conexao, demanda_id, agora)
    return {
        "mensagem": "Status atualizado.",
        "demanda": demanda,
    }


def obter_demanda(demanda_id):
    agora = agora_utc()
    with abrir_conexao() as conexao:
        return _obter_demanda_por_id(conexao, demanda_id, agora)
