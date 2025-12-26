# ultramed_app/sistema_interno/forms.py

from django import forms
from .models import Cliente, Plano # Importe o Cliente e o Plano

class ClienteForm(forms.ModelForm):
    
    class Meta:
        model = Cliente
        # Campos que existem no modelo Cliente e que queremos exibir
        fields = [
            'plan',
            'group_name',
            'is_active'
        ]

        labels = {
            'plan': 'Plano Contratado',
            'group_name': 'Nome do Grupo/Empresa (Opcional)',
            'is_active': 'Plano Ativo'
        }
