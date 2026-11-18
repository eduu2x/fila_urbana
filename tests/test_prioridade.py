from datetime import datetime, timezone

import pytest

from app.config import PESOS_PADRAO
from app.prioridade import calcular_componentes, normalizar_pesos

AGORA = datetime(2026, 11, 18, tzinfo=timezone.utc)


def montar_demanda(**alteracoes):
    demanda = {
        "gravidade": 4,
        "categoria": "buraco",
        "sla_dias": 7,
        "iniciada_em": "2026-11-01T00:00:00+00:00",
        "confirmacoes_validas": 5,
        "ocorrencias_90_dias": 3,
        "entornos": ["escola", "via_arterial"],
    }
    demanda.update(alteracoes)
    return demanda


def test_normalizar_pesos_padrao():
    assert normalizar_pesos({}) == PESOS_PADRAO
    assert normalizar_pesos(None) == PESOS_PADRAO


def test_normalizar_pesos_soma_um():
    pesos = normalizar_pesos({"gravidade": 3, "risco": 1})
    assert pesos["gravidade"] == pytest.approx(0.75)
    assert pesos["risco"] == pytest.approx(0.25)
    assert pesos["tempo"] == 0.0
    assert sum(pesos.values()) == pytest.approx(1.0)


def test_normalizar_pesos_ignora_invalidos():
    pesos = normalizar_pesos(
        {
            "gravidade": -5,
            "risco": float("nan"),
            "tempo": 2,
            "desconhecido": 10,
        }
    )
    assert pesos["gravidade"] == 0.0
    assert pesos["risco"] == 0.0
    assert pesos["tempo"] == 1.0
    assert "desconhecido" not in pesos
    assert sum(pesos.values()) == pytest.approx(1.0)


def test_normalizar_pesos_todos_zero_voltam_ao_padrao():
    pesos = normalizar_pesos(
        {"gravidade": 0, "risco": 0, "tempo": 0, "confirmacoes": 0}
    )
    assert pesos == PESOS_PADRAO


def test_score_conhecido():
    pontuacao, componentes = calcular_componentes(montar_demanda(), AGORA)
    assert pontuacao == pytest.approx(79.38, abs=0.01)
    assert componentes["gravidade"] == pytest.approx(0.75)
    assert componentes["risco"] == 1.0
    assert componentes["tempo"] == 1.0
    assert componentes["confirmacoes"] == pytest.approx(0.625)
    assert componentes["recorrencia"] == pytest.approx(0.3)
    assert componentes["categoria"] == pytest.approx(0.9)


def test_gravidade_e_limitada_entre_um_e_cinco():
    baixa, _ = calcular_componentes(montar_demanda(gravidade=-3), AGORA)
    alta, componentes = calcular_componentes(montar_demanda(gravidade=10), AGORA)
    assert componentes["gravidade"] == 1.0
    assert alta > baixa


def test_tempo_satura_no_dobro_do_sla():
    recente, componentes_recente = calcular_componentes(
        montar_demanda(iniciada_em="2026-11-18T00:00:00+00:00"),
        AGORA,
    )
    antiga, componentes_antiga = calcular_componentes(
        montar_demanda(iniciada_em="2026-06-01T00:00:00+00:00"),
        AGORA,
    )
    assert componentes_recente["tempo"] == 0.0
    assert componentes_antiga["tempo"] == 1.0
    assert antiga > recente


def test_risco_satura_em_um():
    _, componentes = calcular_componentes(
        montar_demanda(
            entornos=["escola", "hospital", "ponto_onibus", "via_arterial"]
        ),
        AGORA,
    )
    assert componentes["risco"] == 1.0


def test_confirmacoes_e_recorrencia_saturam():
    _, componentes = calcular_componentes(
        montar_demanda(confirmacoes_validas=1000, ocorrencias_90_dias=99),
        AGORA,
    )
    assert componentes["confirmacoes"] == pytest.approx(1000 / 1003)
    assert componentes["recorrencia"] == 1.0


def test_pesos_alteram_o_resultado():
    score_tempo, _ = calcular_componentes(
        montar_demanda(),
        AGORA,
        {"tempo": 1},
    )
    score_gravidade, _ = calcular_componentes(
        montar_demanda(),
        AGORA,
        {"gravidade": 1},
    )
    assert score_tempo == pytest.approx(100.0)
    assert score_gravidade == pytest.approx(75.0)
