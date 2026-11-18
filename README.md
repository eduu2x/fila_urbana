# Fila Urbana

Mapa colaborativo de problemas urbanos com fila de prioridade explicável.

O cidadão registra buracos, falhas de iluminação, descarte irregular de lixo, sinalização danificada e problemas de drenagem. O sistema agrupa relatos próximos do mesmo tipo, classifica o texto por palavras-chave, calcula um score de urgência e entrega ao gestor uma fila ordenada, com prazo, componentes do score e histórico de decisões.

Projeto acadêmico de Estruturas de Dados e Algoritmos. O foco é armazenar, organizar, classificar e priorizar ocorrências usando heap, ordenação por intercalação, busca binária, fila FIFO, dicionários e índices de banco.

## Funcionalidades

- Relato anônimo com categoria, gravidade, descrição, coordenadas, região e entornos de risco.
- Deduplicação por célula geográfica e distância real, com raio de 50 m e janela de 30 dias.
- Classificação por tabela de palavras-chave, com sugestão, confiança e fila de revisão.
- Score multicritério com pesos normalizados e componentes visíveis.
- Fila de prioridade calculada na leitura, sem heap persistido obsoleto.
- Agenda por prazo, painel de garantia e mapa com marcadores por categoria.
- Confirmações de cidadãos com limite por dispositivo, distância e teto por demanda.
- Simulador de pesos que recalcula o Top 10 sem gravar alterações.
- Ações de gestão protegidas por um token simples.

## Stack

| Camada | Ferramenta | Papel |
|---|---|---|
| Linguagem | Python 3.13.7 | Backend e algoritmos |
| API | FastAPI 0.165.0 | Rotas, validação e documentação automática |
| Servidor | Uvicorn 0.54.0 | Servidor ASGI com um worker |
| Validação | Pydantic 2.14.x | Modelos de entrada, incluído no FastAPI |
| Banco | SQLite 3 com `sqlite3` | Persistência local sem servidor e sem ORM |
| Frontend | HTML, CSS e JavaScript puro | Interface sem build e sem npm |
| Mapa | Leaflet 1.9.4 via CDN | Marcadores e interação com OpenStreetMap |
| Testes | pytest 9.2.0 e httpx 0.28.1 | Testes unitários e de API |
| Deploy | Render com runtime Python | Publicação sem Docker |

Fora da stack: Node, npm, React, Vite, Tailwind, ORM, Docker, Redis, Celery e banco externo.

As versões do Python e das dependências ficam em `.python-version`, `requirements.txt` e `requirements-dev.txt`. O deploy usa um único worker porque o SQLite é um arquivo local e a aplicação não depende de estado compartilhado entre processos.

## Estrutura

```text
fila-urbana/
  app/
    banco.py
    classificacao.py
    config.py
    estruturas.py
    main.py
    modelos.py
    prioridade.py
    semeador.py
    servicos.py
    utilidades.py
  scripts/
    semear.py
  static/
    index.html
    estilo.css
    app.js
  tests/
    conftest.py
    test_api.py
    test_classificacao.py
    test_estruturas.py
    test_prioridade.py
    test_servicos.py
    test_utilidades.py
  data/
  requirements.txt
  requirements-dev.txt
  pytest.ini
  render.yaml
  README.md
```

## Como rodar

O projeto foi validado localmente em Python 3.14.10 e fixa Python 3.13.7 para o deploy. Use 3.13.7 para reproduzir o ambiente publicado.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/semear.py --limpar
uvicorn app.main:app --reload --workers 1
```

Acesse `http://127.0.0.1:8000`.

O seed determinístico cria 185 demandas e 441 relatos. Sem `--limpar`, ele só popula um banco vazio. A documentação interativa da API fica em `http://127.0.0.1:8000/docs`.

Para rodar os testes:

```bash
pip install -r requirements-dev.txt
pytest
```

Variáveis de ambiente:

| Variável | Padrão | Uso |
|---|---|---|
| `FILA_URBANA_DB` | `data/fila_urbana.db` | Caminho do arquivo SQLite |
| `FILA_URBANA_TOKEN_GESTOR` | `gestor` | Token do header `X-Token-Gestor` |
| `AUTO_SEED` | desligado | Com `1`, `true` ou `sim`, semeia no boot se o banco estiver vazio |

O token `gestor` existe apenas para demonstração. Em produção, defina `FILA_URBANA_TOKEN_GESTOR` com um valor forte.

## Modelo de dados

| Tabela | Conteúdo |
|---|---|
| `demandas` | Agregado de relatos, centroide, célula, categoria, gravidade, SLA, status, confirmações, reaberturas e último score calculado |
| `relatos` | Denúncia individual, categoria escolhida, categoria sugerida, confiança, descrição, coordenadas e marcação de revisão |
| `confirmacoes` | Apoio por demanda, token, dia e distância; `UNIQUE (demanda_id, token_cidadao, dia)` |
| `eventos` | Transições de status, data e ator |
| `historico_score` | Snapshots do score e dos componentes, com versão dos pesos |

Índices cobrem célula/categoria/status, status, região, relatos por demanda, fila de revisão, confirmações, eventos e histórico.

Receita de concorrência do SQLite:

- `journal_mode = WAL` para leitura e escrita simultâneas.
- `foreign_keys = ON` em cada conexão.
- `busy_timeout = 5000` e timeout de conexão de 10 s.
- Uma conexão aberta e fechada por requisição.
- `BEGIN IMMEDIATE` nas escritas que decidem deduplicação, confirmação e status.
- Endpoints síncronos (`def`) para não bloquear o event loop com o driver `sqlite3`.
- Um único worker no servidor.

Os testes usam um arquivo SQLite temporário por teste, não `:memory:`, para reproduzir o comportamento real de arquivo e WAL.

## Deduplicação e grade

Um relato entra em uma demanda existente quando:

- a categoria escolhida é a mesma;
- a demanda não está resolvida;
- a última ocorrência foi há no máximo 30 dias;
- a distância haversine até o centroide é de no máximo 50 m.

A busca usa uma grade de passo `0,002°` com `math.floor`, não `round`, e consulta as nove células ao redor. A distância real é confirmada por haversine antes do agrupamento.

Prova de cobertura da grade:

```text
0,002° de latitude  ≈ 0,002 × 111,32 km = 222,6 m
0,002° de longitude na latitude 33,7° ≈ 0,002 × 111,32 × cos(33,7°) = 185,2 m
metade da menor célula = 185,2 / 2 = 92,6 m
92,6 m > 50 m de raio
```

Como a metade da menor dimensão da célula é maior que o raio de busca, o disco de 50 m de um ponto cruza no máximo uma fronteira por eixo. Portanto, as nove células cobrem todos os candidatos. Na latitude de São Paulo (23,55°), a célula longitudinal tem cerca de 204 m. O passo anterior de `0,001°` teria metade de 46 m na latitude 33,7° e deixaria pares a 48 m fora do agrupamento.

Regras de confirmação:

- raio de 200 m em relação ao centroide;
- uma confirmação por token de dispositivo por demanda por dia;
- teto de 20 confirmações por demanda;
- confirmação repetida no dia ou acima do teto retorna `409`;
- confirmação fora do raio retorna `400`.

O token do cidadão é um UUID salvo no `localStorage`. Ele reduz duplicidades acidentais, mas não é uma defesa contra fraude determinada.

## Score de prioridade

O score é calculado na leitura:

```text
score = 100 × Σ (peso_normalizado × componente)
```

Os pesos são normalizados para somar 1. Valores negativos, `NaN` e chaves desconhecidas são descartados; se todos forem zero, os pesos padrão são usados.

| Componente | Peso | Normalização |
|---|---:|---|
| Gravidade | 30% | `(gravidade - 1) / 4`, com gravidade entre 1 e 5 |
| Risco | 20% | `min(1, risco da categoria + soma dos riscos do entorno)` |
| Tempo | 20% | `min(1, dias em aberto / (2 × SLA))` |
| Confirmações | 15% | `confirmacoes / (confirmacoes + 3)` |
| Recorrência | 10% | `min(1, ocorrências em 90 dias / 10)` |
| Categoria | 5% | Prioridade intrínseca da categoria |

SLAs por categoria: buraco 7 dias, iluminação 5, lixo 3, sinalização 10, drenagem 5 e outros 15.

Desempate da fila: score decrescente, prazo crescente, identificador crescente. O heap é construído sob demanda com `heapify` e extrai os primeiros `k`; ele nunca é persistido porque tempo e confirmações mudam a cada leitura. O banco guarda apenas snapshots em `historico_score`.

A garantia lista demandas com mais de duas vezes o SLA. A agenda usa ordenação por intercalação e busca binária para separar atrasadas, próximas do prazo e além do período.

Transições de status:

| De | Para |
|---|---|
| `aberta` | `em_analise`, `resolvida` |
| `em_analise` | `em_execucao`, `resolvida`, `aberta` |
| `em_execucao` | `resolvida`, `em_analise` |
| `resolvida` | `aberta` (incrementa reaberturas) |

## Algoritmos e estruturas

| Estrutura | Uso | Complexidade |
|---|---|---|
| Heap binário máximo próprio | Fila de prioridade e Top 10 do simulador | `O(n)` para construir, `O(k log n)` para extrair `k` |
| Ordenação por intercalação | Agenda e garantia | `O(n log n)`, estável |
| Busca binária de limite inferior | Corte da agenda por data | `O(log n)` |
| Fila FIFO com `deque` | Revisões de classificação | `O(1)` por operação |
| Dicionários | Categorias, palavras-chave, pesos, riscos e transições | `O(1)` médio |
| Índices SQLite | Célula, status, região e relacionamentos | B-tree |

O heap foi implementado do zero em `app/estruturas.py`, com `construir`, `inserir`, `remover_maximo`, `espiar`, `_subir` e `_descer`. A ordenação por intercalação e a busca binária também são próprias.

## API

Base: `/api`. A interface e a API são servidas pela mesma origem, então não há configuração de CORS.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/saude` | Saúde e versão |
| `GET` | `/api/categorias` | Categorias, SLAs, entornos, regiões, pesos e centro do mapa |
| `POST` | `/api/relatos` | Cria um relato ou adiciona à demanda próxima |
| `GET` | `/api/demandas` | Lista com filtros de status, categoria e região, além de `limite` e `deslocamento` |
| `GET` | `/api/demandas/top` | Fila priorizada; aceita `limite` e `regiao` |
| `GET` | `/api/demandas/{id}` | Detalhe com relatos, eventos e histórico |
| `POST` | `/api/demandas/{id}/confirmacoes` | Confirma uma demanda |
| `PATCH` | `/api/demandas/{id}/status` | Atualiza o status; exige token de gestor |
| `GET` | `/api/mapa` | Pontos abertos; aceita `limite` e bounding box completa |
| `GET` | `/api/agenda` | Atrasadas e vencimentos; aceita `dias` e `limite` |
| `GET` | `/api/garantia` | Demandas acima de 2× o SLA |
| `GET` | `/api/estatisticas` | Contagens por categoria, região e status |
| `GET` | `/api/revisoes` | Fila FIFO de relatos com baixa confiança |
| `POST` | `/api/revisoes/{id}/concluir` | Conclui uma revisão; exige token de gestor |
| `POST` | `/api/simulacao` | Recalcula o Top 10 com outros pesos, sem gravar |

Observações de contrato:

- `POST /api/relatos` aceita `token_cidadao`, `categoria`, `gravidade`, `descricao`, `latitude`, `longitude`, `regiao` e `entornos`. A resposta informa `acao` (`demanda_criada` ou `relato_adicionado`), `classificacao`, `token_cidadao` e a demanda completa.
- `GET /api/demandas` sem `status` lista apenas demandas não resolvidas. Use `status=todas` para incluir resolvidas.
- `limite` é limitado entre 1 e 200 em `/api/demandas`, 1 e 50 no top e 1 e 1000 no mapa.
- `/api/mapa` exige a bounding box completa (`oeste`, `sul`, `leste`, `norte`) ou nenhuma coordenada.
- `/api/agenda` aceita de 1 a 90 dias.
- `PATCH` e conclusão de revisão exigem o header `X-Token-Gestor`.
- Erros de validação retornam `422`; regra de negócio, `400`; não encontrado, `404`; token inválido, `401`; conflito de confirmação, `409`.

Exemplos:

```bash
curl http://127.0.0.1:8000/api/demandas/top?limite=5

curl -X POST http://127.0.0.1:8000/api/relatos \
  -H 'Content-Type: application/json' \
  -d '{"categoria":"buraco","gravidade":4,"descricao":"Buraco na pista","latitude":-23.5505,"longitude":-46.6333,"regiao":"Centro","entornos":["escola"]}'

curl -X PATCH http://127.0.0.1:8000/api/demandas/1/status \
  -H 'Content-Type: application/json' \
  -H 'X-Token-Gestor: gestor' \
  -d '{"status":"em_analise"}'
```

## Frontend

A interface é uma única página, sem build:

- aba **Mapa e denúncia** com Leaflet, seleção do ponto por clique, geolocalização opcional e formulário de relato;
- aba **Fila de prioridade** com Top 20, filtro por região e acesso ao detalhe;
- aba **Agenda** com atrasadas e próximos vencimentos;
- aba **Garantia** com excesso de prazo em relação ao SLA;
- aba **Revisões** com fila FIFO e botão de conclusão;
- aba **Simulador** com sliders dos seis componentes e Top 10 recalculado.

O modal de detalhe mostra score, componentes, prazo, confirmações, relatos agrupados, eventos e histórico. O token do gestor fica no `sessionStorage`; o token do cidadão, no `localStorage`.

O Leaflet 1.9.4 e o OpenStreetMap são carregados por CDN. Se o mapa não carregar, as listas e a fila continuam funcionando. O CSS é responsivo para desktop e celular.

## Privacidade e retenção

- Não há login, foto, IP armazenado ou identificação civil.
- O token do cidadão é aleatório e local ao navegador.
- Coordenadas retornadas pela API são arredondadas para três casas decimais, cerca de 110 m na latitude de São Paulo.
- Descrições são texto livre; a orientação é não incluir nome, telefone, documento ou endereço completo.
- O seed é sintético e determinístico.
- O MVP não faz expurgo automático. Para uso real, recomenda-se revisar a LGPD e definir retenção, por exemplo 180 dias após a resolução, com rotina de limpeza.
- O token de gestor é uma autenticação de demonstração, não uma solução institucional.
- O limite de confirmações reduz duplicidade, mas não substitui antifraude.

## Testes

```bash
pytest
```

A suíte tem 73 testes:

- `test_estruturas.py`: heap, FIFO, ordenação por intercalação e busca binária.
- `test_classificacao.py`: palavras-chave, acentos, proporção de acertos e caso sem categoria.
- `test_prioridade.py`: normalização de pesos, fórmulas, saturações e efeito dos pesos.
- `test_utilidades.py`: datas, distância, células e normalização de texto.
- `test_servicos.py`: desempate da fila.
- `test_api.py`: saúde, categorias, criação, deduplicação, confirmações, autorização, status, filtros, top, mapa, agenda, garantia, estatísticas, revisões, simulação e arquivos estáticos.

Cada teste de API cria um banco temporário isolado. O seed não é executado implicitamente nos testes. Como o código não tem comentários, os testes e este README documentam o comportamento esperado.

## Deploy no Render

O arquivo `render.yaml` define:

- runtime Python e plano free;
- `pip install -r requirements.txt`;
- `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`;
- Python 3.13.7;
- `FILA_URBANA_DB=data/fila_urbana.db`;
- `AUTO_SEED=1`;
- `FILA_URBANA_TOKEN_GESTOR=gestor`.

Passos sugeridos:

1. Envie o projeto para um repositório no GitHub.
2. No Render, crie um Blueprint apontando para o repositório e aceite o `render.yaml`.
3. Troque o token de gestor por um valor forte nas variáveis de ambiente.
4. Aguarde o build e valide `https://seu-servico.onrender.com/api/saude`.
5. Abra a página inicial e confira o mapa, a fila e o simulador.

O disco do plano free é efêmero: o SQLite pode ser recriado a cada deploy, reinício ou spin-down. Com `AUTO_SEED=1`, o banco vazio é semeado novamente, o que serve para demonstração. Para persistência real, use um disco persistente ou um banco gerenciado, ambos fora do escopo mínimo deste MVP.

Não use Docker neste projeto. O runtime Python do Render é suficiente.

## Escopo e limitações

Fora do MVP: NLP livre, roteirização, aplicativo nativo, autenticação institucional, integração com sistemas da prefeitura, fotos, notificações, múltiplas cidades, antifraude real e banco gerenciado.

O sistema é um piloto de uma cidade. A base é sintética. A classificação é lexical e explicável, não aprende sozinha. A fila é uma recomendação de prioridade, não uma decisão automática de política pública.

## Decisões principais

- Stack mínima: FastAPI, SQLite e JavaScript puro, sem Node, ORM ou Docker.
- Heap derivado na leitura para evitar ordenação obsoleta; snapshots ficam no histórico.
- Grade de 0,002° como índice grosseiro e haversine como confirmação exata de 50 m.
- Score com componentes visíveis e pesos normalizados, em vez de um número opaco.
- Fila FIFO separada para revisar classificações de baixa confiança.
- Token simples de gestor e token local de cidadão, adequados ao escopo acadêmico.
- Seed determinístico para demonstração e testes reproduzíveis.
- Código sem comentários, com identificadores em português e testes como documentação executável.
