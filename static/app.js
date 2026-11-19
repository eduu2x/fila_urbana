const PESOS_PADRAO = {
  gravidade: 0.3,
  risco: 0.2,
  tempo: 0.2,
  confirmacoes: 0.15,
  recorrencia: 0.1,
  categoria: 0.05,
};

const COMPONENTES = {
  gravidade: "Gravidade",
  risco: "Risco do entorno",
  tempo: "Tempo em aberto",
  confirmacoes: "Confirmações",
  recorrencia: "Recorrência",
  categoria: "Peso da categoria",
};

const TRANSICOES = {
  aberta: ["em_analise", "resolvida"],
  em_analise: ["em_execucao", "resolvida", "aberta"],
  em_execucao: ["resolvida", "em_analise"],
  resolvida: ["aberta"],
};

const NOMES_STATUS = {
  aberta: "Aberta",
  em_analise: "Em análise",
  em_execucao: "Em execução",
  resolvida: "Resolvida",
};

const CORES_CATEGORIAS = {
  buraco: "#d95d39",
  iluminacao: "#d99a00",
  lixo: "#4f8a3d",
  sinalizacao: "#2f6db3",
  drenagem: "#21867a",
  outros: "#7a7f86",
};

const estado = {
  categorias: [],
  regioes: [],
  entornos: [],
  pesosPadrao: PESOS_PADRAO,
  centro: { latitude: -23.5505, longitude: -46.6333 },
  mapa: null,
  camadaMarcadores: null,
  marcadorNovo: null,
  mapaAjustado: false,
  demandaAtual: null,
};

document.addEventListener("DOMContentLoaded", iniciar);

async function iniciar() {
  configurarAbas();
  configurarToken();
  configurarFormulario();
  configurarFiltros();
  configurarModal();
  configurarSimulador();
  configurarAcoesGlobais();
  try {
    await carregarConfiguracoes();
  } catch (erro) {
    mostrarToast("Não foi possível carregar as configurações da API.", "erro");
    montarControlesPesos(PESOS_PADRAO);
  }
  iniciarMapa();
  desenharLegenda();
  await recarregarDados();
  simular(null, true);
}

function configurarAbas() {
  const botoes = document.querySelectorAll(".aba");
  const carregadores = {
    mapa: carregarMapa,
    fila: carregarFila,
    agenda: carregarAgenda,
    garantia: carregarGarantia,
    revisoes: carregarRevisoes,
    simulador: () => simular(null, true),
  };
  botoes.forEach((botao) => {
    botao.addEventListener("click", () => {
      botoes.forEach((item) => item.classList.toggle("ativa", item === botao));
      document.querySelectorAll(".painel").forEach((painel) => {
        painel.classList.remove("ativo");
      });
      document.getElementById(`painel-${botao.dataset.aba}`).classList.add("ativo");
      const carregador = carregadores[botao.dataset.aba];
      if (carregador) {
        carregador().catch(tratarErro);
      }
    });
  });
}

function configurarToken() {
  const campo = document.getElementById("token-gestor");
  const botao = document.getElementById("validar-token");
  campo.value = sessionStorage.getItem("filaUrbanaTokenGestor") || "";
  campo.addEventListener("input", () => {
    sessionStorage.setItem("filaUrbanaTokenGestor", campo.value);
    marcarTokenPendente();
  });
  campo.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
      evento.preventDefault();
      validarToken();
    }
  });
  botao.addEventListener("click", () => validarToken());
  if (campo.value.trim()) {
    validarToken(true);
  } else {
    marcarTokenPendente();
  }
}

function marcarTokenPendente() {
  const campo = document.getElementById("token-gestor");
  const aviso = document.getElementById("aviso-token");
  aviso.className = "aviso-token";
  aviso.textContent = campo.value.trim()
    ? "Token não verificado — clique em Validar"
    : "Digite o token e clique em Validar";
}

async function validarToken(silencioso = false) {
  const campo = document.getElementById("token-gestor");
  const aviso = document.getElementById("aviso-token");
  const botao = document.getElementById("validar-token");
  const token = campo.value.trim();
  if (!token) {
    aviso.className = "aviso-token invalido";
    aviso.textContent = "Informe o token para ações de gestão";
    if (!silencioso) {
      mostrarToast("Informe o token do gestor.", "erro");
    }
    return;
  }
  botao.disabled = true;
  aviso.className = "aviso-token verificando";
  aviso.textContent = "Verificando token...";
  try {
    await pedir("/gestor/verificar", {
      method: "POST",
      headers: { "X-Token-Gestor": token },
    });
    if (campo.value.trim() !== token) {
      return;
    }
    aviso.className = "aviso-token valido";
    aviso.textContent = "Token válido — ações de gestão liberadas";
    if (!silencioso) {
      mostrarToast("Token válido. Ações de gestão liberadas.", "sucesso");
    }
  } catch (erro) {
    if (campo.value.trim() === token) {
      aviso.className = "aviso-token invalido";
      aviso.textContent = "Token inválido — confira o valor";
      if (!silencioso) {
        mostrarToast(erro.message, "erro");
      }
    }
  } finally {
    botao.disabled = false;
  }
}

function obterTokenGestor() {
  return document.getElementById("token-gestor").value.trim();
}

function tokenCidadao() {
  let token = localStorage.getItem("filaUrbanaTokenCidadao");
  if (!token) {
    token = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `cidadao-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem("filaUrbanaTokenCidadao", token);
  }
  return token;
}

function configurarFormulario() {
  const formulario = document.getElementById("formulario-relato");
  formulario.addEventListener("submit", enviarRelato);
  document.getElementById("botao-localizacao").addEventListener("click", usarLocalizacao);
  const gravidade = document.getElementById("gravidade");
  gravidade.addEventListener("input", () => {
    document.getElementById("saida-gravidade").textContent = gravidade.value;
  });
  document.getElementById("latitude").value = estado.centro.latitude.toFixed(4);
  document.getElementById("longitude").value = estado.centro.longitude.toFixed(4);
}

function configurarFiltros() {
  document.getElementById("botao-atualizar-fila").addEventListener("click", () => {
    carregarFila().catch(tratarErro);
  });
  document.getElementById("filtro-regiao-fila").addEventListener("change", () => {
    carregarFila().catch(tratarErro);
  });
  document.getElementById("botao-atualizar-agenda").addEventListener("click", () => {
    carregarAgenda().catch(tratarErro);
  });
  document.getElementById("dias-agenda").addEventListener("change", () => {
    carregarAgenda().catch(tratarErro);
  });
}

function configurarModal() {
  document.getElementById("fechar-modal").addEventListener("click", fecharModal);
  document.getElementById("modal").addEventListener("click", (evento) => {
    if (evento.target.id === "modal") {
      fecharModal();
    }
  });
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") {
      fecharModal();
    }
  });
}

function configurarSimulador() {
  document.getElementById("formulario-simulacao").addEventListener("submit", simular);
  document.getElementById("botao-restaurar-pesos").addEventListener("click", restaurarPesos);
}

function configurarAcoesGlobais() {
  document.addEventListener("click", (evento) => {
    const alvoDetalhe = evento.target.closest("[data-detalhe]");
    if (alvoDetalhe) {
      abrirDetalhe(Number(alvoDetalhe.dataset.detalhe));
      return;
    }
    const alvoRevisao = evento.target.closest("[data-concluir-revisao]");
    if (alvoRevisao) {
      concluirRevisao(alvoRevisao);
    }
  });
}

async function carregarConfiguracoes() {
  const dados = await pedir("/categorias");
  estado.categorias = dados.categorias;
  estado.regioes = dados.regioes;
  estado.entornos = dados.entornos;
  estado.pesosPadrao = dados.pesos_padrao || PESOS_PADRAO;
  estado.centro = dados.centro_mapa || estado.centro;
  preencherSelect(
    document.getElementById("categoria"),
    estado.categorias.map((categoria) => ({
      valor: categoria.chave,
      rotulo: categoria.nome,
    })),
    "Automática",
  );
  preencherSelect(
    document.getElementById("regiao"),
    estado.regioes.map((regiao) => ({ valor: regiao, rotulo: regiao })),
    "Não informar",
  );
  preencherSelect(
    document.getElementById("filtro-regiao-fila"),
    estado.regioes.map((regiao) => ({ valor: regiao, rotulo: regiao })),
    "Todas as regiões",
  );
  preencherEntornos();
  montarControlesPesos(estado.pesosPadrao);
  document.getElementById("latitude").value = estado.centro.latitude.toFixed(4);
  document.getElementById("longitude").value = estado.centro.longitude.toFixed(4);
}

function preencherSelect(elemento, itens, rotuloVazio) {
  const partes = [];
  if (rotuloVazio) {
    partes.push(`<option value="">${escaparHtml(rotuloVazio)}</option>`);
  }
  itens.forEach((item) => {
    partes.push(
      `<option value="${escaparHtml(item.valor)}">${escaparHtml(item.rotulo)}</option>`,
    );
  });
  elemento.innerHTML = partes.join("");
}

function preencherEntornos() {
  const container = document.getElementById("entornos");
  container.innerHTML = estado.entornos
    .map(
      (entorno) => `<label><input type="checkbox" name="entorno" value="${escaparHtml(entorno.chave)}"> ${escaparHtml(entorno.nome)}</label>`,
    )
    .join("");
}

function desenharLegenda() {
  const container = document.getElementById("legenda");
  if (!estado.categorias.length) {
    container.style.display = "none";
    return;
  }
  container.innerHTML = estado.categorias
    .map(
      (categoria) => `<span class="legenda-item"><span class="ponto-cor" style="background:${corCategoria(categoria.chave)}"></span>${escaparHtml(categoria.nome)}</span>`,
    )
    .join("");
}

function iniciarMapa() {
  const elemento = document.getElementById("mapa");
  if (typeof L === "undefined") {
    elemento.innerHTML = '<div class="mapa-indisponivel">O mapa não carregou. A fila, a agenda e as demais listas continuam disponíveis.</div>';
    return;
  }
  estado.mapa = L.map(elemento, { zoomControl: true }).setView(
    [estado.centro.latitude, estado.centro.longitude],
    11,
  );
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(estado.mapa);
  estado.camadaMarcadores = L.layerGroup().addTo(estado.mapa);
  estado.mapa.on("click", (evento) => {
    const latitude = evento.latlng.lat;
    const longitude = evento.latlng.lng;
    document.getElementById("latitude").value = latitude.toFixed(4);
    document.getElementById("longitude").value = longitude.toFixed(4);
    atualizarMarcadorNovo(latitude, longitude);
    mostrarMensagemRelato("Local escolhido no mapa. Preencha os dados e envie.", "info");
  });
}

function atualizarMarcadorNovo(latitude, longitude) {
  if (!estado.mapa) {
    return;
  }
  if (latitude === null || longitude === null) {
    if (estado.marcadorNovo) {
      estado.mapa.removeLayer(estado.marcadorNovo);
      estado.marcadorNovo = null;
    }
    return;
  }
  const posicao = [latitude, longitude];
  if (!estado.marcadorNovo) {
    estado.marcadorNovo = L.circleMarker(posicao, {
      radius: 9,
      color: "#0c2f2b",
      weight: 3,
      fillColor: "#f0a202",
      fillOpacity: 0.9,
    }).addTo(estado.mapa);
  } else {
    estado.marcadorNovo.setLatLng(posicao);
  }
}

async function recarregarDados() {
  const resultados = await Promise.allSettled([
    carregarEstatisticas(),
    carregarMapa(),
    carregarFila(),
    carregarAgenda(),
    carregarGarantia(),
    carregarRevisoes(),
  ]);
  if (resultados.every((resultado) => resultado.status === "rejected")) {
    mostrarToast("Não foi possível carregar os dados. Verifique a API.", "erro");
  }
}

async function carregarEstatisticas() {
  const dados = await pedir("/estatisticas");
  const categoriaLider = dados.categoria_mais_frequente
    ? rotuloCategoria(dados.categoria_mais_frequente)
    : "Sem dados";
  const cartoes = [
    ["Demandas abertas", dados.demandas_abertas, `${dados.demandas_atrasadas} em atraso`],
    ["Resolvidas", dados.demandas_resolvidas, `de ${dados.total_demandas} demandas`],
    ["Relatos", dados.total_relatos, "denúncias agrupadas"],
    ["Confirmações", dados.total_confirmacoes, "apoios validados"],
    ["Categoria líder", categoriaLider, "maior volume"],
  ];
  document.getElementById("faixa-estatisticas").innerHTML = cartoes
    .map(
      (item) => `<div class="cartao-estatistica"><span>${escaparHtml(item[0])}</span><strong>${escaparHtml(item[1])}</strong><small>${escaparHtml(item[2])}</small></div>`,
    )
    .join("");
}

async function carregarMapa() {
  const dados = await pedir("/mapa?limite=1000");
  if (!estado.mapa || !estado.camadaMarcadores) {
    return;
  }
  estado.camadaMarcadores.clearLayers();
  dados.itens.forEach((demanda) => {
    const marcador = L.circleMarker([demanda.latitude, demanda.longitude], {
      radius: 6 + Math.min(8, demanda.score / 12),
      color: corCategoria(demanda.categoria),
      fillColor: corCategoria(demanda.categoria),
      fillOpacity: 0.72,
      weight: 1,
    });
    marcador.bindTooltip(
      `${escaparHtml(demanda.nome_categoria)} · score ${formatarPontuacao(demanda.score)}`,
      { direction: "top" },
    );
    marcador.on("click", () => abrirDetalhe(demanda.identificador));
    marcador.addTo(estado.camadaMarcadores);
  });
  if (!estado.mapaAjustado && dados.itens.length) {
    const limites = L.latLngBounds(
      dados.itens.map((demanda) => [demanda.latitude, demanda.longitude]),
    );
    estado.mapa.fitBounds(limites.pad(0.18), { maxZoom: 13 });
    estado.mapaAjustado = true;
  }
}

async function carregarFila() {
  const regiao = document.getElementById("filtro-regiao-fila").value;
  const parametros = new URLSearchParams();
  parametros.set("limite", "20");
  if (regiao) {
    parametros.set("regiao", regiao);
  }
  const dados = await pedir(`/demandas/top?${parametros.toString()}`);
  const escopo = regiao ? ` em ${regiao}` : "";
  const exibidas = Math.min(20, dados.itens.length);
  document.getElementById("fila-resumo").textContent = `${dados.total} demandas abertas${escopo}. Exibindo as ${exibidas} mais prioritárias.`;
  document.getElementById("tabela-fila").innerHTML = montarTabelaFila(dados.itens);
}

async function carregarAgenda() {
  const campoDias = document.getElementById("dias-agenda");
  const dias = Math.min(90, Math.max(1, Number(campoDias.value) || 7));
  campoDias.value = dias;
  const dados = await pedir(`/agenda?dias=${dias}&limite=100`);
  document.getElementById("agenda-resumo").innerHTML = [
    `<div class="resumo-item"><strong>${dados.total_atrasadas}</strong> atrasadas</div>`,
    `<div class="resumo-item"><strong>${dados.proximas.length}</strong> nos próximos ${dados.dias} dias</div>`,
    `<div class="resumo-item"><strong>${dados.alem_do_periodo}</strong> além do período</div>`,
    `<div class="resumo-item"><strong>${dados.total}</strong> demandas abertas</div>`,
  ].join("");
  document.getElementById("contagem-atrasadas").textContent = `${dados.total_atrasadas} no total`;
  document.getElementById("agenda-atrasadas").innerHTML = montarTabelaPrazo(
    dados.atrasadas,
    "Nenhuma demanda atrasada.",
  );
  document.getElementById("agenda-proximas").innerHTML = montarTabelaPrazo(
    dados.proximas,
    "Nenhum vencimento no período.",
  );
}

async function carregarGarantia() {
  const dados = await pedir("/garantia?limite=100");
  document.getElementById("garantia-resumo").innerHTML = `<div class="resumo-item"><strong>${dados.total}</strong> demandas com mais de 2× o SLA</div>`;
  document.getElementById("tabela-garantia").innerHTML = montarTabelaGarantia(dados.itens);
}

async function carregarRevisoes() {
  const dados = await pedir("/revisoes?limite=100");
  document.getElementById("revisoes-resumo").innerHTML = `<div class="resumo-item"><strong>${dados.total}</strong> relatos na fila FIFO</div>`;
  document.getElementById("tabela-revisoes").innerHTML = montarTabelaRevisoes(dados.itens);
}

function montarTabelaFila(itens) {
  if (!itens.length) {
    return vazio("Nenhuma demanda encontrada para este filtro.");
  }
  const linhas = itens
    .map(
      (demanda, indice) => `<tr>
        <td><span class="rank ${indice < 3 ? "destaque" : ""}">${indice + 1}</span></td>
        <td>${celulaProblema(demanda)}</td>
        <td><span class="pilula ${classePontuacao(demanda.score)}">${formatarPontuacao(demanda.score)}</span></td>
        <td>${formatarDataCurta(demanda.prazo)}${demanda.atrasada ? '<br><span class="texto-suave">atrasada</span>' : ""}</td>
        <td>${Math.round(demanda.dias_em_aberto)}</td>
        <td>${demanda.confirmacoes_validas}</td>
        <td>${celulaStatus(demanda.status)}</td>
        <td><button type="button" class="link-detalhe" data-detalhe="${demanda.identificador}">Detalhar</button></td>
      </tr>`,
    )
    .join("");
  return `<table class="tabela">
    <thead><tr><th>#</th><th>Problema</th><th>Score</th><th>Prazo</th><th>Dias</th><th>Confirmações</th><th>Status</th><th></th></tr></thead>
    <tbody>${linhas}</tbody>
  </table>`;
}

function montarTabelaPrazo(itens, mensagemVazia) {
  if (!itens.length) {
    return vazio(mensagemVazia);
  }
  const linhas = itens
    .map(
      (demanda) => `<tr>
        <td>${celulaProblema(demanda)}</td>
        <td><span class="pilula ${classePontuacao(demanda.score)}">${formatarPontuacao(demanda.score)}</span></td>
        <td>${formatarDataCurta(demanda.prazo)}</td>
        <td>${Math.round(demanda.dias_em_aberto)}</td>
        <td>${demanda.confirmacoes_validas}</td>
        <td>${celulaStatus(demanda.status)}</td>
        <td><button type="button" class="link-detalhe" data-detalhe="${demanda.identificador}">Detalhar</button></td>
      </tr>`,
    )
    .join("");
  return `<table class="tabela">
    <thead><tr><th>Problema</th><th>Score</th><th>Prazo</th><th>Dias em aberto</th><th>Confirmações</th><th>Status</th><th></th></tr></thead>
    <tbody>${linhas}</tbody>
  </table>`;
}

function montarTabelaGarantia(itens) {
  if (!itens.length) {
    return vazio("Nenhuma demanda ultrapassou duas vezes o SLA.");
  }
  const linhas = itens
    .map(
      (demanda) => `<tr>
        <td>${celulaProblema(demanda)}</td>
        <td><span class="pilula ${classePontuacao(demanda.score)}">${formatarPontuacao(demanda.score)}</span></td>
        <td>${Math.round(demanda.dias_em_aberto)}</td>
        <td>${demanda.sla_dias}</td>
        <td>${Math.max(0, Math.round(demanda.dias_em_aberto - 2 * demanda.sla_dias))}</td>
        <td>${celulaStatus(demanda.status)}</td>
        <td><button type="button" class="link-detalhe" data-detalhe="${demanda.identificador}">Detalhar</button></td>
      </tr>`,
    )
    .join("");
  return `<table class="tabela">
    <thead><tr><th>Problema</th><th>Score</th><th>Dias em aberto</th><th>SLA</th><th>Excesso</th><th>Status</th><th></th></tr></thead>
    <tbody>${linhas}</tbody>
  </table>`;
}

function montarTabelaRevisoes(itens) {
  if (!itens.length) {
    return vazio("Nenhum relato pendente de revisão.");
  }
  const linhas = itens
    .map((item) => {
      const descricao = item.descricao || "Sem descrição";
      return `<tr>
        <td><span class="descricao-curta" title="${escaparHtml(descricao)}">${escaparHtml(descricao)}</span></td>
        <td>${escaparHtml(rotuloCategoria(item.categoria_demanda))}</td>
        <td>${escaparHtml(rotuloCategoria(item.categoria_sugerida))}</td>
        <td>${Math.round(item.confianca_classificacao * 100)}%</td>
        <td>${item.gravidade}/5</td>
        <td>${escaparHtml(item.regiao || "Não informada")}</td>
        <td>${formatarDataCurta(item.criado_em)}</td>
        <td><button type="button" class="botao secundario pequeno" data-concluir-revisao="${item.id}">Concluir</button></td>
      </tr>`;
    })
    .join("");
  return `<table class="tabela">
    <thead><tr><th>Descrição</th><th>Categoria atual</th><th>Sugestão</th><th>Confiança</th><th>Gravidade</th><th>Região</th><th>Criado em</th><th></th></tr></thead>
    <tbody>${linhas}</tbody>
  </table>`;
}

function celulaProblema(demanda) {
  return `<div class="categoria-celula"><span class="ponto-cor" style="background:${corCategoria(demanda.categoria)}"></span>${escaparHtml(demanda.nome_categoria)}</div><span class="texto-suave">${escaparHtml(demanda.regiao)}</span>`;
}

function celulaStatus(status) {
  return `<span class="status status-${status}">${rotuloStatus(status)}</span>`;
}

async function concluirRevisao(botao) {
  botao.disabled = true;
  try {
    await pedir(`/revisoes/${botao.dataset.concluirRevisao}/concluir`, {
      method: "POST",
      headers: { "X-Token-Gestor": obterTokenGestor() },
    });
    mostrarToast("Revisão concluída.", "sucesso");
    await carregarRevisoes();
  } catch (erro) {
    mostrarToast(erro.message, "erro");
    botao.disabled = false;
  }
}

async function enviarRelato(evento) {
  evento.preventDefault();
  const botao = evento.target.querySelector('button[type="submit"]');
  botao.disabled = true;
  const entornos = Array.from(
    document.querySelectorAll('input[name="entorno"]:checked'),
  ).map((campo) => campo.value);
  const dados = {
    token_cidadao: tokenCidadao(),
    categoria: document.getElementById("categoria").value || null,
    gravidade: Number(document.getElementById("gravidade").value),
    descricao: document.getElementById("descricao").value.trim(),
    latitude: Number(document.getElementById("latitude").value),
    longitude: Number(document.getElementById("longitude").value),
    regiao: document.getElementById("regiao").value || null,
    entornos,
  };
  try {
    const resposta = await pedir("/relatos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
    const confianca = Math.round(resposta.classificacao.confianca * 100);
    const sugestao = rotuloCategoria(resposta.classificacao.categoria_sugerida);
    mostrarMensagemRelato(
      `${resposta.mensagem} Sugestão: ${sugestao} (${confianca}% de confiança).`,
      "sucesso",
    );
    document.getElementById("descricao").value = "";
    atualizarMarcadorNovo(null);
    await recarregarDados();
    await abrirDetalhe(resposta.demanda.identificador);
  } catch (erro) {
    mostrarMensagemRelato(erro.message, "erro");
  } finally {
    botao.disabled = false;
  }
}

async function usarLocalizacao() {
  mostrarMensagemRelato("Buscando sua localização...", "info");
  try {
    const posicao = await obterPosicao();
    const latitude = posicao.coords.latitude;
    const longitude = posicao.coords.longitude;
    document.getElementById("latitude").value = latitude.toFixed(4);
    document.getElementById("longitude").value = longitude.toFixed(4);
    atualizarMarcadorNovo(latitude, longitude);
    if (estado.mapa) {
      estado.mapa.setView([latitude, longitude], 16);
    }
    mostrarMensagemRelato("Localização obtida. Ajuste o ponto no mapa se necessário.", "sucesso");
  } catch (erro) {
    mostrarMensagemRelato(
      "Não foi possível obter a localização. Informe as coordenadas ou clique no mapa.",
      "erro",
    );
  }
}

function obterPosicao() {
  return new Promise((resolver, rejeitar) => {
    if (!navigator.geolocation) {
      rejeitar(new Error("Geolocalização indisponível."));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolver, rejeitar, {
      enableHighAccuracy: true,
      timeout: 6000,
      maximumAge: 30000,
    });
  });
}

function montarControlesPesos(pesos) {
  const container = document.getElementById("pesos-simulacao");
  container.innerHTML = Object.entries(COMPONENTES)
    .map(([chave, nome]) => {
      const valor = Math.round((pesos[chave] || 0) * 100);
      return `<label class="controle-peso">
        <span>${escaparHtml(nome)} <output data-saida-peso="${chave}">${valor}%</output></span>
        <input type="range" min="0" max="100" step="5" value="${valor}" data-peso="${chave}">
      </label>`;
    })
    .join("");
  container.querySelectorAll("input[data-peso]").forEach((controle) => {
    controle.addEventListener("input", () => {
      const saida = container.querySelector(`[data-saida-peso="${controle.dataset.peso}"]`);
      saida.textContent = `${controle.value}%`;
    });
  });
}

async function simular(evento, silencioso = false) {
  if (evento) {
    evento.preventDefault();
  }
  const pesos = {};
  document.querySelectorAll("#pesos-simulacao input[data-peso]").forEach((controle) => {
    pesos[controle.dataset.peso] = Number(controle.value) / 100;
  });
  try {
    const dados = await pedir("/simulacao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pesos }),
    });
    const chips = Object.keys(dados.pesos)
      .map(
        (chave) => `<span class="peso-chip">${escaparHtml(COMPONENTES[chave] || chave)}: ${Math.round(dados.pesos[chave] * 100)}%</span>`,
      )
      .join("");
    document.getElementById("resumo-simulacao").innerHTML = `<strong>Pesos normalizados</strong><div class="pesos-resultado">${chips}</div><span class="texto-suave">Ranking recalculado sem alterar o banco.</span>`;
    document.getElementById("tabela-simulacao").innerHTML = montarTabelaFila(dados.itens);
    if (!silencioso) {
      mostrarToast("Simulação recalculada.", "sucesso");
    }
  } catch (erro) {
    if (!silencioso) {
      mostrarToast(erro.message, "erro");
    }
  }
}

function restaurarPesos() {
  montarControlesPesos(estado.pesosPadrao);
  simular(null, true);
  mostrarToast("Pesos padrão restaurados.", "info");
}

async function abrirDetalhe(identificador) {
  try {
    const demanda = await pedir(`/demandas/${identificador}`);
    estado.demandaAtual = demanda;
    document.getElementById("corpo-modal").innerHTML = montarDetalhe(demanda);
    document.getElementById("modal").classList.remove("escondido");
    document.body.classList.add("sem-rolagem");
    configurarAcoesDetalhe(demanda);
    document.getElementById("fechar-modal").focus();
  } catch (erro) {
    mostrarToast(erro.message, "erro");
  }
}

function fecharModal() {
  document.getElementById("modal").classList.add("escondido");
  document.body.classList.remove("sem-rolagem");
  estado.demandaAtual = null;
}

function renderizarDetalhe(demanda) {
  document.getElementById("corpo-modal").innerHTML = montarDetalhe(demanda);
  configurarAcoesDetalhe(demanda);
}

function montarDetalhe(demanda) {
  const cor = corCategoria(demanda.categoria);
  const entornos = (demanda.entornos || [])
    .map((chave) => {
      const encontrado = estado.entornos.find((entorno) => entorno.chave === chave);
      return encontrado ? encontrado.nome : chave;
    })
    .join(", ") || "Não informado";
  const transicoes = TRANSICOES[demanda.status] || [];
  const opcoesStatus = transicoes.length
    ? transicoes
        .map((status) => {
          const rotulo = demanda.status === "resolvida" && status === "aberta"
            ? "Reabrir demanda"
            : rotuloStatus(status);
          return `<option value="${status}">${escaparHtml(rotulo)}</option>`;
        })
        .join("")
    : '<option value="">Sem transição disponível</option>';
  const componentes = Object.entries(COMPONENTES)
    .map(([chave, nome]) => {
      const valor = Math.min(1, Math.max(0, Number(demanda.componentes[chave] || 0)));
      return `<div class="componente-linha">
        <div class="componente-topo"><span>${escaparHtml(nome)}</span><span>${Math.round(valor * 100)}%</span></div>
        <div class="barra"><div class="barra-preenchimento" style="width:${valor * 100}%"></div></div>
      </div>`;
    })
    .join("");
  const relatos = (demanda.relatos || []).length
    ? demanda.relatos.map(montarRelato).join("")
    : vazio("Nenhum relato registrado.");
  const eventos = (demanda.eventos || []).length
    ? demanda.eventos
        .map(
          (evento) => `<div class="evento"><span><strong>${rotuloStatus(evento.status_novo)}</strong> · ${formatarData(evento.criado_em)} · ${escaparHtml(evento.ator)}</span></div>`,
        )
        .join("")
    : vazio("Nenhum evento registrado.");
  const historico = (demanda.historico || []).length
    ? demanda.historico
        .slice(0, 6)
        .map(
          (registro) => `<span>${formatarDataCurta(registro.criado_em)}: ${formatarPontuacao(registro.score)}</span>`,
        )
        .join("")
    : '<span class="texto-suave">Sem histórico.</span>';
  const botoesDesabilitados = transicoes.length ? "" : "disabled";
  const confirmacaoDesabilitada = demanda.status === "resolvida" ? "disabled" : "";
  return `<div class="detalhe-topo" style="border-left-color:${cor}">
    <div>
      <div class="detalhe-etiquetas">
        <span class="pilula" style="background:${cor}22;color:${cor}">${escaparHtml(demanda.nome_categoria)}</span>
        ${celulaStatus(demanda.status)}
      </div>
      <h2>Demanda #${demanda.identificador}</h2>
      <p>${escaparHtml(demanda.regiao)} · aberta em ${formatarData(demanda.iniciada_em)} · SLA de ${demanda.sla_dias} dias</p>
    </div>
    <div class="score-destaque">
      <strong>${formatarPontuacao(demanda.score)}</strong>
      <span>score de prioridade</span>
    </div>
  </div>
  <div class="meta-grade">
    <div class="meta-item"><span>Prazo</span><strong>${formatarDataCurta(demanda.prazo)}</strong></div>
    <div class="meta-item"><span>Situação do prazo</span><strong>${demanda.atrasada ? "Atrasada" : "No prazo"}</strong></div>
    <div class="meta-item"><span>Dias em aberto</span><strong>${Math.round(demanda.dias_em_aberto)}</strong></div>
    <div class="meta-item"><span>Confirmações</span><strong>${demanda.confirmacoes_validas}</strong></div>
    <div class="meta-item"><span>Relatos</span><strong>${demanda.relatos_count}</strong></div>
    <div class="meta-item"><span>Gravidade</span><strong>${demanda.gravidade}/5</strong></div>
    <div class="meta-item"><span>Reaberturas</span><strong>${demanda.reaberturas}</strong></div>
    <div class="meta-item"><span>Entornos</span><strong>${escaparHtml(entornos)}</strong></div>
  </div>
  <div class="acoes-detalhe">
    <label for="status-detalhe">Novo status
      <select id="status-detalhe">${opcoesStatus}</select>
    </label>
    <button type="button" class="botao primario" id="botao-status" ${botoesDesabilitados}>Atualizar status</button>
    <button type="button" class="botao secundario" id="botao-confirmar" ${confirmacaoDesabilitada}>Confirmar problema</button>
  </div>
  <div class="secao-detalhe">
    <h3>Como o score foi calculado</h3>
    <div class="componentes">${componentes}</div>
  </div>
  <div class="secao-detalhe">
    <h3>Relatos agrupados</h3>
    <div class="lista-relatos">${relatos}</div>
  </div>
  <div class="secao-detalhe">
    <h3>Histórico de status</h3>
    <div class="linha-tempo">${eventos}</div>
  </div>
  <div class="secao-detalhe">
    <h3>Histórico do score</h3>
    <div class="historico-score">${historico}</div>
  </div>`;
}

function montarRelato(relato) {
  const descricao = relato.descricao
    ? escaparHtml(relato.descricao)
    : "<em>Sem descrição.</em>";
  const confianca = Math.round((relato.confianca_classificacao || 0) * 100);
  return `<div class="relato-item">
    <p>${descricao}</p>
    <div class="relato-meta">
      <span>Sugestão: ${escaparHtml(rotuloCategoria(relato.categoria_sugerida))} (${confianca}%)</span>
      <span>Categoria: ${escaparHtml(rotuloCategoria(relato.categoria_escolhida))}</span>
      <span>Gravidade ${relato.gravidade}/5</span>
      <span>${formatarData(relato.criado_em)}</span>
      ${relato.revisado ? "<span>revisado</span>" : ""}
    </div>
  </div>`;
}

function configurarAcoesDetalhe(demanda) {
  const botaoStatus = document.getElementById("botao-status");
  if (botaoStatus) {
    botaoStatus.addEventListener("click", () => atualizarStatus(demanda.identificador));
  }
  const botaoConfirmar = document.getElementById("botao-confirmar");
  if (botaoConfirmar) {
    botaoConfirmar.addEventListener("click", () => confirmarDemanda(demanda));
  }
}

async function atualizarStatus(identificador) {
  const seletor = document.getElementById("status-detalhe");
  if (!seletor || !seletor.value) {
    return;
  }
  const botao = document.getElementById("botao-status");
  if (botao) {
    botao.disabled = true;
  }
  try {
    const resposta = await pedir(`/demandas/${identificador}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Token-Gestor": obterTokenGestor(),
      },
      body: JSON.stringify({ status: seletor.value, ator: "gestor" }),
    });
    estado.demandaAtual = resposta.demanda;
    renderizarDetalhe(resposta.demanda);
    mostrarToast("Status atualizado.", "sucesso");
    await recarregarDados();
  } catch (erro) {
    mostrarToast(erro.message, "erro");
    if (botao) {
      botao.disabled = false;
    }
  }
}

async function confirmarDemanda(demanda) {
  const botao = document.getElementById("botao-confirmar");
  if (botao) {
    botao.disabled = true;
  }
  let latitude = demanda.centroide_latitude;
  let longitude = demanda.centroide_longitude;
  let localizada = false;
  try {
    const posicao = await obterPosicao();
    latitude = posicao.coords.latitude;
    longitude = posicao.coords.longitude;
    localizada = true;
  } catch (erro) {
    localizada = false;
  }
  try {
    const resposta = await pedir(`/demandas/${demanda.identificador}/confirmacoes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token_cidadao: tokenCidadao(),
        latitude,
        longitude,
      }),
    });
    estado.demandaAtual = resposta.demanda;
    renderizarDetalhe(resposta.demanda);
    mostrarToast(
      localizada
        ? "Confirmação registrada."
        : "Confirmação registrada com o ponto da demanda.",
      "sucesso",
    );
    await recarregarDados();
  } catch (erro) {
    mostrarToast(erro.message, "erro");
    if (botao) {
      botao.disabled = false;
    }
  }
}

async function pedir(caminho, opcoes = {}) {
  const resposta = await fetch(`/api${caminho}`, opcoes);
  let dados = null;
  try {
    dados = await resposta.json();
  } catch (erro) {
    dados = null;
  }
  if (!resposta.ok) {
    const detalhe = dados && dados.detail ? dados.detail : `Erro ${resposta.status}`;
    throw new Error(
      typeof detalhe === "string"
        ? detalhe
        : "Não foi possível concluir a operação.",
    );
  }
  return dados;
}

function mostrarMensagemRelato(texto, tipo) {
  const elemento = document.getElementById("mensagem-relato");
  elemento.textContent = texto;
  elemento.className = `mensagem ${tipo || ""}`.trim();
}

function mostrarToast(mensagem, tipo = "info") {
  const container = document.getElementById("toasts");
  const elemento = document.createElement("div");
  elemento.className = `toast ${tipo}`;
  elemento.textContent = mensagem;
  container.appendChild(elemento);
  setTimeout(() => {
    elemento.remove();
  }, 4500);
}

function tratarErro(erro) {
  mostrarToast(erro.message || "Falha inesperada.", "erro");
}

function escaparHtml(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (caractere) => {
    const mapa = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return mapa[caractere];
  });
}

function vazio(mensagem) {
  return `<div class="vazio">${escaparHtml(mensagem)}</div>`;
}

function corCategoria(chave) {
  return CORES_CATEGORIAS[chave] || CORES_CATEGORIAS.outros;
}

function rotuloCategoria(chave) {
  const encontrada = estado.categorias.find((categoria) => categoria.chave === chave);
  return encontrada ? encontrada.nome : chave || "Outros";
}

function rotuloStatus(status) {
  return NOMES_STATUS[status] || status;
}

function classePontuacao(valor) {
  if (valor >= 70) {
    return "score-alto";
  }
  if (valor >= 45) {
    return "score-medio";
  }
  return "score-baixo";
}

function formatarPontuacao(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) {
    return "0,0";
  }
  return numero.toFixed(1).replace(".", ",");
}

function formatarData(texto) {
  const data = new Date(texto);
  if (Number.isNaN(data.getTime())) {
    return "—";
  }
  return data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function formatarDataCurta(texto) {
  const data = new Date(texto);
  if (Number.isNaN(data.getTime())) {
    return "—";
  }
  return data.toLocaleDateString("pt-BR", { dateStyle: "short" });
}
