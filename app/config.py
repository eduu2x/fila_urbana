import os

CATEGORIAS = {
    "buraco": {
        "nome": "Buraco na via",
        "sla_dias": 7,
        "prioridade": 0.90,
        "risco": 0.60,
    },
    "iluminacao": {
        "nome": "Falha de iluminação",
        "sla_dias": 5,
        "prioridade": 0.80,
        "risco": 0.50,
    },
    "lixo": {
        "nome": "Descarte irregular de lixo",
        "sla_dias": 3,
        "prioridade": 0.70,
        "risco": 0.40,
    },
    "sinalizacao": {
        "nome": "Sinalização danificada",
        "sla_dias": 10,
        "prioridade": 0.60,
        "risco": 0.50,
    },
    "drenagem": {
        "nome": "Problema de drenagem",
        "sla_dias": 5,
        "prioridade": 0.80,
        "risco": 0.60,
    },
    "outros": {
        "nome": "Outros",
        "sla_dias": 15,
        "prioridade": 0.30,
        "risco": 0.20,
    },
}

PESOS_PADRAO = {
    "gravidade": 0.30,
    "risco": 0.20,
    "tempo": 0.20,
    "confirmacoes": 0.15,
    "recorrencia": 0.10,
    "categoria": 0.05,
}

RISCOS_ENTORNO = {
    "escola": 0.25,
    "hospital": 0.25,
    "ponto_onibus": 0.15,
    "via_arterial": 0.20,
}

NOMES_ENTORNOS = {
    "escola": "Escola",
    "hospital": "Hospital",
    "ponto_onibus": "Ponto de ônibus",
    "via_arterial": "Via arterial",
}

PALAVRAS_CHAVE = {
    "buraco": ["buraco", "cratera", "asfalto", "pista", "bueiro", "remendo"],
    "iluminacao": ["iluminacao", "poste", "lampada", "luz", "escuro", "energia"],
    "lixo": ["lixo", "residuo", "entulho", "descarte", "sujeira", "coleta"],
    "sinalizacao": ["sinalizacao", "placa", "faixa", "semaforo", "pintura", "sinal"],
    "drenagem": ["drenagem", "alagamento", "enchente", "esgoto", "vazamento", "agua"],
}

REGIOES = [
    "Centro",
    "Zona Norte",
    "Zona Sul",
    "Zona Leste",
    "Zona Oeste",
]

STATUS_VALIDOS = [
    "aberta",
    "em_analise",
    "em_execucao",
    "resolvida",
]

TRANSICOES_STATUS = {
    "aberta": ["em_analise", "resolvida"],
    "em_analise": ["em_execucao", "resolvida", "aberta"],
    "em_execucao": ["resolvida", "em_analise"],
    "resolvida": ["aberta"],
}

LIMIAR_CONFIANCA = 0.50
RAIO_DEDUPLICACAO_METROS = 50.0
PASSO_GRADE = 0.002
JANELA_DEDUPLICACAO_DIAS = 30
JANELA_RECORRENCIA_DIAS = 90
MAXIMO_CONFIRMACOES = 20
RAIO_CONFIRMACAO_METROS = 200.0
CENTRO_MAPA = (-23.5505, -46.6333)
RAIO_PILOTO_KM = 50.0
VERSAO_PESOS = "1.0"
TOKEN_GESTOR = os.environ.get("FILA_URBANA_TOKEN_GESTOR", "gestor")
