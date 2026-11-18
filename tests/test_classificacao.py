import pytest

from app.classificacao import classificar_descricao


@pytest.mark.parametrize(
    ("descricao", "categoria"),
    [
        ("Buraco fundo na pista", "buraco"),
        ("Poste apagado deixa a rua escura", "iluminacao"),
        ("Muito lixo e entulho na calçada", "lixo"),
        ("Placa de sinalização caída", "sinalizacao"),
        ("Alagamento e esgoto na rua", "drenagem"),
    ],
)
def test_classifica_categorias_conhecidas(descricao, categoria):
    categoria_sugerida, confianca = classificar_descricao(descricao)
    assert categoria_sugerida == categoria
    assert 0.0 < confianca <= 1.0


def test_classificacao_ignora_acentos_e_maiusculas():
    categoria_sugerida, confianca = classificar_descricao(
        "ILUMINAÇÃO PÚBLICA com LÂMPADA queimada"
    )
    assert categoria_sugerida == "iluminacao"
    assert confianca == 1.0


def test_classificacao_considera_proporcao_dos_acertos():
    categoria_sugerida, confianca = classificar_descricao(
        "Buraco na pista com muito lixo"
    )
    assert categoria_sugerida == "buraco"
    assert confianca == pytest.approx(2.0 / 3.0)


def test_classificacao_sem_palavra_conhecida():
    assert classificar_descricao("Problema urbano observado") == ("outros", 0.0)


def test_classificacao_vazia():
    assert classificar_descricao("") == ("outros", 0.0)
    assert classificar_descricao(None) == ("outros", 0.0)
