from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Paciente, LeadSite
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            # Redireciona para o painel principal
            return redirect('sistema_interno:painel_colaborador')
        else:
            messages.error(request, "Usuario ou senha incorretos.")
    return render(request, 'login.html')

@login_required
def painel_colaborador(request):
    leads = LeadSite.objects.all().order_by('-data_solicitacao')[:10]
    pacientes = Paciente.objects.all().order_by('-data_cadastro')[:10]
    
    context = {
        'leads': leads,
        'pacientes': pacientes,
        # Estas variaveis serao usadas no seu HTML para esconder/mostrar botoes
        'is_admin': request.user.is_superuser or request.user.groups.filter(name='Administrativo').exists(),
        'is_medico': request.user.groups.filter(name='Medicos').exists(),
        'is_equipe': request.user.groups.filter(name='Equipe').exists(),
    }
    return render(request, 'painel_colaborador.html', context)
