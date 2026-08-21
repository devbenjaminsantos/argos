"""Entrada HTTP autenticada para updates do Telegram."""

import json
import secrets
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError

from argos.api.schemas import TelegramUpdateInput
from argos.config import Settings

router = APIRouter(prefix="/webhooks", tags=["telegram"])

_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def _authenticate(request: Request, settings: Settings) -> None:
    configured = settings.telegram_webhook_secret
    if configured is None:
        raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE)

    received = request.headers.get(_SECRET_HEADER, "")
    expected = configured.get_secret_value()
    if not received or not secrets.compare_digest(received, expected):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)


async def _read_limited_json(request: Request, maximum_bytes: int) -> object:
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", maxsplit=1)[0].strip().lower() != "application/json":
        raise HTTPException(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            if int(declared_length) > maximum_bytes:
                raise HTTPException(status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except ValueError as error:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST) from error

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > maximum_bytes:
            raise HTTPException(status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST) from error


@router.post("/telegram", status_code=HTTPStatus.SERVICE_UNAVAILABLE)
async def receive_telegram_update(request: Request) -> Response:
    """Valida a entrega sem confirmá-la antes de existir persistência."""

    settings: Settings = request.app.state.settings
    _authenticate(request, settings)
    payload = await _read_limited_json(
        request,
        settings.telegram_webhook_max_body_bytes,
    )

    try:
        TelegramUpdateInput.model_validate(payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY
        ) from error

    raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE)
