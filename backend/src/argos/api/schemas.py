"""Schemas exclusivos do transporte HTTP."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Resposta pública de liveness, sem detalhes de infraestrutura."""

    status: Literal["ok"] = "ok"
    service: Literal["argos"] = "argos"
    version: str


class ErrorDetail(BaseModel):
    """Detalhes seguros e estáveis de uma falha HTTP."""

    code: str
    message: str
    correlation_id: str


class ErrorResponse(BaseModel):
    """Envelope comum para respostas de erro."""

    error: ErrorDetail
