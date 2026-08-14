"""Licença mensal Ultramed → Rinan Code (separada do financeiro da clínica)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from .models import FaturaLicencaSistema

LICENCA_VALOR_MENSAL = Decimal("399.00")
LICENCA_DIA_VENCIMENTO = 10
LICENCA_REF_PREFIX = "licenca-"


def valor_licenca_mensal() -> Decimal:
    raw = getattr(settings, "LICENCA_RINAN_VALOR", None)
    try:
        if raw is not None and str(raw).strip() != "":
            return Decimal(str(raw))
    except Exception:
        pass
    return LICENCA_VALOR_MENSAL


def dia_vencimento_licenca() -> int:
    try:
        d = int(getattr(settings, "LICENCA_RINAN_DIA_VENCIMENTO", LICENCA_DIA_VENCIMENTO))
        return min(28, max(1, d))
    except (TypeError, ValueError):
        return LICENCA_DIA_VENCIMENTO


def referencia_competencia(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}"


def vencimento_competencia(ano: int, mes: int) -> date:
    return date(ano, mes, dia_vencimento_licenca())


def rinan_mp_configurado() -> bool:
    token = (getattr(settings, "MERCADO_PAGO_RINAN_ACCESS_TOKEN", "") or "").strip()
    return bool(token)


def rinan_mp_public_key() -> str:
    return (getattr(settings, "MERCADO_PAGO_RINAN_PUBLIC_KEY", "") or "").strip()


def rinan_mp_checkout_ok() -> bool:
    return rinan_mp_configurado() and bool(rinan_mp_public_key())


def sincronizar_status_fatura(fatura: FaturaLicencaSistema, hoje: date | None = None) -> FaturaLicencaSistema:
    hoje = hoje or timezone.now().date()
    if fatura.status == "PAGO":
        return fatura
    novo = "ATRASADO" if fatura.data_vencimento < hoje else "PENDENTE"
    if fatura.status != novo:
        fatura.status = novo
        fatura.save(update_fields=["status", "atualizado_em"])
    return fatura


def garantir_fatura_competencia(ano: int, mes: int) -> FaturaLicencaSistema:
    ref = referencia_competencia(ano, mes)
    fatura, created = FaturaLicencaSistema.objects.get_or_create(
        referencia=ref,
        defaults={
            "valor": valor_licenca_mensal(),
            "data_vencimento": vencimento_competencia(ano, mes),
            "status": "PENDENTE",
        },
    )
    if not created and fatura.status != "PAGO":
        # Mantém valor/vencimento coerentes se ainda aberta
        mudou = False
        esperado_venc = vencimento_competencia(ano, mes)
        if fatura.data_vencimento != esperado_venc:
            fatura.data_vencimento = esperado_venc
            mudou = True
        if fatura.valor != valor_licenca_mensal():
            fatura.valor = valor_licenca_mensal()
            mudou = True
        if mudou:
            fatura.save(update_fields=["data_vencimento", "valor", "atualizado_em"])
    return sincronizar_status_fatura(fatura)


def garantir_faturas_licenca(hoje: date | None = None) -> FaturaLicencaSistema:
    """Garante a fatura do mês corrente (vencimento no dia 10)."""
    hoje = hoje or timezone.now().date()
    return sincronizar_status_fatura(garantir_fatura_competencia(hoje.year, hoje.month))


def fatura_aberta_atual(hoje: date | None = None) -> FaturaLicencaSistema | None:
    hoje = hoje or timezone.now().date()
    garantir_faturas_licenca(hoje)
    return (
        FaturaLicencaSistema.objects.exclude(status="PAGO")
        .order_by("data_vencimento", "id")
        .first()
    )


def marcar_licenca_paga(fatura: FaturaLicencaSistema, payment_id: str | None = None, observacao: str | None = None):
    fatura.status = "PAGO"
    fatura.data_pagamento = timezone.now().date()
    if payment_id:
        fatura.mercadopago_id = str(payment_id)
    if observacao:
        fatura.observacao = observacao
    fatura.save()
    return fatura


def external_reference_licenca(fatura_id: int) -> str:
    return f"{LICENCA_REF_PREFIX}{int(fatura_id)}"


def parse_external_reference_licenca(ref: str | None) -> int | None:
    if not ref:
        return None
    ref = str(ref).strip()
    if not ref.startswith(LICENCA_REF_PREFIX):
        return None
    try:
        return int(ref[len(LICENCA_REF_PREFIX) :])
    except ValueError:
        return None
