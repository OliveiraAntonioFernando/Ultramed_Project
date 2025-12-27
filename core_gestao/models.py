from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Plano(models.Model):
    NOME_CHOICES = [('ESSENCIAL', 'Ultramed Essencial'), ('MASTER', 'Ultramed Master Familiar'), ('EMPRESARIAL', 'Ultramed Empresarial')]
    nome = models.CharField(max_length=50, choices=NOME_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    def __str__(self): return self.nome

class Paciente(models.Model):
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=20)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], default='M')
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True)
    responsavel = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependentes')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nome_completo

class Fatura(models.Model):
    STATUS_CHOICES = [('PAGO', 'Pago'), ('PENDENTE', 'Pendente'), ('ATRASADO', 'Atrasado')]
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    linha_digitavel = models.CharField(max_length=255, blank=True, null=True)
    link_boleto = models.URLField(blank=True, null=True)
    data_pagamento = models.DateField(null=True, blank=True)

class Exame(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    nome_exame = models.CharField(max_length=255)
    data_solicitacao = models.DateField(auto_now_add=True)
    laudo = models.TextField(blank=True, null=True)
    realizado = models.BooleanField(default=False)

class Prontuario(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    medico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_atendimento = models.DateTimeField(auto_now_add=True)
    evolucao = models.TextField()
    prescricao = models.TextField(blank=True, null=True)

class LeadSite(models.Model):
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20)
    interesse = models.CharField(max_length=100)
    atendido = models.BooleanField(default=False)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
