from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# =================================================================
# 1. GESTÃO DE PLANOS
# =================================================================

class Plano(models.Model):
    NOME_CHOICES = [
        ('ESSENCIAL', 'Ultramed Essencial'),
        ('MASTER', 'Ultramed Master Familiar'),
        ('EMPRESARIAL', 'Ultramed Empresarial')
    ]
    nome = models.CharField(max_length=50, choices=NOME_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    # Valor anual utilizado para gerar as faturas no checkout
    valor_anual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.get_nome_display()

# =================================================================
# 2. GESTÃO DE PACIENTES E FAMÍLIA
# =================================================================

class Paciente(models.Model):
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    possui_dependentes = models.BooleanField(default=False)
    is_titular = models.BooleanField(default=True) 
    telefone = models.CharField(max_length=20)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], default='M')

    # Endereço
    endereco = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, default="São Félix do Xingu")

    # Detalhes do Plano e Vencimento
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True)
    modalidade_plano = models.CharField(max_length=100, blank=True, null=True)
    vencimento_plano = models.DateField(null=True, blank=True)

    # Hierarquia Familiar (Auto-relacionamento)
    # related_name='dependentes' permite: titular.dependentes.all()
    responsavel = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependentes')
    
    # Campo para KPI de Crônicos
    is_cronico = models.BooleanField(default=False)
    doencas_cronicas = models.CharField(max_length=500, blank=True, null=True)
    
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo

# =================================================================
# 3. FINANCEIRO (UNIFICADO COM MERCADO PAGO)
# =================================================================

class Fatura(models.Model):
    STATUS_CHOICES = [('PAGO', 'Pago'), ('PENDENTE', 'Pendente'), ('ATRASADO', 'Atrasado')]
    METODO_CHOICES = [('PIX', 'PIX'), ('CARTAO', 'Cartão de Crédito'), ('PIX/CARTAO', 'PIX ou Cartão')]

    # related_name='faturas' permite: paciente.faturas.all()
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='faturas')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField() 
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_CHOICES, blank=True, null=True)
    data_pagamento = models.DateField(null=True, blank=True)
    
    # Ajustado: removido unique=True para evitar travamentos em reprocessamentos
    mercadopago_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Fatura {self.id} - {self.paciente.nome_completo} ({self.status})"

# =================================================================
# 4. AGENDAMENTO E ATENDIMENTO
# =================================================================

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
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='exames_paciente')
    nome_exame = models.CharField(max_length=255)
    data_solicitacao = models.DateField(auto_now_add=True)
    realizado = models.BooleanField(default=False)
    laudo = models.TextField(blank=True, null=True)
    valor_tabela = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    arquivo = models.FileField(upload_to='exames/%Y/%m/%d/', blank=True, null=True)

    def __str__(self):
        return f"{self.nome_exame} - {self.paciente.nome_completo}"

class Prontuario(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    medico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_atendimento = models.DateTimeField(auto_now_add=True)
    evolucao = models.TextField()
    prescricao = models.TextField(blank=True, null=True)

class Receita(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='receitas')
    medico = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = models.TextField()
    data_emissao = models.DateTimeField(auto_now_add=True)
    hash_digital = models.CharField(max_length=100, blank=True, null=True)

# =================================================================
# 5. CRM E LEADS
# =================================================================

class LeadSite(models.Model):
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20)
    interesse = models.CharField(max_length=100)
    atendido = models.BooleanField(default=False)
    data_solicitacao = models.DateTimeField(auto_now_add=True)