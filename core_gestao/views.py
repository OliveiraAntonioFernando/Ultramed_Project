from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.utils import timezone
from .models import Paciente, Fatura, Prontuario, LeadSite, Plano, Exame

# =================================================================
# 1. REGRAS DE NEGÓCIO (LOGICA DE DESCONTOS E LIMITES)
# =================================================================

def calcular_valor_com_desconto(paciente, valor_base):
    """ 
    Aplica as regras da Ultramed:
    - Particular: 0% desconto.
    - Essencial: 30% no 1º atendimento do mês, 20% nos demais.
    - Master: 30% fixo.
    - Empresarial: 35% fixo.
    """
    if not paciente.plano:
        return float(valor_base)

    plano_nome = paciente.plano.nome.upper()
    desconto = 0.0
    
    if 'ESSENCIAL' in plano_nome:
        # Verifica se já houve pagamento de fatura este mês
        ja_usou_este_mes = Fatura.objects.filter(
            paciente=paciente, 
            status='PAGO',
            data_pagamento__month=timezone.now().month,
            data_pagamento__year=timezone.now().year
        ).exists()
        desconto = 0.30 if not ja_usou_este_mes else 0.20
        
    elif 'MASTER' in plano_nome:
        desconto = 0.30
        
    elif 'EMPRESARIAL' in plano_nome:
        desconto = 0.35
        
    return float(valor_base) * (1 - desconto)

# =================================================================
# 2. SISTEMA DE ACESSO (LOGIN/LOGOUT)
# =================================================================

def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            # Redirecionamento Blindado por Perfil
            if user.username == 'medico':
                return redirect('sistema_interno:painel_medico')
            if user.username == 'recepcao':
                return redirect('sistema_interno:painel_colaborador')
            if user.username == 'master' or user.is_superuser:
                return redirect('sistema_interno:master_dashboard')
            return redirect('sistema_interno:painel_paciente')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

# =================================================================
# 3. GESTÃO DE PACIENTES E DEPENDENTES
# =================================================================

@login_required
def cliente_list(request):
    """ Lista apenas Titulares para manter a organização """
    context = {
        'pacientes': Paciente.objects.filter(responsavel__isnull=True).order_by('-data_cadastro'),
        'planos': Plano.objects.all()
    }
    return render(request, 'cliente_list.html', context)

@login_required
def cliente_create(request):
    """ Cadastro largo: Titular + N dependentes no mesmo POST """
    if request.method == 'POST':
        plano_id = request.POST.get('plano')
        
        # 1. Cria o Titular
        titular = Paciente.objects.create(
            nome_completo=request.POST.get('nome_completo'),
            cpf=request.POST.get('cpf'),
            telefone=request.POST.get('telefone'),
            data_nascimento=request.POST.get('data_nascimento') or None,
            sexo=request.POST.get('sexo', 'M'),
            endereco=request.POST.get('endereco'),
            bairro=request.POST.get('bairro'),
            cidade=request.POST.get('cidade', 'São Félix do Xingu'),
            possui_dependentes=request.POST.get('possui_dependentes') == 'on',
            modalidade_plano=request.POST.get('modalidade_plano'),
            plano_id=plano_id if request.POST.get('plano_tipo') == 'PLANO' else None,
            vencimento_plano=request.POST.get('vencimento_plano') or None
        )

        # 2. Processa Dependentes (Arrays do JavaScript)
        nomes_dep = request.POST.getlist('dep_nome[]')
        cpfs_dep = request.POST.getlist('dep_cpf[]')
        nascs_dep = request.POST.getlist('dep_nasc[]')
        
        # Define limite de segurança por plano
        limite = 999
        if titular.plano:
            if 'ESSENCIAL' in titular.plano.nome: limite = 3
            elif 'MASTER' in titular.plano.nome: limite = 6

        for i in range(min(len(nomes_dep), limite)):
            if nomes_dep[i].strip():
                Paciente.objects.create(
                    nome_completo=nomes_dep[i],
                    cpf=cpfs_dep[i] if i < len(cpfs_dep) else None,
                    data_nascimento=nascs_dep[i] if i < len(nascs_dep) and nascs_dep[i] else None,
                    responsavel=titular,
                    # Herança de dados do Titular para agilidade
                    telefone=titular.telefone,
                    endereco=titular.endereco,
                    bairro=titular.bairro,
                    cidade=titular.cidade,
                    plano=titular.plano
                )
    return redirect('sistema_interno:cliente_list')

# =================================================================
# 4. FINANCEIRO (FATURAMENTO COM DESCONTO)
# =================================================================

@login_required
def fatura_create(request):
    """ Tela de emissão de cobrança """
    return render(request, 'fatura_form.html', {
        'pacientes': Paciente.objects.all().order_by('nome_completo'),
        'today': timezone.now()
    })

@login_required
def fatura_store(request):
    """ Processa e salva a fatura com desconto automático """
    if request.method == 'POST':
        paciente = get_object_or_404(Paciente, id=request.POST.get('paciente'))
        valor_base = request.POST.get('valor_base')
        
        valor_final = calcular_valor_com_desconto(paciente, valor_base)
        
        Fatura.objects.create(
            paciente=paciente,
            valor=valor_final,
            data_vencimento=request.POST.get('data_vencimento'),
            status='PENDENTE'
        )
    return redirect('sistema_interno:master_dashboard')

# =================================================================
# 5. ATENDIMENTO MÉDICO E DASHBOARDS
# =================================================================

@login_required
def painel_medico(request):
    return render(request, 'painel_medico.html', {'pacientes': Paciente.objects.all()})

@login_required
def prontuario_view(request, paciente_id):
    if request.user.username == 'recepcao':
        return redirect('sistema_interno:painel_colaborador')
    
    p = get_object_or_404(Paciente, id=paciente_id)
    if request.method == 'POST':
        Prontuario.objects.create(
            paciente=p, medico=request.user,
            evolucao=request.POST.get('evolucao'),
            prescricao=request.POST.get('prescricao')
        )
        return redirect('sistema_interno:painel_medico')
        
    hist = Prontuario.objects.filter(paciente=p).order_by('-data_atendimento')
    return render(request, 'prontuario.html', {'paciente': p, 'historico': hist})

@login_required
def master_dashboard(request):
    if not request.user.is_superuser and request.user.username != 'master':
        return redirect('sistema_interno:login')
    
    pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    leads = LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')
    return render(request, 'master_dashboard.html', {
        'faturamento_total': pago, 
        'leads_recentes': leads
    })

@login_required
def painel_colaborador(request):
    leads = LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')
    return render(request, 'painel_colaborador.html', {'leads_recentes': leads})

# --- APIS E AUXILIARES RESTANTES ---
@csrf_exempt
def api_lead_capture(request):
    if request.method == 'POST':
        nome, tel = request.POST.get('nome'), request.POST.get('telefone')
        if nome and tel:
            LeadSite.objects.create(nome=nome, telefone=tel, interesse=request.POST.get('interesse', 'Geral'))
            return JsonResponse({'status': 'sucesso', 'success': True})
    return JsonResponse({'status': 'erro', 'success': False}, status=400)

def agenda_view(request): return render(request, 'agenda.html')
def fatura_baixar(request, fatura_id): return redirect('sistema_interno:master_dashboard')
def plan_create(request): return redirect('sistema_interno:master_dashboard')
