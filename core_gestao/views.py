from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import Paciente, Fatura, Prontuario, LeadSite, Plano, Exame, Agenda

# =================================================================
# 1. REGRAS DE NEGÓCIO (LÓGICA DE DESCONTOS BLINDADA)
# =================================================================

def calcular_valor_com_desconto(paciente, valor_base):
    """ Calcula o valor final garantindo que Particulares paguem 100% """
    hoje = timezone.now().date()
    try:
        valor_base = float(valor_base)
    except:
        valor_base = 0.0

    # TRAVA DE SEGURANÇA: Se não tem plano vinculado, é PARTICULAR (Sem desconto)
    if not paciente.plano:
        return valor_base

    # TRAVA DE VENCIMENTO: Se o plano expirou, vira PARTICULAR automaticamente
    if not paciente.vencimento_plano or paciente.vencimento_plano < hoje:
        return valor_base

    plano_nome = paciente.plano.nome.upper()
    desconto = 0.0

    # Cálculo por categoria de plano ativo
    if 'ESSENCIAL' in plano_nome:
        # Regra Essencial: 30% no primeiro uso do mês, 20% nos demais
        ja_usou_este_mes = Prontuario.objects.filter(
            paciente=paciente,
            data_atendimento__month=timezone.now().month,
            data_atendimento__year=timezone.now().year
        ).exists()
        desconto = 0.30 if not ja_usou_este_mes else 0.20
    elif 'MASTER' in plano_nome:
        desconto = 0.30
    elif 'EMPRESARIAL' in plano_nome:
        desconto = 0.35
    
    # Retorna o valor com o desconto aplicado
    return valor_base * (1 - desconto)

# =================================================================
# 2. SISTEMA DE ACESSO
# =================================================================

def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            if user.username == 'medico': return redirect('sistema_interno:painel_medico')
            if user.username == 'recepcao': return redirect('sistema_interno:painel_colaborador')
            if user.username == 'master' or user.is_superuser: return redirect('sistema_interno:master_dashboard')
            return redirect('sistema_interno:painel_paciente')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

# =================================================================
# 3. GESTÃO DE PACIENTES
# =================================================================

@login_required
def cliente_list(request):
    context = {
        'pacientes': Paciente.objects.filter(responsavel__isnull=True).order_by('-data_cadastro'),
        'planos': Plano.objects.all()
    }
    return render(request, 'cliente_list.html', context)

@login_required
def cliente_create(request):
    if request.method == 'POST':
        plano_id = request.POST.get('plano')
        venc_input = request.POST.get('vencimento_plano')
        vencimento = venc_input if venc_input else (timezone.now().date() + timedelta(days=365))

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
            plano_id=plano_id if plano_id else None,
            vencimento_plano=vencimento
        )

        nomes_dep = request.POST.getlist('dep_nome[]')
        cpfs_dep = request.POST.getlist('dep_cpf[]')
        for i in range(len(nomes_dep)):
            if nomes_dep[i].strip():
                Paciente.objects.create(
                    nome_completo=nomes_dep[i],
                    cpf=cpfs_dep[i] if i < len(cpfs_dep) else None,
                    responsavel=titular,
                    plano=titular.plano,
                    vencimento_plano=titular.vencimento_plano
                )
    return redirect('sistema_interno:cliente_list')

# =================================================================
# 4. FINANCEIRO E AGENDA
# =================================================================

@login_required
def fatura_create(request):
    return render(request, 'fatura_form.html', {
        'pacientes': Paciente.objects.all().order_by('nome_completo'),
        'today': timezone.now()
    })

@login_required
def fatura_store(request):
    if request.method == 'POST':
        paciente = get_object_or_404(Paciente, id=request.POST.get('paciente'))
        status = request.POST.get('status').upper()
        Fatura.objects.create(
            paciente=paciente,
            valor=request.POST.get('valor'),
            metodo_pagamento=request.POST.get('metodo_pagamento'),
            status=status,
            data_pagamento=timezone.now() if status == 'PAGO' else None
        )
        if status == 'PAGO':
            hoje = timezone.now().date()
            data_base = paciente.vencimento_plano if paciente.vencimento_plano and paciente.vencimento_plano > hoje else hoje
            paciente.vencimento_plano = data_base + timedelta(days=365)
            paciente.save()
            Paciente.objects.filter(responsavel=paciente).update(vencimento_plano=paciente.vencimento_plano)
    return redirect('sistema_interno:master_dashboard')

@login_required
def agenda_view(request):
    hoje = timezone.now().date()

    agendamento_id = request.GET.get('id')
    novo_status = request.GET.get('status')
    if agendamento_id and novo_status:
        ag = get_object_or_404(Agenda, id=agendamento_id)
        ag.status = novo_status
        ag.save()
        return redirect('sistema_interno:painel_colaborador')

    if request.method == 'POST':
        paciente_id = request.POST.get('paciente_id')
        paciente = get_object_or_404(Paciente, id=paciente_id)

        tipo = request.POST.get('tipo')
        exame_nome = request.POST.get('exame_nome', 'Consulta')
        valor_cheio = request.POST.get('valor_cheio', 0)
        comprovante = request.POST.get('comprovante', 'N/A')

        # AQUI O SISTEMA RECALCULA NO SERVIDOR POR SEGURANÇA
        valor_final = calcular_valor_com_desconto(paciente, valor_cheio)

        Agenda.objects.create(
            paciente=paciente,
            data=request.POST.get('data'),
            hora=request.POST.get('hora'),
            tipo=tipo,
            status='AGENDADO',
            observacoes=f"Procedimento: {exame_nome} | Ref: {comprovante} | V.Tabela: {valor_cheio} | V.Final: {valor_final}"
        )

        Fatura.objects.create(
            paciente=paciente,
            valor=valor_final,
            metodo_pagamento='PIX/CARTAO',
            status='PAGO',
            data_pagamento=timezone.now()
        )
        return redirect('sistema_interno:painel_colaborador')

    agendamentos = Agenda.objects.filter(data=hoje).order_by('hora')
    return render(request, 'agenda.html', {'agendamentos': agendamentos})

# =================================================================
# 5. PAINÉIS
# =================================================================

@login_required
def master_dashboard(request):
    hoje = timezone.now().date()
    alertas = Paciente.objects.filter(vencimento_plano__range=[hoje, hoje + timedelta(days=30)], responsavel__isnull=True)
    pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    leads = LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')
    return render(request, 'master_dashboard.html', {
        'faturamento_total': pago, 'leads_recentes': leads, 'pacientes_vencendo': alertas,
        'boletos_recentes': Fatura.objects.filter(status='PAGO').order_by('-id')[:10]
    })

@login_required
def painel_colaborador(request):
    hoje = timezone.now().date()
    leads = LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')
    agendamentos_hoje = Agenda.objects.filter(data=hoje).order_by('hora')
    return render(request, 'painel_colaborador.html', {
        'leads_recentes': leads,
        'agendamentos_hoje': agendamentos_hoje
    })

@login_required
def painel_medico(request):
    espera = Agenda.objects.filter(data=timezone.now().date(), status='CHEGOU').order_by('hora')
    return render(request, 'painel_medico.html', {'pacientes_espera': espera})

# =================================================================
# 6. APIs E OUTROS
# =================================================================

@login_required
def api_buscar_paciente(request):
    q = request.GET.get('q', '')
    pacientes = Paciente.objects.filter(Q(nome_completo__icontains=q) | Q(cpf__icontains=q))[:10]
    results = [{'id': p.id, 'text': f"{p.nome_completo} ({p.cpf})"} for p in pacientes]
    return JsonResponse({'results': results})

@login_required
def api_detalhes_paciente(request, paciente_id):
    """ API ajustada para garantir 0% de desconto para particulares e vencidos """
    paciente = get_object_or_404(Paciente, id=paciente_id)
    hoje = timezone.now().date()

    percentual = 0.0
    plano_status = "PARTICULAR"

    # Verificação rígida de Plano e Validade
    if paciente.plano and paciente.vencimento_plano and paciente.vencimento_plano >= hoje:
        plano_nome = paciente.plano.nome.upper()
        plano_status = plano_nome

        if 'ESSENCIAL' in plano_nome:
            ja_usou_este_mes = Prontuario.objects.filter(
                paciente=paciente,
                data_atendimento__month=timezone.now().month,
                data_atendimento__year=timezone.now().year
            ).exists()
            percentual = 0.30 if not ja_usou_este_mes else 0.20
        elif 'MASTER' in plano_nome:
            percentual = 0.30
        elif 'EMPRESARIAL' in plano_nome:
            percentual = 0.35
    else:
        # Se cair aqui, ou não tem plano ou está vencido
        plano_status = "PARTICULAR / PLANO VENCIDO"
        percentual = 0.0

    return JsonResponse({
        'id': paciente.id,
        'plano': plano_status,
        'percentual': percentual,
        'cpf': paciente.cpf
    })

@csrf_exempt
def api_lead_capture(request):
    if request.method == 'POST':
        LeadSite.objects.create(nome=request.POST.get('nome'), telefone=request.POST.get('telefone'), interesse=request.POST.get('interesse', 'Geral'))
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@login_required
def prontuario_view(request, paciente_id):
    p = get_object_or_404(Paciente, id=paciente_id)
    if request.method == 'POST':
        Prontuario.objects.create(paciente=p, medico=request.user, evolucao=request.POST.get('evolucao'))
        Agenda.objects.filter(paciente=p, data=timezone.now().date(), status='CHEGOU').update(status='FINALIZADO')
        return redirect('sistema_interno:painel_medico')
    hist = Prontuario.objects.filter(paciente=p).order_by('-data_atendimento')
    return render(request, 'prontuario.html', {'paciente': p, 'historico': hist})

def painel_paciente(request): return render(request, 'painel_paciente.html')
def fatura_baixar(request, fatura_id): return redirect('sistema_interno:master_dashboard')
def plan_create(request): return redirect('sistema_interno:master_dashboard')
