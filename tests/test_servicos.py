from app.servicos import _chave_prioridade


def montar_demanda(identificador, pontuacao, prazo):
    return {
        "identificador": identificador,
        "score": pontuacao,
        "prazo": prazo,
    }


def test_desempate_usa_score_prazo_e_identificador():
    atrasada = montar_demanda(9, 50.0, "2026-11-19T00:00:00+00:00")
    adiantada = montar_demanda(1, 50.0, "2026-11-20T00:00:00+00:00")
    assert _chave_prioridade(atrasada) > _chave_prioridade(adiantada)


def test_desempate_favorece_identificador_menor():
    antiga = montar_demanda(1, 50.0, "2026-11-20T00:00:00+00:00")
    recente = montar_demanda(2, 50.0, "2026-11-20T00:00:00+00:00")
    assert _chave_prioridade(antiga) > _chave_prioridade(recente)


def test_score_tem_peso_maior_que_qualquer_desempate():
    maior_score = montar_demanda(99, 60.0, "2026-12-01T00:00:00+00:00")
    menor_score = montar_demanda(1, 50.0, "2026-11-01T00:00:00+00:00")
    assert _chave_prioridade(maior_score) > _chave_prioridade(menor_score)
