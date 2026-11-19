# Fila Urbana

Mapa colaborativo de problemas urbanos com fila de prioridade explicável.

**Site:** [fila-urbana.onrender.com](https://fila-urbana.onrender.com)  
**Documentação da API:** [fila-urbana.onrender.com/docs](https://fila-urbana.onrender.com/docs)  
**Testes:** 74 passando  
**Projeto acadêmico:** Estruturas de Dados e Algoritmos

![Mapa do Fila Urbana](docs/captura-mapa.jpg)

O cidadão registra buracos, falhas de iluminação, descarte irregular de lixo, sinalização danificada e problemas de drenagem. O sistema agrupa relatos próximos do mesmo tipo, classifica o texto por palavras-chave, calcula uma nota de urgência e entrega ao gestor uma fila ordenada, com prazo, componentes da nota e histórico de decisões.

## Como funciona

1. **O cidadão marca o problema no mapa.** Escolhe o local, a categoria, a gravidade, os arredores e escreve uma descrição.
2. **O sistema junta relatos parecidos.** Se alguém já registrou o mesmo tipo de problema em até 50 metros e nos últimos 30 dias, o novo relato é somado à ocorrência existente, em vez de duplicá-la.
3. **O texto é classificado.** Uma tabela de palavras-chave sugere a categoria e informa o grau de confiança. Relatos com baixa confiança entram numa fila de revisão.
4. **Cada problema recebe uma nota de urgência.** A nota considera gravidade, risco do entorno, tempo em aberto, confirmações, recorrência e a prioridade da categoria.
5. **O gestor vê a fila.** Os problemas mais urgentes aparecem primeiro, com prazo, mapa, relatos agrupados e histórico.
6. **O atendimento é acompanhado.** O gestor muda o status, o cidadão confirma problemas existentes e a agenda mostra o que está atrasado ou perto do prazo.

## O que dá para fazer

- Registrar um problema anonimamente, direto no mapa.
- Agrupar denúncias próximas e evitar registros repetidos.
- Classificar automaticamente o relato e revisar os casos duvidosos.
- Consultar a fila de prioridade, com filtro por região.
- Ver a agenda por prazo, as demandas atrasadas e a garantia de atendimento.
- Confirmar um problema existente, com limite por dispositivo.
- Acompanhar o detalhe de cada demanda, com componentes da nota e histórico.
- Simular outros pesos e ver o Top 10 recalculado sem alterar o banco.
- Acessar tudo pelo celular ou pelo computador, sem instalar nada.

## Tecnologias

| Camada | Ferramenta |
|---|---|
| Backend | Python 3.13.7 e FastAPI 0.165.0 |
| Servidor | Uvicorn 0.54.0, com um worker |
| Banco | SQLite 3, usando `sqlite3` e sem ORM |
| Frontend | HTML, CSS e JavaScript puro, sem build |
| Mapa | Leaflet 1.9.4 e OpenStreetMap via CDN |
| Testes | pytest 9.2.0 e httpx 0.28.1 |
| Deploy | Render, runtime Python e plano free |

Fora da stack: Node, npm, React, Vite, Tailwind, ORM, Docker, Redis, Celery e banco externo.

## Rodando localmente

```bash
git clone https://github.com/eduu2x/fila_urbana.git
cd fila_urbana
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/semear.py --limpar
uvicorn app.main:app --reload --workers 1
```

Acesse `http://127.0.0.1:8000`.

O seed determinístico cria 185 demandas, 441 relatos e 1.710 confirmações. Sem `--limpar`, ele só popula um banco vazio. A documentação interativa fica em `http://127.0.0.1:8000/docs`.

Para rodar os testes:

```bash
pip install -r requirements-dev.txt
pytest
```

## Token do gestor

O token é uma senha simples da equipe, não um login. Ele libera as ações de gestão, como mudar o status de uma demanda e concluir uma revisão. O cidadão não precisa dele para registrar ou confirmar problemas.

- No servidor, o token fica na variável `FILA_URBANA_TOKEN_GESTOR`. O valor de demonstração é `gestor`.
- No site, o campo **Token do gestor** fica no topo da página. A pessoa digita ali o mesmo valor configurado no servidor.
- No Render, o caminho é **serviço → Environment → FILA_URBANA_TOKEN_GESTOR → editar → salvar e fazer deploy**.
- Em uso real, troque `gestor` por um valor forte. O `render.yaml` é público, então o ideal é não guardar o segredo nele.

## Estrutura

```text
fila_urbana/
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
  docs/
    captura-mapa.jpg
  scripts/
    semear.py
  static/
    app.js
    estilo.css
    favicon.svg
    index.html
  tests/
    conftest.py
    test_api.py
    test_classificacao.py
    test_estruturas.py
    test_prioridade.py
    test_servicos.py
    test_utilidades.py
  data/
  pytest.ini
  render.yaml
  requirements.txt
  requirements-dev.txt
  README.md
```

## API

Base: `/api`. A interface e a API são servidas pela mesma origem, então não há CORS.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/saude` | Saúde e versão |
| `GET` | `/api/categorias` | Categorias, prazos, entornos, regiões, pesos e centro do mapa |
| `POST` | `/api/relatos` | Cria um relato ou adiciona a uma demanda próxima |
| `GET` | `/api/demandas` | Lista com filtros de status, categoria e região |
| `GET` | `/api/demandas/top` | Fila priorizada, com `limite` e `regiao` |
| `GET` | `/api/demandas/{id}` | Detalhe com relatos, eventos e histórico |
| `POST` | `/api/demandas/{id}/confirmacoes` | Confirma uma demanda |
| `PATCH` | `/api/demandas/{id}/status` | Atualiza o status; exige token de gestor |
| `GET` | `/api/mapa` | Pontos abertos, com `limite` e bounding box opcional |
| `GET` | `/api/agenda` | Atrasadas e vencimentos, com `dias` e `limite` |
| `GET` | `/api/garantia` | Demandas acima de 2× o prazo da categoria |
| `GET` | `/api/estatisticas` | Contagens por categoria, região e status |
| `GET` | `/api/revisoes` | Fila FIFO de relatos com baixa confiança |
| `POST` | `/api/revisoes/{id}/concluir` | Conclui uma revisão; exige token de gestor |
| `POST` | `/api/simulacao` | Recalcula o Top 10 com outros pesos, sem gravar |

Erros de validação retornam `422`; regra de negócio, `400`; não encontrado, `404`; token inválido, `401`; conflito de confirmação, `409`.

## Score de prioridade

```text
score = 100 × Σ (peso_normalizado × componente)
```

| Componente | Peso | Normalização |
|---|---:|---|
| Gravidade | 30% | `(gravidade - 1) / 4` |
| Risco | 20% | risco da categoria + riscos do entorno, limitado a 1 |
| Tempo | 20% | dias em aberto divididos por 2 × prazo, limitado a 1 |
| Confirmações | 15% | `confirmacoes / (confirmacoes + 3)` |
| Recorrência | 10% | ocorrências em 90 dias divididas por 10, limitado a 1 |
| Categoria | 5% | prioridade própria da categoria |

Prazos por categoria: buraco 7 dias, iluminação 5, lixo 3, sinalização 10, drenagem 5 e outros 15.

Os pesos são normalizados para somar 1. Valores inválidos são descartados; se todos forem zero, os pesos padrão voltam. O desempate da fila é: maior score, menor prazo e menor identificador.

## Estruturas de dados

| Estrutura | Uso |
|---|---|
| Heap binário máximo próprio | Fila de prioridade e Top 10 do simulador |
| Ordenação por intercalação | Agenda e garantia |
| Busca binária | Corte da agenda por data |
| Fila FIFO com `deque` | Revisões de classificação |
| Dicionários | Categorias, palavras-chave, pesos, riscos e transições |
| Índices SQLite | Célula, status, região e relacionamentos |

O heap, a ordenação por intercalação e a busca binária foram implementados em `app/estruturas.py`, sem biblioteca pronta.

## Testes

```bash
pytest
```

A suíte tem 74 testes:

- `test_estruturas.py`: heap, FIFO, ordenação por intercalação e busca binária.
- `test_classificacao.py`: palavras-chave, acentos, confiança e caso sem categoria.
- `test_prioridade.py`: pesos, fórmulas, saturações e efeito dos componentes.
- `test_utilidades.py`: datas, distância, células e normalização de texto.
- `test_servicos.py`: desempate da fila.
- `test_api.py`: saúde, categorias, criação, agrupamento, confirmações, autorização, status, filtros, top, mapa, agenda, garantia, estatísticas, revisões, simulação, arquivos estáticos e favicon.

Cada teste de API usa um banco temporário isolado. O seed não roda automaticamente nos testes.

## Deploy

O site está publicado no Render:

- URL: https://fila-urbana.onrender.com
- Health check: https://fila-urbana.onrender.com/api/saude
- Configuração: `render.yaml`
- Comando de build: `pip install -r requirements.txt`
- Comando de start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- Variáveis: `FILA_URBANA_DB=data/fila_urbana.db`, `AUTO_SEED=1` e `FILA_URBANA_TOKEN_GESTOR`

Com o auto-deploy ligado, cada push na branch `main` publica uma nova versão. Também é possível usar **Manual Deploy → Deploy latest commit** no painel do Render. O plano free usa disco efêmero: o SQLite pode ser recriado a cada deploy, reinício ou spin-down. Com `AUTO_SEED=1`, um banco vazio é semeado novamente, o que serve para demonstração. Para persistência real, seria necessário um disco persistente ou um banco gerenciado.

## Limitações

O projeto é um piloto de uma cidade, com base sintética. A classificação é lexical e explicável, não aprende sozinha. A fila é uma recomendação de prioridade, não uma decisão automática de política pública. Ficam fora do MVP: fotos, notificações, aplicativo nativo, autenticação institucional, integração com sistemas da prefeitura, múltiplas cidades e antifraude real.

<details>
<summary>Detalhes técnicos</summary>

### Agrupamento e grade

Um relato entra em uma demanda existente quando a categoria é a mesma, a demanda não está resolvida, a última ocorrência foi há no máximo 30 dias e a distância até o centroide é de no máximo 50 metros.

A busca usa uma grade de passo `0,002°` com `math.floor` e consulta as nove células ao redor. A distância real é confirmada por haversine. A metade da menor célula da grade é maior que o raio de 50 metros, então as nove células cobrem todos os candidatos.

### Modelo de dados

| Tabela | Conteúdo |
|---|---|
| `demandas` | Agregado de relatos, centroide, célula, categoria, gravidade, prazo, status, confirmações, reaberturas e último score |
| `relatos` | Denúncia individual, categoria escolhida, categoria sugerida, confiança, descrição, coordenadas e revisão |
| `confirmacoes` | Apoio por demanda, token, dia e distância, com restrição única por demanda, token e dia |
| `eventos` | Transições de status, data e ator |
| `historico_score` | Snapshots do score e dos componentes, com versão dos pesos |

### Concorrência do SQLite

- `journal_mode = WAL`, `foreign_keys = ON` e `busy_timeout = 5000`.
- Uma conexão aberta e fechada por requisição.
- `BEGIN IMMEDIATE` nas escritas que decidem agrupamento, confirmação e status.
- Endpoints síncronos e um único worker.

### Regras de confirmação

- Raio de 200 metros em relação ao centroide.
- Uma confirmação por dispositivo, por demanda, por dia.
- Teto de 20 confirmações por demanda.
- Confirmação repetida ou acima do teto retorna `409`; fora do raio retorna `400`.

### Transições de status

| De | Para |
|---|---|
| `aberta` | `em_analise`, `resolvida` |
| `em_analise` | `em_execucao`, `resolvida`, `aberta` |
| `em_execucao` | `resolvida`, `em_analise` |
| `resolvida` | `aberta`, incrementando reaberturas |

### Privacidade

- Não há login, foto, IP armazenado ou identificação civil.
- O token do cidadão é aleatório e local ao navegador.
- As coordenadas retornadas pela API são arredondadas para três casas decimais.
- O seed é sintético e determinístico.
- O MVP não faz expurgo automático. Para uso real, é necessário revisar a LGPD e definir retenção.

</details>

## Decisões principais

- Stack mínima: FastAPI, SQLite e JavaScript puro, sem Node, ORM ou Docker.
- Heap derivado na leitura para evitar ordenação obsoleta; snapshots ficam no histórico.
- Grade de 0,002° como índice grosseiro e haversine como confirmação exata de 50 metros.
- Score com componentes visíveis e pesos normalizados, em vez de um número opaco.
- Fila FIFO separada para revisar classificações de baixa confiança.
- Token simples de gestor e token local de cidadão, adequados ao escopo acadêmico.
- Seed determinístico para demonstração e testes reproduzíveis.
- Código sem comentários, com identificadores em português e testes como documentação executável.
