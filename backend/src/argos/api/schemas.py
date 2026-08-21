"""Schemas exclusivos do transporte HTTP."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class TelegramUserInput(BaseModel):
    """Identidade mínima usada para definir o proprietário do update."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)


class TelegramPrivateChatInput(BaseModel):
    """Chat privado aceito pelo MVP."""

    model_config = ConfigDict(extra="ignore")

    id: int
    type: Literal["private"]


class TelegramTextMessageInput(BaseModel):
    """Subconjunto fechado de uma mensagem de texto do Telegram."""

    model_config = ConfigDict(extra="ignore")

    message_id: int = Field(gt=0)
    sender: TelegramUserInput = Field(alias="from")
    chat: TelegramPrivateChatInput
    text: str = Field(min_length=1, max_length=4_096)


class TelegramUpdateInput(BaseModel):
    """Único tipo de update aceito no primeiro bloco do webhook."""

    model_config = ConfigDict(extra="ignore")

    update_id: int = Field(ge=0)
    message: TelegramTextMessageInput
