import math

from app.config import CATEGORIAS, PESOS_PADRAO, RISCOS_ENTORNO
from app.utilidades import dias_desde


def normalizar_pesos(pesos):
    pesos_finais = {nome: 0.0 for nome in PESOS_PADRAO}
    for nome, valor in (pesos or {}).items():
        if nome in pesos_finais:
            numero = float(valor)
            if not math.isfinite(numero) or numero < 0.0:
                numero = 0.0
            pesos_finais[nome] = numero
    soma = sum(pesos_finais.values())
    if soma <= 0.0:
        return dict(PESOS_PADRAO)
    return {nome: valor / soma for nome, valor in pesos_finais.items()}


def calcular_componentes(demanda, agora, pesos=None):
    pesos_normalizados = normalizar_pesos(pesos)
    gravidade = max(1, min(5, int(demanda.get("gravidade", 1))))
    fator_gravidade = (gravidade - 1) / 4.0
    categoria = demanda.get("categoria", "outros")
    dados_categoria = CATEGORIAS.get(categoria, CATEGORIAS["outros"])
    risco_categoria = dados_categoria.get("risco", 0.0)
    entornos = demanda.get("entornos", [])
    risco_entorno = 0.0
    for entorno in entornos:
        risco_entorno += RISCOS_ENTORNO.get(entorno, 0.0)
    fator_risco = min(1.0, risco_categoria + risco_entorno)
    sla_dias = max(1, int(demanda.get("sla_dias", 1)))
    dias_em_aberto = dias_desde(demanda.get("iniciada_em"), agora)
    fator_tempo = min(1.0, dias_em_aberto / (2.0 * sla_dias))
    confirmacoes = max(0, int(demanda.get("confirmacoes_validas", 0)))
    fator_confirmacoes = confirmacoes / (confirmacoes + 3.0)
    ocorrencias = max(1, int(demanda.get("ocorrencias_90_dias", 1)))
    fator_recorrencia = min(1.0, ocorrencias / 10.0)
    fator_categoria = dados_categoria.get("prioridade", 0.0)
    componentes = {
        "gravidade": fator_gravidade,
        "risco": fator_risco,
        "tempo": fator_tempo,
        "confirmacoes": fator_confirmacoes,
        "recorrencia": fator_recorrencia,
        "categoria": fator_categoria,
    }
    pontuacao = 100.0 * sum(
        pesos_normalizados[nome] * componentes[nome] for nome in componentes
    )
    return round(pontuacao, 2), componentes
