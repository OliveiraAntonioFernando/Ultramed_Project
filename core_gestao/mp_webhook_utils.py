"""Validação de assinatura de webhooks Mercado Pago."""
import hashlib
import hmac
import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)


def _parse_x_signature(header: str) -> tuple[str, str]:
    ts = ""
    v1 = ""
    for part in (header or "").split(","):
        part = part.strip()
        if part.startswith("ts="):
            ts = part[3:]
        elif part.startswith("v1="):
            v1 = part[3:]
    return ts, v1


def validar_assinatura_webhook_mp(request, payment_id: str | None) -> bool:
    """
    Valida x-signature do Mercado Pago quando MERCADO_PAGO_WEBHOOK_SECRET está definido.
    Se o secret não estiver configurado, aceita (confirmação via API MP no handler).
    """
    secret = (getattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "") or "").strip()
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")

    if not secret:
        if x_signature:
            logger.warning("Webhook MP com assinatura, mas MERCADO_PAGO_WEBHOOK_SECRET ausente.")
        return True

    if not x_signature or not payment_id:
        logger.warning("Webhook MP rejeitado: assinatura ou payment_id ausente.")
        return False

    ts, v1 = _parse_x_signature(x_signature)
    if not ts or not v1:
        logger.warning("Webhook MP rejeitado: x-signature malformado.")
        return False

    manifest = f"id:{payment_id};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(
        secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, v1):
        logger.warning("Webhook MP rejeitado: assinatura inválida.")
        return False
    return True
