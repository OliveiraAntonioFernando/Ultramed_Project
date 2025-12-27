from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from .models import Paciente, Plano, LeadSite
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            return redirect('sistema_interno:painel_colaborador')
        messages.error(request, "Usuário ou senha inválidos")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

@login_required
def painel_colaborador(request):
    leads = LeadSite.objects.all().order_by('-data_solicitacao')[:10]
    pacientes = Paciente.objects.all().order_by('-data_cadastro')[:10]
    return render(request, 'painel_colaborador.html', {'leads': leads, 'pacientes': pacientes})

@login_required
def cliente_create(request):
    if request.method == 'POST':
        Paciente.objects.create(
            nome_completo=request.POST.get('nome_completo') or request.POST.get('nome'),
            cpf=request.POST.get('cpf'),
            telefone=request.POST.get('telefone'),
            data_nascimento=request.POST.get('data_nascimento'),
            sexo=request.POST.get('sexo', 'M'),
            endereco=request.POST.get('endereco', '')
        )
        messages.success(request, "Paciente cadastrado com sucesso!")
        return redirect('sistema_interno:painel_colaborador')
    return render(request, 'cliente_create.html')

@login_required
def cliente_list(request):
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'painel_colaborador.html', {'pacientes': pacientes}) # Reaproveita o painel ou crie cliente_list.html

@login_required
def agenda_view(request):
    return render(request, 'agenda.html')

@login_required
def plan_create(request):
    return render(request, 'plan_form.html')

@csrf_exempt
def api_lead_capture(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            LeadSite.objects.create(
                nome=data.get('nome'),
                telefone=data.get('telefone'),
                interesse=data.get('interesse')
            )
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)

def api_buscar_paciente(request):
    term = request.GET.get('term', '')
    pacientes = Paciente.objects.filter(nome_completo__icontains=term) | Paciente.objects.filter(cpf__icontains=term)
    results = [{'nome': p.nome_completo, 'cpf': p.cpf, 'convenio': p.plano.nome if p.plano else 'PARTICULAR'} for p in pacientes]
    return JsonResponse({'results': results})
