from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

# 0. USUÁRIO (Ajustado para evitar conflitos de migração)
class User(AbstractUser):
    telefone = models.CharField(max_length=15, blank=True, null=True)
    cargo = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    
    # Adicionando related_name únicos para evitar o erro de conflito do Django
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name="custom_user_groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_permissions",
    )

    class Meta:
        app_label = 'sistema_interno'

    def __str__(self):
        return self.username

# 1. PLANOS
class Plano(models.Model):
    TYPE_CHOICES = (('INDIVIDUAL', 'Individual'), ('FAMILIAR', 'Familiar'), ('CORPORATIVO', 'Corporativo'))
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    plan_type = models.CharField(max_length=15, choices=TYPE_CHOICES, default='INDIVIDUAL')
    max_people = models.IntegerField(default=1)
    
    def __str__(self): return self.name

# 2. PACIENTES
class Paciente(models.Model):
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    rg = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    data_nascimento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    convenio = models.CharField(max_length=100, default='PARTICULAR')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self): return self.nome_completo

# 3. AGENDAMENTO
class Agendamento(models.Model):
    STATUS_CHOICES = (('AGUARDANDO', 'Aguardando'), ('REALIZADO', 'Realizado'), ('CANCELADO', 'Cancelado'))
    TIPO_CHOICES = (('CONSULTA', 'Consulta'), ('EXAME', 'Exame'))

    paciente_nome = models.CharField(max_length=255)
    medico = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='CONSULTA')
    exame_nome = models.CharField(max_length=255, blank=True, null=True)
    data = models.DateField(null=True, blank=True)
    hora = models.TimeField(null=True, blank=True)
    valor_consulta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AGUARDANDO')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.paciente_nome} - {self.tipo}"

# 4. FATURA
class Fatura(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.SET_NULL, null=True, blank=True)
    paciente_nome_avulso = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    tipo_pagamento = models.CharField(max_length=50, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

# 5. LEADS E LEGACY
class LeadCapture(models.Model):
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20)
    interesse = models.CharField(max_length=255, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    plan = models.ForeignKey(Plano, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(auto_now_add=True)

