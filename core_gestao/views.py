from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Paciente, Plano, Fatura, Exame, Prontuario, LeadSite

# --- AUTENTICAÇÃO E REDIRECIONAMENTO ---
def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            # 1. Se for MÉDICO (Grupo Medico), vai para o Consultório
            if user.groups.filter(name='Medico').exists():
                return redirect('sistema_interno:painel_medico')
            # 2. Se for ADMIN/DONO, vai para o Master Control
            if user.is_superuser or user.is_staff:
                return redirect('sistema_interno:master_dashboard')
            # 3. Se for PACIENTE (CPF), vai para o Meu Espaço
            return redirect('sistema_interno:painel_paciente')
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

# --- PAINEL DO MÉDICO & ATENDIMENTO ---
@login_required
def painel_medico(request):
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'painel_medico.html', {'pacientes': pacientes})

@login_required
def prontuario_view(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    if request.method == 'POST':
        Prontuario.objects.create(
            paciente=paciente, 
            medico=request.user, 
            evolucao=request.POST.get('evolucao')
        )
        messages.success(request, "Atendimento registrado com sucesso!")
        return redirect('sistema_interno:painel_medico')
    
    historico = Prontuario.objects.filter(paciente=paciente).order_by('-data_atendimento')
    return render(request, 'prontuario.html', {'paciente': paciente, 'historico': historico})

# --- PAINEL DO PACIENTE (MEU ESPAÇO) ---

@login_required
def painel_paciente(request):
    # Tenta buscar o paciente, se não existir, redireciona em vez de dar 404
    paciente = Paciente.objects.filter(cpf=request.user.username).first()
    
    if not paciente:
        messages.warning(request, "Acesso restrito a pacientes cadastrados.")
        if request.user.is_staff or request.user.is_superuser:
            return redirect('sistema_interno:master_dashboard')
        return redirect('sistema_interno:login')

    faturas = Fatura.objects.filter(paciente=paciente).order_by('-data_vencimento')
    exames = Exame.objects.filter(paciente=paciente).order_by('-data_solicitacao')
    
    return render(request, 'painel_paciente.html', {
        'paciente': paciente, 
        'faturas': faturas, 
        'exames': exames
    })

# --- MASTER DASHBOARD & GESTÃO ---
@login_required
def master_dashboard(request):
    pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    atrasado = Fatura.objects.filter(status='ATRASADO').aggregate(Sum('valor'))['valor__sum'] or 0
    pendente = Fatura.objects.filter(status='PENDENTE').aggregate(Sum('valor'))['valor__sum'] or 0
    context = {
        'faturamento_total': pago, 'inadimplencia': atrasado, 'pendente_receber': pendente,
        'faturas_abertas': Fatura.objects.filter(status__in=['PENDENTE', 'ATRASADO']).order_by('data_vencimento'),
        'boletos_recentes': Fatura.objects.filter(status='PENDENTE').order_by('-data_vencimento')[:10],
    }
    return render(request, 'master_dashboard.html', context)

@login_required
def painel_colaborador(request):
    return render(request, 'painel_colaborador.html')

# --- FINANCEIRO ---
@login_required
def fatura_create(request):
    if request.method == 'POST':
        Fatura.objects.create(
            paciente_id=request.POST.get('paciente'),
            valor=request.POST.get('valor').replace(',', '.'),
            data_vencimento=request.POST.get('vencimento'),
            linha_digitavel=request.POST.get('linha_digitavel'),
            link_boleto=request.POST.get('link_boleto'),
            status='PENDENTE'
        )
        return redirect('sistema_interno:master_dashboard')
    return render(request, 'fatura_form.html', {'pacientes': Paciente.objects.all()})

@login_required
def fatura_baixar(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    fatura.status = 'PAGO'
    fatura.save()
    return redirect('sistema_interno:master_dashboard')

# --- CADASTRO DE CLIENTES/PLANOS ---
@login_required
def cliente_create(request):
    if request.method == 'POST':
        Paciente.objects.create(
            nome_completo=request.POST.get('nome_completo'),
            cpf=request.POST.get('cpf'),
            telefone=request.POST.get('telefone'),
            data_nascimento=request.POST.get('data_nascimento')
        )
        return redirect('sistema_interno:cliente_list')
    return render(request, 'cliente_create.html')

@login_required
def cliente_list(request):
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'cliente_list.html', {'pacientes': pacientes})

@login_required
def plan_create(request):
    return render(request, 'plan_form.html')

@login_required
def agenda_view(request):
    return render(request, 'agenda.html')

# --- APIs PARA O SITE ---
def api_lead_capture(request):
    return JsonResponse({'status': 'sucesso'})

def api_buscar_paciente(request):
    term = request.GET.get('term', '')
    pacientes = Paciente.objects.filter(nome_completo__icontains=term)[:10]
    results = [{'id': p.id, 'text': p.nome_completo} for p in pacientes]
    return JsonResponse({'results': results})
