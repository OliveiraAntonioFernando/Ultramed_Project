from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Paciente, Plano, LeadSite, Fatura

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            if user.is_superuser or user.groups.filter(name='Administrativo').exists():
                return redirect('sistema_interno:master_dashboard')
            return redirect('sistema_interno:painel_colaborador')
        messages.error(request, "Usuario ou senha invalidos")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

@login_required
def master_dashboard(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrativo').exists()):
        return redirect('sistema_interno:painel_colaborador')

    faturamento_pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    inadimplencia = Fatura.objects.filter(status='ATRASADO').aggregate(Sum('valor'))['valor__sum'] or 0
    pendente = Fatura.objects.filter(status='PENDENTE').aggregate(Sum('valor'))['valor__sum'] or 0
    
    total_geral = faturamento_pago + inadimplencia + pendente
    taxa_adimplencia = (faturamento_pago / total_geral * 100) if total_geral > 0 else 0

    context = {
        'total_pacientes': Paciente.objects.count(),
        'total_leads': LeadSite.objects.filter(atendido=False).count(),
        'faturamento_total': faturamento_pago,
        'inadimplencia': inadimplencia,
        'pendente_receber': pendente,
        'taxa_adimplencia': round(taxa_adimplencia, 1),
        'leads': LeadSite.objects.all().order_by('-data_solicitacao')[:5],
        'faturas_abertas': Fatura.objects.filter(status__in=['PENDENTE', 'ATRASADO']).order_by('data_vencimento'),
        'is_admin': True,
    }
    return render(request, 'master_dashboard.html', context)

@login_required
def fatura_baixar(request, fatura_id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Administrativo').exists()):
        return redirect('sistema_interno:painel_colaborador')
    
    fatura = get_object_or_404(Fatura, id=fatura_id)
    fatura.status = 'PAGO'
    fatura.data_pagamento = timezone.now()
    fatura.save()
    messages.success(request, f"Pagamento de {fatura.paciente.nome_completo} confirmado!")
    return redirect('sistema_interno:master_dashboard')

@login_required
def painel_colaborador(request):
    leads = LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')[:10]
    pacientes = Paciente.objects.all().order_by('-data_cadastro')[:10]
    context = {
        'leads': leads,
        'pacientes': pacientes,
        'is_admin': request.user.is_superuser or request.user.groups.filter(name='Administrativo').exists(),
        'is_medico': request.user.groups.filter(name='Medicos').exists(),
    }
    return render(request, 'painel_colaborador.html', context)

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
        return redirect('sistema_interno:painel_colaborador')
    return render(request, 'cliente_create.html')

@login_required
def cliente_list(request):
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'painel_colaborador.html', {'pacientes': pacientes})

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
            LeadSite.objects.create(nome=data.get('nome'), telefone=data.get('telefone'), interesse=data.get('interesse'))
            return JsonResponse({'success': True})
        except: return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)

@login_required
def api_buscar_paciente(request):
    term = request.GET.get('term', '')
    pacientes = Paciente.objects.filter(nome_completo__icontains=term) | Paciente.objects.filter(cpf__icontains=term)
    results = [{'nome': p.nome_completo, 'cpf': p.cpf, 'convenio': p.plano.nome if p.plano else 'PARTICULAR'} for p in pacientes]
    return JsonResponse({'results': results})
