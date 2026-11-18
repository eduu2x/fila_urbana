from datetime import datetime, timedelta, timezone

import pytest

from app.utilidades import (
    adicionar_dias,
    calcular_celula,
    celulas_vizinhas,
    de_iso,
    dias_desde,
    distancia_metros,
    normalizar_texto,
    para_iso,
)


def test_normalizar_texto_remove_acentos_e_espacos():
    assert normalizar_texto("  Iluminação PÚBLICA  ") == "iluminacao publica"
    assert normalizar_texto(None) == ""
    assert normalizar_texto("") == ""


def test_distancia_metros_mesmo_ponto():
    assert distancia_metros(-23.55, -46.63, -23.55, -46.63) == 0.0


def test_distancia_metros_um_grau_de_latitude():
    distancia = distancia_metros(0.0, 0.0, 1.0, 0.0)
    assert distancia == pytest.approx(111195, rel=0.01)


def test_calcular_celula_usa_floor():
    assert calcular_celula(-23.5505, -46.6333, "buraco") == (
        "-11776:-23317:buraco"
    )


def test_celulas_vizinhas_sao_nove_e_incluem_centro():
    chaves = celulas_vizinhas(-23.5505, -46.6333, "buraco")
    assert len(chaves) == 9
    assert len(set(chaves)) == 9
    assert calcular_celula(-23.5505, -46.6333, "buraco") in chaves


def test_celulas_vizinhas_cruzam_fronteira_da_grade():
    chaves = celulas_vizinhas(0.0019, 0.0019, "lixo")
    assert "0:0:lixo" in chaves
    assert "-1:-1:lixo" in chaves
    assert "1:1:lixo" in chaves


def test_datas_ida_e_volta():
    momento = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    texto = para_iso(momento)
    assert de_iso(texto) == momento
    assert de_iso("2026-11-18T12:00:00") == momento
    assert dias_desde(texto, momento) == 0.0
    assert de_iso(adicionar_dias(texto, 3)) == momento + timedelta(days=3)


def test_dias_desde_nao_fica_negativo():
    momento = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    futuro = para_iso(momento + timedelta(days=5))
    assert dias_desde(futuro, momento) == 0.0
