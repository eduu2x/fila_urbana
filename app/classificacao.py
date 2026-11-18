from app.config import PALAVRAS_CHAVE
from app.utilidades import normalizar_texto


def classificar_descricao(descricao):
    texto = normalizar_texto(descricao)
    pontuacoes = {}
    for categoria, palavras in PALAVRAS_CHAVE.items():
        acertos = 0
        for palavra in palavras:
            if palavra in texto:
                acertos += 1
        if acertos > 0:
            pontuacoes[categoria] = acertos
    if not pontuacoes:
        return "outros", 0.0
    categoria_sugerida = max(pontuacoes, key=pontuacoes.get)
    total = sum(pontuacoes.values())
    confianca = pontuacoes[categoria_sugerida] / total
    return categoria_sugerida, confianca
