from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.conf import settings
import mercadopago

from .models import Paciente, Fatura, Prontuario, LeadSite, Plano, Exame, Agenda, Receita, Pagamento

# =================================================================
# 1. REGRAS DE NEGÓCIO (LÓGICA DE DESCONTOS E FINANCEIRO)
# =================================================================

def calcular_valor_com_desconto(paciente, valor_base):
    """ Calcula o valor final garantindo que Particulares paguem 100% """
    hoje = timezone.now().date()
    try:
        valor_base = float(valor_base)
    except:
        valor_base = 0.0

    if not paciente.plano:
        return valor_base

    if not paciente.vencimento_plano or paciente.vencimento_plano < hoje:
        return valor_base

    plano_nome = paciente.plano.nome.upper()
    desconto = 0.0

    if 'ESSENCIAL' in plano_nome:
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
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

# =================================================================
# 3. GESTÃO DE PACIENTES E UPLOAD DE EXAMES
# =================================================================

@login_required
def upload_exame(request):
    """ API para a recepção anexar exames ao paciente sem entrar no prontuário """
    if request.method == 'POST' and request.FILES.get('arquivo_exame'):
        paciente_id = request.POST.get('paciente_id')
        paciente = get_object_or_404(Paciente, id=paciente_id)
        
        Exame.objects.create(
            paciente=paciente,
            nome_exame=request.POST.get('nome_exame'),
            arquivo=request.FILES.get('arquivo_exame'),
            realizado=True,
            data_solicitacao=timezone.now().date()
        )
        messages.success(request, f"Exame anexado com sucesso para {paciente.nome_completo}")
        return redirect('sistema_interno:cliente_list')
    return redirect('sistema_interno:cliente_list')

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
# 4. FINANCEIRO, AGENDA E MERCADO PAGO
# =================================================================

@login_required
def checkout_pagamento(request, paciente_id, plano_id):
    """ Gera a preferência de pagamento no Mercado Pago e cria a Fatura """
    paciente = get_object_or_404(Paciente, id=paciente_id)
    plano = get_object_or_404(Plano, id=plano_id)
    
    # Cria a fatura como PENDENTE antes de enviar ao MP
    fatura = Fatura.objects.create(
        paciente=paciente,
        valor=plano.valor_anual,
        status='PENDENTE',
        metodo_pagamento='PIX/CARTAO'
    )

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    preference_data = {
        "items": [
            {
                "id": str(fatura.id),
                "title": f"Plano {plano.nome} - {paciente.nome_completo}",
                "quantity": 1,
                "unit_price": float(plano.valor_anual),
            }
        ],
        "payer": {
            "name": paciente.nome_completo,
            "email": "financeiro@ultramedsaudexingu.com.br",
            "identification": {"type": "CPF", "number": paciente.cpf.replace(".","").replace("-","") if paciente.cpf else "00000000000"}
        },
        "back_urls": {
            "success": "https://ultramedsaudexingu.com.br/sistema/painel/",
            "failure": "https://ultramedsaudexingu.com.br/sistema/painel/",
        },
        "auto_return": "approved",
        "external_reference": str(fatura.id),
        "notification_url": "https://ultramedsaudexingu.com.br/sistema/api/v1/mp/webhook/",
    }

    preference = sdk.preference().create(preference_data)["response"]

    return render(request, 'core_gestao/checkout.html', {
        'preference_id': preference['id'],
        'public_key': settings.MERCADO_PAGO_PUBLIC_KEY,
        'paciente': paciente,
        'plano': plano
    })

@csrf_exempt
def mercadopago_webhook(request):
    """ Webhook que dá baixa automática e renova o plano """
    if request.method == 'POST':
        payment_id = request.GET.get('data.id') or request.POST.get('data.id')
        if payment_id:
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            payment_info = sdk.payment().get(payment_id)
            if payment_info["status"] == 200:
                resposta = payment_info["response"]
                fatura_id = resposta.get("external_reference")
                if resposta.get("status") == "approved":
                    fatura = Fatura.objects.filter(id=fatura_id).first()
                    if fatura and fatura.status != 'PAGO':
                        fatura.status = 'PAGO'
                        fatura.data_pagamento = timezone.now()
                        fatura.save()
                        p = fatura.paciente
                        hoje = timezone.now().date()
                        base = p.vencimento_plano if p.vencimento_plano and p.vencimento_plano > hoje else hoje
                        p.vencimento_plano = base + timedelta(days=365)
                        p.save()
                        Paciente.objects.filter(responsavel=p).update(vencimento_plano=p.vencimento_plano)
        return JsonResponse({'status': 'ok'}, status=200)
    return JsonResponse({'status': 'erro'}, status=400)

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
        valor = request.POST.get('valor')
        
        fatura = Fatura.objects.create(
            paciente=paciente,
            valor=valor,
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
    
    total_pacientes = Paciente.objects.count()
    total_cronicos = Paciente.objects.filter(is_cronico=True).count()
    porcentagem_cronicos = round((total_cronicos / total_pacientes * 100), 1) if total_pacientes > 0 else 0

    return render(request, 'master_dashboard.html', {
        'faturamento_total': pago, 
        'leads_recentes': leads, 
        'pacientes_vencendo': alertas,
        'boletos_recentes': Fatura.objects.filter(status='PAGO').order_by('-id')[:10],
        'total_cronicos': total_cronicos,
        'porcentagem_cronicos': porcentagem_cronicos
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

@login_required
def painel_paciente(request):
    """ Painel exclusivo do Paciente com seu Histórico de Saúde """
    paciente = get_object_or_404(Paciente, cpf=request.user.username)
    context = {
        'paciente': paciente,
        'exames': Exame.objects.filter(paciente=paciente).order_by('-data_solicitacao'),
        'receitas': Receita.objects.filter(paciente=paciente).order_by('-data_emissao'),
        'consultas': Agenda.objects.filter(paciente=paciente).order_by('-data', '-hora'),
    }
    return render(request, 'painel_paciente.html', context)

# =================================================================
# 6. APIs E GESTÃO MÉDICA
# =================================================================

@login_required
def salvar_doencas_cronicas(request, paciente_id):
    if request.method == 'POST':
        paciente = get_object_or_404(Paciente, id=paciente_id)
        selecionadas = request.POST.getlist('doencas[]')
        paciente.doencas_cronicas = ", ".join(selecionadas)
        paciente.is_cronico = len(selecionadas) > 0
        paciente.save()
        return JsonResponse({
            'success': True, 
            'is_cronico': paciente.is_cronico,
            'texto_doencas': paciente.doencas_cronicas or "Classificar Crônico"
        })
    return JsonResponse({'success': False}, status=400)

@login_required
def api_ultima_receita(request, paciente_id):
    ultima = Receita.objects.filter(paciente_id=paciente_id).order_by('-data_emissao').first()
    if ultima:
        return JsonResponse({'success': True, 'conteudo': ultima.conteudo})
    return JsonResponse({'success': False})

@login_required
def api_buscar_paciente(request):
    q = request.GET.get('q', '')
    pacientes = Paciente.objects.filter(Q(nome_completo__icontains=q) | Q(cpf__icontains=q))[:10]
    results = [{'id': p.id, 'text': f"{p.nome_completo} ({p.cpf})"} for p in pacientes]
    return JsonResponse({'results': results})

@login_required
def api_detalhes_paciente(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    hoje = timezone.now().date()
    percentual = 0.0
    plano_status = "PARTICULAR"

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
        plano_status = "PARTICULAR / PLANO VENCIDO"

    return JsonResponse({
        'id': paciente.id,
        'plano': plano_status,
        'percentual': percentual,
        'cpf': paciente.cpf
    })

@csrf_exempt
def api_lead_capture(request):
    """ Captura Lead do site, cria Paciente e retorna IDs para o Modal """
    if request.method == 'POST':
        nome = request.POST.get('nome')
        tel = request.POST.get('telefone')
        int_ = request.POST.get('interesse', 'Geral')
        
        LeadSite.objects.create(nome=nome, telefone=tel, interesse=int_)
        
        p = Paciente.objects.create(nome_completo=nome, telefone=tel, endereco="Site", cidade="SFX")
        
        plano = Plano.objects.filter(nome__icontains=int_.split()[-1]).first() or Plano.objects.first()
        
        return JsonResponse({'success': True, 'paciente_id': p.id, 'plano_id': plano.id if plano else 1})
    return JsonResponse({'success': False}, status=400)

@login_required
def prontuario_view(request, paciente_id):
    if request.user.username == 'recepcao' and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Apenas médicos podem acessar o prontuário.")
        return redirect('sistema_interno:cliente_list')

    p = get_object_or_404(Paciente, id=paciente_id)
    if request.method == 'POST':
        evolucao = request.POST.get('evolucao')
        prescricao = request.POST.get('prescricao')
        Prontuario.objects.create(paciente=p, medico=request.user, evolucao=evolucao, prescricao=prescricao)
        if prescricao and prescricao.strip():
            Receita.objects.create(paciente=p, medico=request.user, conteudo=prescricao)
        Agenda.objects.filter(paciente=p, data=timezone.now().date(), status='CHEGOU').update(status='FINALIZADO')
        return redirect('sistema_interno:painel_medico')
        
    hist = Prontuario.objects.filter(paciente=p).order_by('-data_atendimento')
    exames = Exame.objects.filter(paciente=p).order_by('-id')
    return render(request, 'prontuario.html', {'paciente': p, 'historico': hist, 'exames': exames})

def fatura_baixar(request, fatura_id): return redirect('sistema_interno:master_dashboard')
def plan_create(request): return redirect('sistema_interno:master_dashboard')