from datetime import datetime, timedelta, timezone
import math
import unicodedata

from app.config import PASSO_GRADE


def agora_utc():
    return datetime.now(timezone.utc)


def para_iso(momento):
    return momento.astimezone(timezone.utc).isoformat()


def de_iso(texto):
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento


def dias_desde(texto_iso, agora=None):
    if agora is None:
        agora = agora_utc()
    inicio = de_iso(texto_iso)
    return max(0.0, (agora - inicio).total_seconds() / 86400.0)


def adicionar_dias(texto_iso, dias):
    return para_iso(de_iso(texto_iso) + timedelta(days=dias))


def normalizar_texto(texto):
    texto = texto or ""
    decomposto = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(
        caractere
        for caractere in decomposto
        if unicodedata.category(caractere) != "Mn"
    )
    return sem_acento.lower().strip()


def distancia_metros(latitude1, longitude1, latitude2, longitude2):
    raio_terra = 6371000.0
    latitude1_rad = math.radians(latitude1)
    latitude2_rad = math.radians(latitude2)
    delta_latitude = math.radians(latitude2 - latitude1)
    delta_longitude = math.radians(longitude2 - longitude1)
    seno_latitude = math.sin(delta_latitude / 2.0)
    seno_longitude = math.sin(delta_longitude / 2.0)
    termo = (
        seno_latitude * seno_latitude
        + math.cos(latitude1_rad)
        * math.cos(latitude2_rad)
        * seno_longitude
        * seno_longitude
    )
    termo = min(1.0, max(0.0, termo))
    return 2.0 * raio_terra * math.asin(math.sqrt(termo))


def calcular_celula(latitude, longitude, categoria):
    indice_latitude = math.floor(latitude / PASSO_GRADE)
    indice_longitude = math.floor(longitude / PASSO_GRADE)
    return f"{indice_latitude}:{indice_longitude}:{categoria}"


def celulas_vizinhas(latitude, longitude, categoria):
    indice_latitude = math.floor(latitude / PASSO_GRADE)
    indice_longitude = math.floor(longitude / PASSO_GRADE)
    chaves = []
    for deslocamento_latitude in (-1, 0, 1):
        for deslocamento_longitude in (-1, 0, 1):
            chave = (
                f"{indice_latitude + deslocamento_latitude}:"
                f"{indice_longitude + deslocamento_longitude}:{categoria}"
            )
            chaves.append(chave)
    return chaves
