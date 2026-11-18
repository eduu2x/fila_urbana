from pydantic import BaseModel, Field


class RelatoEntrada(BaseModel):
    token_cidadao: str | None = Field(default=None, max_length=64)
    categoria: str | None = Field(default=None, max_length=30)
    gravidade: int = Field(default=1, ge=1, le=5)
    descricao: str = Field(default="", max_length=500)
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    regiao: str | None = Field(default=None, max_length=40)
    entornos: list[str] = Field(default_factory=list)


class ConfirmacaoEntrada(BaseModel):
    token_cidadao: str = Field(min_length=1, max_length=64)
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class StatusEntrada(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    ator: str = Field(default="gestor", max_length=60)


class SimulacaoEntrada(BaseModel):
    pesos: dict[str, float] = Field(default_factory=dict)
