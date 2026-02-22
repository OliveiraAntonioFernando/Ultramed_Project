from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Avg, Count
from django.utils import timezone
from datetime import timedelta, date
from django.contrib import messages
from django.conf import settings
import mercadopago

from .models import Paciente, Fatura, Prontuario, LeadSite, Plano, Exame, Agenda, Receita

# =================================================================
# 1. REGRAS DE NEGÓCIO (LÓGICA DE DESCONTOS E FINANCEIRO)
# =================================================================

def calcular_valor_com_desconto(paciente, valor_base):
    """ Calcula o valor final garantindo que Particulares paguem 100% """
    hoje = timezone.now().date()
    try:
        if isinstance(valor_base, str):
            valor_base = valor_base.replace(',', '.')
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
            data_nascimento=request.POST.get('data_nascimento') or "1900-01-01",
            sexo=request.POST.get('sexo', 'M'),
            endereco=request.POST.get('endereco'),
            bairro=request.POST.get('bairro'),
            cidade=request.POST.get('cidade', 'São Félix do Xingu'),
            possui_dependentes=request.POST.get('possui_dependentes') == 'on',
            is_titular=True,
            modalidade_plano=request.POST.get('modalidade_plano'),
            plano_id=plano_id if plano_id else None,
            vencimento_plano=vencimento
        )

        nomes_dep = request.POST.getlist('dep_nome[]')
        cpfs_dep = request.POST.getlist('dep_cpf[]')
        nasc_dep = request.POST.getlist('dep_nascimento[]') 

        for i in range(len(nomes_dep)):
            if nomes_dep[i].strip():
                dt_nasc = nasc_dep[i] if i < len(nasc_dep) and nasc_dep[i] else "1900-01-01"
                Paciente.objects.create(
                    nome_completo=nomes_dep[i],
                    cpf=cpfs_dep[i] if i < len(cpfs_dep) and cpfs_dep[i] else None,
                    data_nascimento=dt_nasc,
                    is_titular=False,
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
    paciente = get_object_or_404(Paciente, id=paciente_id)
    plano = get_object_or_404(Plano, id=plano_id)
    
    fatura = Fatura.objects.create(
        paciente=paciente,
        valor=plano.valor_anual,
        data_vencimento=timezone.now().date(),
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

    pref_res = sdk.preference().create(preference_data)
    
    if pref_res["status"] == 200 or pref_res["status"] == 201:
        preference = pref_res["response"]
        return render(request, 'checkout.html', {
            'preference_id': preference['id'],
            'public_key': settings.MERCADO_PAGO_PUBLIC_KEY,
            'paciente': paciente,
            'plano': plano,
            'link_pagamento': preference.get('init_point')
        })
    return HttpResponse(f"Erro Mercado Pago: {pref_res['response'].get('message', 'Erro desconhecido')}")

@csrf_exempt
def mercadopago_webhook(request):
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
                        fatura.data_pagamento = timezone.now().date()
                        fatura.mercadopago_id = str(payment_id)
                        fatura.save()
                        
                        p = fatura.paciente
                        hoje = timezone.now().date()
                        base = p.vencimento_plano if p.vencimento_plano and p.vencimento_plano > hoje else hoje
                        novo_vencimento = base + timedelta(days=365)
                        p.vencimento_plano = novo_vencimento
                        p.save()
                        Paciente.objects.filter(responsavel=p).update(vencimento_plano=novo_vencimento)
                        
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
        valor = request.POST.get('valor').replace(',', '.')
        
        fatura = Fatura.objects.create(
            paciente=paciente,
            valor=valor,
            data_vencimento=timezone.now().date(),
            metodo_pagamento=request.POST.get('metodo_pagamento'),
            status=status,
            data_pagamento=timezone.now().date() if status == 'PAGO' else None
        )
        
        if status == 'PAGO':
            hoje = timezone.now().date()
            data_base = paciente.vencimento_plano if paciente.vencimento_plano and paciente.vencimento_plano > hoje else hoje
            novo_vencimento = data_base + timedelta(days=365)
            paciente.vencimento_plano = novo_vencimento
            paciente.save()
            Paciente.objects.filter(responsavel=paciente).update(vencimento_plano=novo_vencimento)
            
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
        try:
            paciente_id = request.POST.get('paciente_id')
            paciente = get_object_or_404(Paciente, id=paciente_id)
            tipo = request.POST.get('tipo')
            exame_nome = request.POST.get('exame_nome', 'Consulta')
            valor_cheio = request.POST.get('valor_cheio', '0').replace(',', '.')
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
                data_vencimento=timezone.now().date(),
                metodo_pagamento='PIX/CARTAO',
                status='PAGO',
                data_pagamento=timezone.now().date()
            )
            messages.success(request, "Agendamento realizado com sucesso!")
            return redirect('sistema_interno:painel_colaborador')
        except Exception as e:
            messages.error(request, f"Erro ao salvar: {e}")

    agendamentos = Agenda.objects.filter(data=hoje).order_by('hora')
    return render(request, 'agenda.html', {'agendamentos': agendamentos})

# =================================================================
# 5. PAINÉIS (MASTER DASHBOARD ATUALIZADO COM BI E CRM)
# =================================================================

@login_required
def master_dashboard(request):
    hoje = timezone.now().date()
    
    # 1. Filtros de CRM e Doenças Crônicas
    doenca_filtro = request.GET.get('doenca')
    q_busca = request.GET.get('q', '')
    
    pacientes_lista = Paciente.objects.filter(is_titular=True)
    
    if doenca_filtro:
        pacientes_lista = pacientes_lista.filter(doencas_cronicas__icontains=doenca_filtro)
    
    if q_busca:
        pacientes_lista = pacientes_lista.filter(
            Q(nome_completo__icontains=q_busca) | Q(cpf__icontains=q_busca)
        )
    
    # 2. Dados Financeiros do Mês
    pago = Fatura.objects.filter(
        status='PAGO', 
        data_pagamento__month=timezone.now().month,
        data_pagamento__year=timezone.now().year
    ).aggregate(Sum('valor'))['valor__sum'] or 0
    
    # 3. Alertas e Leads
    alertas = Paciente.objects.filter(vencimento_plano__range=[hoje, hoje + timedelta(days=30)], is_titular=True)
    leads = LeadSite.objects.filter(atendido=False).order_by('-id')
    
    # 4. Estatísticas Gerais e BI
    total_pacientes = Paciente.objects.count()
    total_cronicos = Paciente.objects.filter(is_cronico=True).count()
    porcentagem_cronicos = round((total_cronicos / total_pacientes * 100), 1) if total_pacientes > 0 else 0

    stats_doencas = {
        'Diabetes': Paciente.objects.filter(doencas_cronicas__icontains='DIABETES').count(),
        'Hipertensão': Paciente.objects.filter(doencas_cronicas__icontains='HIPERTENSAO').count(),
        'Asma': Paciente.objects.filter(doencas_cronicas__icontains='ASMA').count(),
        'Outros': Paciente.objects.filter(is_cronico=True).exclude(
            Q(doencas_cronicas__icontains='DIABETES') | 
            Q(doencas_cronicas__icontains='HIPERTENSAO') | 
            Q(doencas_cronicas__icontains='ASMA')
        ).count()
    }

    return render(request, 'master_dashboard.html', {
        'pacientes_lista': pacientes_lista,
        'doenca_selecionada': doenca_filtro,
        'faturamento_total': pago, 
        'leads_recentes': leads, 
        'pacientes_vencendo': alertas,
        'boletos_recentes': Fatura.objects.filter(status='PAGO').order_by('-id')[:10],
        'total_cronicos': total_cronicos,
        'porcentagem_cronicos': porcentagem_cronicos,
        'stats_doencas': stats_doencas
    })

@login_required
def painel_colaborador(request):
    hoje = timezone.now().date()
    leads = LeadSite.objects.filter(atendido=False).order_by('-id')
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
    paciente = get_object_or_404(Paciente, cpf=request.user.username)
    hoje = timezone.now().date()
    
    # Lógica de gatilho visual para o cartão (vencimento próximo < 10 dias)
    is_vencendo_ou_vencido = False
    if paciente.vencimento_plano:
        is_vencendo_ou_vencido = paciente.vencimento_plano <= (hoje + timedelta(days=10))

    context = {
        'paciente': paciente,
        'is_vencendo_ou_vencido': is_vencendo_ou_vencido,
        'exames': Exame.objects.filter(paciente=paciente).order_by('-data_solicitacao'),
        'receitas': Receita.objects.filter(paciente=paciente).order_by('-data_emissao'),
        'consultas': Agenda.objects.filter(paciente=paciente).order_by('-data', '-hora'),
    }
    return render(request, 'painel_paciente.html', context)

# =================================================================
# 6. APIs E GESTÃO MÉDICA
# =================================================================

@login_required
def baixar_lead(request, lead_id):
    lead = get_object_or_404(LeadSite, id=lead_id)
    lead.atendido = True
    lead.save()
    return redirect(request.META.get('HTTP_REFERER', 'sistema_interno:painel_colaborador'))

@login_required
@csrf_exempt
def solicitar_renovacao_api(request):
    try:
        paciente = Paciente.objects.get(cpf=request.user.username)
        LeadSite.objects.create(
            nome=paciente.nome_completo,
            telefone=paciente.telefone,
            interesse=f"RENOVAÇÃO DE RECEITA - ID: {paciente.id}",
            atendido=False
        )
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False}, status=400)

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
    if request.method == 'POST':
        nome = request.POST.get('nome')
        tel = request.POST.get('telefone')
        int_ = request.POST.get('interesse', 'Geral')
        LeadSite.objects.create(nome=nome, telefone=tel, interesse=int_, atendido=False)
        return JsonResponse({'success': True})
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

def fatura_baixar(request, fatura_id): 
    f = get_object_or_404(Fatura, id=fatura_id)
    f.status = 'PAGO'
    f.data_pagamento = timezone.now().date()
    f.save()
    return redirect('sistema_interno:master_dashboard')

def plan_create(request): return redirect('sistema_interno:master_dashboard')

def cadastro_plano_completo(request, plano_nome):
    if request.method == 'POST':
        nome = request.POST.get('titular_nome') or request.POST.get('nome')
        cpf = request.POST.get('titular_cpf') or request.POST.get('cpf')
        tel = request.POST.get('titular_telefone') or request.POST.get('telefone')
        end = request.POST.get('endereco')
        sexo = request.POST.get('titular_sexo') or request.POST.get('sexo') or 'M'
        nasc = request.POST.get('titular_nascimento') or request.POST.get('data_nascimento')
        
        if not nasc: nasc = "1900-01-01"

        try:
            p = Paciente.objects.create(
                nome_completo=nome, cpf=cpf, telefone=tel,
                data_nascimento=nasc, endereco=end, sexo=sexo, cidade="SFX",
                is_titular=True
            )
            plano = Plano.objects.filter(nome__icontains=plano_nome).first() or Plano.objects.first()
            return redirect('sistema_interno:checkout_pagamento', paciente_id=p.id, plano_id=plano.id)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'cadastro_plano.html', {'plano_selecionado': plano_nome})