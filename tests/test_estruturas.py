from app.estruturas import Fila, FilaPrioridade, busca_binaria, ordenar_por_intercalacao


def test_fila_prioridade_remove_maior_primeiro():
    fila = FilaPrioridade()
    for prioridade in (10, 40, 20, 30):
        fila.inserir(prioridade, prioridade)
    removidos = []
    while not fila.vazia():
        removidos.append(fila.remover_maximo())
    assert removidos == [(40, 40), (30, 30), (20, 20), (10, 10)]


def test_fila_prioridade_construir_e_espiar():
    fila = FilaPrioridade()
    fila.construir([(5, "a"), (9, "b"), (1, "c"), (3, "d")])
    assert fila.espiar() == (9, "b")
    assert fila.tamanho() == 4
    assert fila.remover_maximo() == (9, "b")
    assert fila.remover_maximo() == (5, "a")
    assert fila.remover_maximo() == (3, "d")
    assert fila.remover_maximo() == (1, "c")


def test_fila_prioridade_vazia():
    fila = FilaPrioridade()
    assert fila.vazia()
    assert fila.espiar() is None
    assert fila.remover_maximo() is None


def test_fila_atende_ordem_de_chegada():
    fila = Fila()
    fila.enfileirar("primeiro")
    fila.enfileirar("segundo")
    assert fila.tamanho() == 2
    assert fila.desenfileirar() == "primeiro"
    assert fila.desenfileirar() == "segundo"
    assert fila.desenfileirar() is None
    assert fila.vazia()


def test_ordenacao_por_intercalacao():
    valores = [8, 3, 5, 1, 9, 2, 7, 4, 6]
    assert ordenar_por_intercalacao(valores, lambda valor: valor) == sorted(valores)
    assert ordenar_por_intercalacao([], lambda valor: valor) == []
    assert ordenar_por_intercalacao([2], lambda valor: valor) == [2]


def test_ordenacao_por_intercalacao_com_chave():
    itens = [
        {"nome": "b", "prazo": "2026-11-20"},
        {"nome": "a", "prazo": "2026-11-19"},
        {"nome": "c", "prazo": "2026-11-21"},
    ]
    resultado = ordenar_por_intercalacao(itens, lambda item: item["prazo"])
    assert [item["nome"] for item in resultado] == ["a", "b", "c"]


def test_busca_binaria_primeiro_maior_ou_igual():
    lista = [1, 3, 5, 7, 9]
    assert busca_binaria(lista, 0, lambda valor: valor) == 0
    assert busca_binaria(lista, 3, lambda valor: valor) == 1
    assert busca_binaria(lista, 6, lambda valor: valor) == 3
    assert busca_binaria(lista, 10, lambda valor: valor) == 5
    assert busca_binaria([], 1, lambda valor: valor) == 0
