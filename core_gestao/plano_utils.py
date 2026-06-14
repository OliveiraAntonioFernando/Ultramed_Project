"""Regras de plano, checkout e descontos — Ultramed."""
import re
import unicodedata

from django.core import signing
from django.utils import timezone

from core_gestao.models import Plano, Prontuario
from core_gestao.procedimentos_catalogo import (
    cobertura_catalogo,
    procedimento_por_id,
)

CHECKOUT_SALT = "ultramed-checkout-v1"
CHECKOUT_MAX_AGE = 86400 * 2  # 48h

PLANO_TIPO_MAP = {
    "essencial": "ESSENCIAL",
    "master": "MASTER",
    "empresarial": "EMPRESARIAL",
}

MAX_DEPENDENTES = {
    "ESSENCIAL": 2,
    "MASTER": 5,
    "EMPRESARIAL": 20,
}

# Procedimentos cobertos — alinhado à landing (planos + seção exames)
PROCEDIMENTOS_ESSENCIAL = (
    "ultrassom",
    "ultrason",
    "usg",
    "ecografia",
    "mapa",
    "holter",
)

PROCEDIMENTOS_MASTER_EXTRA = (
    "consulta",
    "eletrocardiograma",
    "ecg",
    "espirometria",
    "endoscop",
    "diu",
    "implanon",
    "paaf",
    "biopsi",
    "eeg",
    "polissonografia",
    "polisson",
    "doppler",
    "morfolog",
    "obstetric",
    "obstetrica",
    "transvaginal",
    "mama",
    "abdomen",
    "tireoide",
    "prostata",
    "renal",
)

PROCEDIMENTOS_LAB_ROTINA = (
    "hemograma",
    "glicose",
    "glicemia",
    "colesterol",
    "triglicer",
    "urina",
    "eas",
    "parcial de urina",
    "fezes",
    "copro",
    "tsh",
    "t3",
    "t4",
    "hormon",
    "progesterona",
    "testosteron",
    "estradiol",
    "creatinina",
    "ureia",
    "transamin",
    "tgo",
    "tgp",
    "pcr",
    "vhs",
    "vitamina",
    "ferro",
    "ferritina",
    "psa",
    "laborator",
    "bioquimica",
    "lipidograma",
    "perfil lipidico",
    "coleta",
    "sangue",
    "rotina",
)

RESUMO_PROCEDIMENTOS_PLANO = {
    "ESSENCIAL": [
        "Ultrassonografia (USG)",
        "MAPA 24h",
        "Holter 24h",
    ],
    "MASTER": [
        "Tudo do Essencial",
        "Consultas médicas",
        "ECG e Espirometria",
        "Endoscopia, PAAF e Biópsias",
        "DIU / Implanon, EEG, Polissonografia",
    ],
    "EMPRESARIAL": [
        "Tudo do Master",
        "Exames laboratoriais de rotina (40% off)",
        "Consultas e procedimentos hormonais (30% off)",
    ],
}


def normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", str(cpf or ""))


def _normalizar_procedimento(nome: str | None) -> str:
    if not nome:
        return ""
    texto = unicodedata.normalize("NFKD", str(nome))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", texto).strip()


def _contem_termo(nome: str, termos: tuple[str, ...]) -> bool:
    return any(termo in nome for termo in termos)


def _nome_procedimento(nome: str | None, tipo_agenda: str | None) -> str:
    if nome:
        return _normalizar_procedimento(nome)
    if (tipo_agenda or "").upper() == "CONSULTA":
        return "consulta"
    return ""


def _eh_laboratorial_rotina(nome: str) -> bool:
    return _contem_termo(nome, PROCEDIMENTOS_LAB_ROTINA)


def _cobertura_por_plano(plano_nome: str, nome: str, tipo_agenda: str | None) -> tuple[bool, str]:
    plano = (plano_nome or "").upper()
    if not nome and (tipo_agenda or "").upper() != "CONSULTA":
        return False, ""

    if "ESSENCIAL" in plano:
        if _contem_termo(nome, PROCEDIMENTOS_ESSENCIAL):
            return True, "essencial"
        return False, ""

    base = PROCEDIMENTOS_ESSENCIAL + PROCEDIMENTOS_MASTER_EXTRA
    if "MASTER" in plano:
        if (tipo_agenda or "").upper() == "CONSULTA" or _contem_termo(nome, base):
            return True, "master"
        return False, ""

    if "EMPRESARIAL" in plano:
        if _eh_laboratorial_rotina(nome):
            return True, "lab_rotina"
        if (tipo_agenda or "").upper() == "CONSULTA" or _contem_termo(nome, base):
            return True, "empresarial_clinico"
        return False, ""

    return False, ""


def procedimento_coberto_pelo_plano(
    plano_nome: str,
    nome_procedimento: str | None = None,
    tipo_agenda: str | None = None,
) -> tuple[bool, str]:
    nome = _nome_procedimento(nome_procedimento, tipo_agenda)
    return _cobertura_por_plano(plano_nome, nome, tipo_agenda)


def procedimentos_resumo_plano(plano_nome: str) -> list[str]:
    plano = (plano_nome or "").upper()
    for chave, itens in RESUMO_PROCEDIMENTOS_PLANO.items():
        if chave in plano:
            return itens
    return []


def _plano_ativo(paciente) -> bool:
    hoje = timezone.now().date()
    return bool(
        paciente.plano
        and paciente.vencimento_plano
        and paciente.vencimento_plano >= hoje
    )


def avaliar_desconto_procedimento(
    paciente,
    nome_procedimento: str | None = None,
    tipo_agenda: str | None = None,
    procedimento_id: str | None = None,
) -> dict:
    """Avalia cobertura e percentual de desconto para um procedimento."""
    proc_catalogo = procedimento_por_id(procedimento_id)

    if not _plano_ativo(paciente):
        return {
            "percentual": 0.0,
            "coberto": False,
            "categoria": "",
            "plano_ativo": False,
            "mensagem": "Particular / plano vencido",
            "procedimentos_plano": [],
            "procedimento_id": procedimento_id or "",
            "procedimento_nome": proc_catalogo["nome"] if proc_catalogo else (nome_procedimento or ""),
        }

    plano_nome = paciente.plano.nome
    resumo = procedimentos_resumo_plano(plano_nome)

    if proc_catalogo:
        coberto, categoria = cobertura_catalogo(plano_nome, proc_catalogo["id"])
        nome_exib = proc_catalogo["nome"]
    else:
        coberto, categoria = procedimento_coberto_pelo_plano(
            plano_nome, nome_procedimento, tipo_agenda
        )
        nome_exib = (nome_procedimento or tipo_agenda or "Procedimento").strip()

    if not coberto:
        return {
            "percentual": 0.0,
            "coberto": False,
            "categoria": "",
            "plano_ativo": True,
            "mensagem": f"'{nome_exib}' não está coberto pelo plano {plano_nome}.",
            "procedimentos_plano": resumo,
            "procedimento_id": procedimento_id or "",
            "procedimento_nome": nome_exib,
        }

    percentual = _percentual_por_categoria(paciente, plano_nome, categoria)
    return {
        "percentual": percentual,
        "coberto": True,
        "categoria": categoria,
        "plano_ativo": True,
        "mensagem": "",
        "procedimentos_plano": resumo,
        "procedimento_id": procedimento_id or "",
        "procedimento_nome": nome_exib,
    }


def _percentual_por_categoria(paciente, plano_nome: str, categoria: str) -> float:
    plano = (plano_nome or "").upper()
    if categoria == "lab_rotina":
        return 0.40
    if "ESSENCIAL" in plano:
        hoje = timezone.now().date()
        ja_usou = Prontuario.objects.filter(
            paciente=paciente,
            data_atendimento__month=hoje.month,
            data_atendimento__year=hoje.year,
        ).exists()
        return 0.20 if ja_usou else 0.30
    return 0.30


def percentual_desconto(
    paciente,
    tipo_procedimento: str | None = None,
    tipo_agenda: str | None = None,
    procedimento_id: str | None = None,
) -> float:
    info = avaliar_desconto_procedimento(
        paciente, tipo_procedimento, tipo_agenda, procedimento_id
    )
    return info["percentual"]


def resolver_plano(tipo: str | None = None, url_nome: str | None = None) -> Plano | None:
    """Resolve plano pelo select do formulário (prioridade) ou URL."""
    if tipo:
        chave = PLANO_TIPO_MAP.get(str(tipo).strip().lower())
        if chave:
            plano = Plano.objects.filter(nome=chave).first()
            if plano:
                return plano
    if url_nome:
        chave = PLANO_TIPO_MAP.get(str(url_nome).strip().lower())
        if chave:
            return Plano.objects.filter(nome=chave).first()
        plano = Plano.objects.filter(nome__icontains=url_nome).first()
        if plano:
            return plano
    return None


def max_dependentes_plano(plano: Plano) -> int:
    nome = (plano.nome or "").upper()
    for chave, limite in MAX_DEPENDENTES.items():
        if chave in nome:
            return limite
    return 0


def valor_checkout_plano(plano: Plano) -> float:
    valor = float(plano.valor_anual)
    if valor < 100:
        valor = valor * 12
    return round(valor, 2)


def gerar_acesso_checkout(paciente_id: int, plano_id: int) -> str:
    return signing.dumps(
        {"p": paciente_id, "pl": plano_id},
        salt="ultramed-acesso-checkout-v1",
    )


def validar_acesso_checkout(token: str, paciente_id: int, plano_id: int) -> bool:
    if not token:
        return False
    try:
        data = signing.loads(
            token, salt="ultramed-acesso-checkout-v1", max_age=CHECKOUT_MAX_AGE
        )
        return int(data.get("p")) == int(paciente_id) and int(data.get("pl")) == int(
            plano_id
        )
    except signing.BadSignature:
        return False


def gerar_checkout_token(fatura_id: int, paciente_id: int, plano_id: int) -> str:
    return signing.dumps(
        {"f": fatura_id, "p": paciente_id, "pl": plano_id},
        salt=CHECKOUT_SALT,
    )


def validar_checkout_token(token: str, fatura_id: int, paciente_id: int | None = None, plano_id: int | None = None) -> bool:
    if not token:
        return False
    try:
        data = signing.loads(token, salt=CHECKOUT_SALT, max_age=CHECKOUT_MAX_AGE)
        if int(data.get("f")) != int(fatura_id):
            return False
        if paciente_id is not None and int(data.get("p")) != int(paciente_id):
            return False
        if plano_id is not None and int(data.get("pl")) != int(plano_id):
            return False
        return True
    except signing.BadSignature:
        return False


def calcular_valor_com_desconto(
    paciente,
    valor_base,
    tipo_procedimento: str | None = None,
    tipo_agenda: str | None = None,
    procedimento_id: str | None = None,
) -> float:
    try:
        if isinstance(valor_base, str):
            valor_base = valor_base.replace(",", ".")
        valor_base = float(valor_base)
    except (TypeError, ValueError):
        valor_base = 0.0

    desconto = percentual_desconto(
        paciente, tipo_procedimento, tipo_agenda, procedimento_id
    )
    if desconto <= 0:
        return valor_base
    return round(valor_base * (1 - desconto), 2)


def valores_mp_coincidem(valor_fatura, valor_pagamento) -> bool:
    try:
        return abs(float(valor_fatura) - float(valor_pagamento)) < 0.02
    except (TypeError, ValueError):
        return False
