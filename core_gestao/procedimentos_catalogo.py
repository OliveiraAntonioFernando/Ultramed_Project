"""Catálogo fixo de procedimentos para agendamento — evita erro de digitação."""

from __future__ import annotations

from typing import TypedDict


class ProcedimentoItem(TypedDict):
    id: str
    nome: str
    grupo: str
    tipo: str  # CONSULTA | EXAME
    categoria: str  # essencial | master_clinico | lab_rotina
    planos: list[str]


CATALOGO_PROCEDIMENTOS: list[ProcedimentoItem] = [
    # Consultas (Master e Empresarial)
    {
        "id": "consulta_clinica",
        "nome": "Consulta médica",
        "grupo": "Consultas",
        "tipo": "CONSULTA",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    {
        "id": "consulta_retorno",
        "nome": "Consulta de retorno",
        "grupo": "Consultas",
        "tipo": "CONSULTA",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    # Ultrassonografia (Essencial + superiores)
    {
        "id": "usg_obstetrica",
        "nome": "USG Obstétrica",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_morfologica",
        "nome": "USG Morfológica",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_mamas",
        "nome": "USG Mamas",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_transvaginal",
        "nome": "USG Transvaginal",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_abdomen",
        "nome": "USG Abdômen",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_renal",
        "nome": "USG Rins / Vias urinárias",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_prostata",
        "nome": "USG Próstata",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_tireoide",
        "nome": "USG Tireoide",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "usg_doppler_obstetrico",
        "nome": "USG Doppler Obstétrico",
        "grupo": "Ultrassonografia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    # Cardiologia
    {
        "id": "ecg",
        "nome": "Eletrocardiograma (ECG)",
        "grupo": "Cardiologia",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    {
        "id": "mapa_24h",
        "nome": "MAPA 24h",
        "grupo": "Cardiologia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "holter_24h",
        "nome": "Holter 24h",
        "grupo": "Cardiologia",
        "tipo": "EXAME",
        "categoria": "essencial",
        "planos": ["ESSENCIAL", "MASTER", "EMPRESARIAL"],
    },
    {
        "id": "espirometria",
        "nome": "Espirometria",
        "grupo": "Cardiologia",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    # Laboratorial (Empresarial — 40%)
    {
        "id": "lab_hemograma",
        "nome": "Hemograma completo",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_glicemia",
        "nome": "Glicemia / Glicose",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_colesterol",
        "nome": "Colesterol / Perfil lipídico",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_triglicerides",
        "nome": "Triglicerídeos",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_eas",
        "nome": "EAS / Urina tipo I",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_parasito_fezes",
        "nome": "Parasitológico de fezes",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_tsh",
        "nome": "TSH",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_t4_livre",
        "nome": "T4 livre",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_hormonal",
        "nome": "Exame hormonal (rotina)",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_creatinina_ureia",
        "nome": "Creatinina / Ureia",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_transaminases",
        "nome": "TGO / TGP (transaminases)",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    {
        "id": "lab_psa",
        "nome": "PSA",
        "grupo": "Laboratorial de rotina",
        "tipo": "EXAME",
        "categoria": "lab_rotina",
        "planos": ["EMPRESARIAL"],
    },
    # Procedimentos avançados (Master + Empresarial)
    {
        "id": "endoscopia_digestiva",
        "nome": "Endoscopia digestiva",
        "grupo": "Procedimentos avançados",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    {
        "id": "diu_implanon",
        "nome": "Inserção DIU / Implanon",
        "grupo": "Procedimentos avançados",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    {
        "id": "paaf_biopsia",
        "nome": "PAAF / Biópsia",
        "grupo": "Procedimentos avançados",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    {
        "id": "eeg",
        "nome": "EEG",
        "grupo": "Procedimentos avançados",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
    {
        "id": "polissonografia",
        "nome": "Polissonografia",
        "grupo": "Procedimentos avançados",
        "tipo": "EXAME",
        "categoria": "master_clinico",
        "planos": ["MASTER", "EMPRESARIAL"],
    },
]

_CATALOGO_MAP: dict[str, ProcedimentoItem] = {p["id"]: p for p in CATALOGO_PROCEDIMENTOS}


def procedimento_por_id(procedimento_id: str | None) -> ProcedimentoItem | None:
    if not procedimento_id:
        return None
    return _CATALOGO_MAP.get(str(procedimento_id).strip())


def catalogo_por_grupos() -> list[tuple[str, list[ProcedimentoItem]]]:
    grupos: dict[str, list[ProcedimentoItem]] = {}
    ordem: list[str] = []
    for item in CATALOGO_PROCEDIMENTOS:
        g = item["grupo"]
        if g not in grupos:
            grupos[g] = []
            ordem.append(g)
        grupos[g].append(item)
    return [(g, grupos[g]) for g in ordem]


def cobertura_catalogo(plano_nome: str, procedimento_id: str) -> tuple[bool, str]:
    proc = procedimento_por_id(procedimento_id)
    if not proc:
        return False, ""
    plano = (plano_nome or "").upper()
    for chave in proc["planos"]:
        if chave in plano:
            return True, proc["categoria"]
    return False, ""
