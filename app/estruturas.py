from collections import deque


class FilaPrioridade:
    def __init__(self):
        self.itens = []

    def tamanho(self):
        return len(self.itens)

    def vazia(self):
        return len(self.itens) == 0

    def espiar(self):
        if self.vazia():
            return None
        return self.itens[0]

    def construir(self, itens):
        self.itens = list(itens)
        for indice in range((len(self.itens) - 2) // 2, -1, -1):
            self._descer(indice)

    def inserir(self, prioridade, identificador):
        self.itens.append((prioridade, identificador))
        self._subir(len(self.itens) - 1)

    def remover_maximo(self):
        if self.vazia():
            return None
        maximo = self.itens[0]
        ultimo = self.itens.pop()
        if self.itens:
            self.itens[0] = ultimo
            self._descer(0)
        return maximo

    def _subir(self, indice):
        while indice > 0:
            indice_pai = (indice - 1) // 2
            if self.itens[indice] <= self.itens[indice_pai]:
                break
            self.itens[indice], self.itens[indice_pai] = (
                self.itens[indice_pai],
                self.itens[indice],
            )
            indice = indice_pai

    def _descer(self, indice):
        tamanho = len(self.itens)
        while True:
            filho_esquerdo = 2 * indice + 1
            filho_direito = 2 * indice + 2
            maior = indice
            if (
                filho_esquerdo < tamanho
                and self.itens[filho_esquerdo] > self.itens[maior]
            ):
                maior = filho_esquerdo
            if (
                filho_direito < tamanho
                and self.itens[filho_direito] > self.itens[maior]
            ):
                maior = filho_direito
            if maior == indice:
                break
            self.itens[indice], self.itens[maior] = (
                self.itens[maior],
                self.itens[indice],
            )
            indice = maior


class Fila:
    def __init__(self):
        self.itens = deque()

    def enfileirar(self, item):
        self.itens.append(item)

    def desenfileirar(self):
        if not self.itens:
            return None
        return self.itens.popleft()

    def vazia(self):
        return len(self.itens) == 0

    def tamanho(self):
        return len(self.itens)


def ordenar_por_intercalacao(lista, chave):
    if len(lista) <= 1:
        return list(lista)
    meio = len(lista) // 2
    esquerda = ordenar_por_intercalacao(lista[:meio], chave)
    direita = ordenar_por_intercalacao(lista[meio:], chave)
    return _intercalar(esquerda, direita, chave)


def _intercalar(esquerda, direita, chave):
    resultado = []
    indice_esquerda = 0
    indice_direita = 0
    while indice_esquerda < len(esquerda) and indice_direita < len(direita):
        if chave(esquerda[indice_esquerda]) <= chave(direita[indice_direita]):
            resultado.append(esquerda[indice_esquerda])
            indice_esquerda += 1
        else:
            resultado.append(direita[indice_direita])
            indice_direita += 1
    resultado.extend(esquerda[indice_esquerda:])
    resultado.extend(direita[indice_direita:])
    return resultado


def busca_binaria(lista, alvo, chave):
    inicio = 0
    fim = len(lista)
    while inicio < fim:
        meio = (inicio + fim) // 2
        if chave(lista[meio]) < alvo:
            inicio = meio + 1
        else:
            fim = meio
    return inicio
