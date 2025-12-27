from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Paciente, Plano, Fatura, Exame, Prontuario, LeadSite

# --- LOGIN E REDIRECIONAMENTO INTELIGENTE ---
def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            # 1. MÉDICO -> Consultório
            if user.groups.filter(name='Medico').exists():
                return redirect('sistema_interno:painel_medico')
            # 2. RECEPÇÃO -> Painel Equipe
            if user.groups.filter(name='Recepcao').exists():
                return redirect('sistema_interno:painel_colaborador')
            # 3. ADMIN / MASTER -> Dashboard Financeiro
            if user.is_superuser:
                return redirect('sistema_interno:master_dashboard')
            # 4. PACIENTE -> Meu Espaço
            return redirect('sistema_interno:painel_paciente')
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

# --- CAPTURA DE LEADS (LANDING PAGE) ---
@csrf_exempt
def api_lead_capture(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        telefone = request.POST.get('telefone')
        interesse = request.POST.get('interesse', 'Interesse Geral')
        
        if nome and telefone:
            LeadSite.objects.create(nome=nome, telefone=telefone, interesse=interesse)
            return JsonResponse({'status': 'sucesso', 'message': 'Lead registrado!'})
    return JsonResponse({'status': 'erro'}, status=400)

# --- PAINEL MASTER (DONO) ---
@login_required
def master_dashboard(request):
    if not request.user.is_superuser:
        return redirect('sistema_interno:login')
        
    pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    atrasado = Fatura.objects.filter(status='ATRASADO').aggregate(Sum('valor'))['valor__sum'] or 0
    pendente = Fatura.objects.filter(status='PENDENTE').aggregate(Sum('valor'))['valor__sum'] or 0
    
    context = {
        'faturamento_total': pago,
        'inadimplencia': atrasado,
        'pendente_receber': pendente,
        'leads_recentes': LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')[:5],
        'faturas_abertas': Fatura.objects.filter(status__in=['PENDENTE', 'ATRASADO']).order_by('data_vencimento')[:10],
    }
    return render(request, 'master_dashboard.html', context)

# --- PAINEL MÉDICO (CONSULTÓRIO) ---
@login_required
def painel_medico(request):
    if not (request.user.groups.filter(name='Medico').exists() or request.user.is_superuser):
        return redirect('sistema_interno:login')
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'painel_medico.html', {'pacientes': pacientes})

@login_required
def prontuario_view(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    if request.method == 'POST':
        Prontuario.objects.create(paciente=paciente, medico=request.user, evolucao=request.POST.get('evolucao'))
        messages.success(request, "Atendimento salvo.")
        return redirect('sistema_interno:painel_medico')
    historico = Prontuario.objects.filter(paciente=paciente).order_by('-data_atendimento')
    return render(request, 'prontuario.html', {'paciente': paciente, 'historico': historico})

# --- PAINEL EQUIPE (RECEPÇÃO) ---
@login_required
def painel_colaborador(request):
    if not (request.user.groups.filter(name='Recepcao').exists() or request.user.is_superuser):
        return redirect('sistema_interno:login')
    return render(request, 'painel_colaborador.html')

# --- PAINEL PACIENTE (BLINDADO) ---
@login_required
def painel_paciente(request):
    paciente = Paciente.objects.filter(cpf=request.user.username).first()
    if not paciente:
        return redirect('sistema_interno:master_dashboard')
    
    return render(request, 'painel_paciente.html', {
        'paciente': paciente,
        'faturas': Fatura.objects.filter(paciente=paciente).order_by('-data_vencimento'),
        'exames': Exame.objects.filter(paciente=paciente).order_by('-data_solicitacao')
    })

# --- GESTÃO OPERACIONAL ---
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
    return render(request, 'cliente_list.html', {'pacientes': Paciente.objects.all().order_by('nome_completo')})

@login_required
def fatura_create(request):
    if request.method == 'POST':
        Fatura.objects.create(
            paciente_id=request.POST.get('paciente'),
            valor=request.POST.get('valor').replace(',', '.'),
            data_vencimento=request.POST.get('vencimento'),
            status='PENDENTE'
        )
        return redirect('sistema_interno:master_dashboard')
    return render(request, 'fatura_form.html', {'pacientes': Paciente.objects.all()})

@login_required
def fatura_baixar(request, fatura_id):
    f = get_object_or_404(Fatura, id=fatura_id)
    f.status = 'PAGO'; f.save()
    return redirect('sistema_interno:master_dashboard')

# --- ROTAS OBRIGATÓRIAS (STUBS) ---
@login_required
def plan_create(request): return render(request, 'plan_form.html')
@login_required
def agenda_view(request): return render(request, 'agenda.html')
def api_buscar_paciente(request): return JsonResponse({'results': []})
