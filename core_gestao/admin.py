from django.contrib import admin

from .models import Agenda, Exame, Fatura, LeadSite, Paciente, Plano, Prontuario, Receita


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ("nome", "valor_anual")


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "cpf", "plano", "vencimento_plano", "is_titular")
    list_filter = ("is_titular", "plano")
    search_fields = ("nome_completo", "cpf")


@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ("id", "paciente", "valor", "status", "data_pagamento")
    list_filter = ("status",)


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ("paciente", "data", "hora", "tipo", "status")


@admin.register(Exame)
class ExameAdmin(admin.ModelAdmin):
    list_display = ("nome_exame", "paciente", "data_solicitacao", "realizado")


@admin.register(Prontuario)
class ProntuarioAdmin(admin.ModelAdmin):
    list_display = ("paciente", "medico", "data_atendimento")


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ("paciente", "medico", "data_emissao")


@admin.register(LeadSite)
class LeadSiteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "interesse", "atendido", "data_solicitacao")
    list_filter = ("atendido",)
