from django.db import models

class Plano(models.Model):
    NOME_CHOICES = [
        ('ESSENCIAL', 'Ultramed Essencial'),
        ('MASTER', 'Ultramed Master Familiar'),
        ('EMPRESARIAL', 'Ultramed Empresarial'),
    ]
    nome = models.CharField(max_length=50, choices=NOME_CHOICES, verbose_name="Nome do Plano")
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.nome

class Paciente(models.Model):
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')]
    
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, default='M')
    endereco = models.CharField(max_length=255, blank=True, null=True)
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True)
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo

class LeadSite(models.Model):
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20)
    interesse = models.CharField(max_length=100)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    atendido = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome} - {self.interesse}"
