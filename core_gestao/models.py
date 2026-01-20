from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Plano(models.Model):
    NOME_CHOICES = [
        ('ESSENCIAL', 'Ultramed Essencial'),
        ('MASTER', 'Ultramed Master Familiar'),
        ('EMPRESARIAL', 'Ultramed Empresarial')
    ]
    nome = models.CharField(max_length=50, choices=NOME_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    valor_anual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.nome

class Paciente(models.Model):
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    possui_dependentes = models.BooleanField(default=False)
    telefone = models.CharField(max_length=20)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], default='M')

    # Endereço
    endereco = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, default="São Félix do Xingu")

    # Detalhes do Plano Anual
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True)
    modalidade_plano = models.CharField(max_length=100, blank=True, null=True)
    vencimento_plano = models.DateField(null=True, blank=True)

    # Hierarquia Familiar
    responsavel = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependentes')
    
    # Campo para KPI de Crônicos
    is_cronico = models.BooleanField(default=False)
    
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo

class Fatura(models.Model):
    STATUS_CHOICES = [('PAGO', 'Pago'), ('PENDENTE', 'Pendente'), ('ATRASADO', 'Atrasado')]
    METODO_CHOICES = [('PIX', 'PIX'), ('CARTAO', 'Cartão de Crédito')]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_CHOICES, blank=True, null=True)
    data_pagamento = models.DateField(null=True, blank=True)

class Agenda(models.Model):
    TIPOS = [('CONSULTA', 'Consulta'), ('EXAME', 'Exame')]
    STATUS = [
        ('AGENDADO', 'Agendado'),
        ('CHEGOU', 'Em Espera (Chegou)'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado')
    ]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    data = models.DateField()
    hora = models.TimeField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default='CONSULTA')
    status = models.CharField(max_length=15, choices=STATUS, default='AGENDADO')
    observacoes = models.TextField(blank=True, null=True)
    data_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.data} {self.hora} - {self.paciente.nome_completo}"

class Exame(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    nome_exame = models.CharField(max_length=255)
    data_solicitacao = models.DateField(auto_now_add=True)
    laudo = models.TextField(blank=True, null=True)
    realizado = models.BooleanField(default=False)
    valor_tabela = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

class Prontuario(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    medico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_atendimento = models.DateTimeField(auto_now_add=True)
    evolucao = models.TextField()
    prescricao = models.TextField(blank=True, null=True)

class Receita(models.Model):
    """ Novo Modelo para Gestão de Receitas e Renovação """
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='receitas')
    medico = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = models.TextField()
    data_emissao = models.DateTimeField(auto_now_add=True)
    hash_digital = models.CharField(max_length=100, blank=True, null=True) # Para futura assinatura

    def __str__(self):
        return f"Receita de {self.paciente.nome_completo} - {self.data_emissao.strftime('%d/%m/%Y')}"

class LeadSite(models.Model):
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20)
    interesse = models.CharField(max_length=100)
    atendido = models.BooleanField(default=False)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
