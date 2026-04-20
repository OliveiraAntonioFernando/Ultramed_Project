from functools import wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Avg, Count
from django.utils import timezone
from datetime import timedelta, date
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
import mercadopago
from mercadopago.config import RequestOptions
import json
import logging
import re
import uuid

from .models import Paciente, Fatura, Prontuario, LeadSite, Plano, Exame, Agenda, Receita

logger = logging.getLogger(__name__)

# =================================================================
# DADOS DE TESTE OFICIAIS (SANDBOX)
# =================================================================
CPF_TESTE_OFICIAL = "12345678909"

_STAFF_USERNAMES = frozenset({"medico", "recepcao", "master"})


def _is_staff_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or getattr(user, "username", "") in _STAFF_USERNAMES)
    )


def _is_master_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or getattr(user, "username", "") == "master")
    )


def _is_medico_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "username", "") in ("master", "medico")
        )
    )


def _recepcao_ou_master(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "username", "") in ("master", "recepcao")
        )
    )


def _staff_home_redirect(user):
    if getattr(user, "username", "") == "medico":
        return redirect("sistema_interno:painel_medico")
    if getattr(user, "username", "") == "recepcao":
        return redirect("sistema_interno:painel_colaborador")
    if user.is_superuser or getattr(user, "username", "") == "master":
        return redirect("sistema_interno:master_dashboard")
    return redirect("sistema_interno:painel_colaborador")


def staff_member_required(view_func):
    @wraps(view_func)
    def _wrap(request, *args, **kwargs):
        if not _is_staff_user(request.user):
            messages.error(request, "Acesso restrito à equipe Ultramed.")
            return redirect("sistema_interno:painel_paciente")
        return view_func(request, *args, **kwargs)

    return _wrap


def master_member_required(view_func):
    @wraps(view_func)
    def _wrap(request, *args, **kwargs):
        if not _is_master_user(request.user):
            messages.error(request, "Acesso restrito ao financeiro / master.")
            return _staff_home_redirect(request.user)
        return view_func(request, *args, **kwargs)

    return _wrap


def recepcao_ou_master_required(view_func):
    @wraps(view_func)
    def _wrap(request, *args, **kwargs):
        if not _recepcao_ou_master(request.user):
            messages.error(request, "Acesso restrito à recepção.")
            return _staff_home_redirect(request.user)
        return view_func(request, *args, **kwargs)

    return _wrap


def _pode_ver_dados_clinicos_paciente(user, paciente_id):
    if _is_staff_user(user):
        return True
    try:
        p = Paciente.objects.select_related("responsavel").get(pk=paciente_id)
    except Paciente.DoesNotExist:
        return False
    uname = getattr(user, "username", "")
    if p.cpf == uname:
        return True
    if p.responsavel_id and p.responsavel.cpf == uname:
        return True
    return False


def _mp_limpar_cpf(valor, fallback=CPF_TESTE_OFICIAL):
    digitos = re.sub(r"\D", "", str(valor or ""))
    return digitos if len(digitos) >= 11 else fallback


def _mp_credencial_teste():
    return (getattr(settings, "MERCADO_PAGO_ACCESS_TOKEN", "") or "").startswith("TEST-")


def _mp_email_comprador_sandbox():
    return (getattr(settings, "MERCADO_PAGO_TEST_PAYER_EMAIL", "") or "").strip().lower()


def _mp_email_teste_valido(email):
    email = (email or "").strip().lower()
    return email.endswith("@testuser.com")


def _mp_payer_do_payload(data, paciente):
    """Monta payer para a API MP. Em sandbox, e-mail é sempre @testuser.com (Brick pode enviar e-mail real)."""
    payer_in = data.get("payer") or {}
    if _mp_credencial_teste():
        email_brick = (payer_in.get("email") or "").strip().lower()
        email_cfg = _mp_email_comprador_sandbox()
        email = email_brick or email_cfg
    else:
        email = (payer_in.get("email") or "").strip()
    ident = payer_in.get("identification") or {}
    cpf = _mp_limpar_cpf(ident.get("number") or paciente.cpf)
    return {
        "email": email,
        "identification": {"type": "CPF", "number": cpf},
    }


def _mp_installments(val):
    try:
        return max(1, int(float(val)))
    except (TypeError, ValueError):
        return 1


def _mp_timeout_seconds():
    try:
        return max(5, int(getattr(settings, "MERCADO_PAGO_TIMEOUT_SECONDS", 15)))
    except (TypeError, ValueError):
        return 15


def _mp_max_attempts():
    try:
        return max(1, int(getattr(settings, "MERCADO_PAGO_MAX_ATTEMPTS", 2)))
    except (TypeError, ValueError):
        return 2


def _mp_should_retry(resp):
    if not isinstance(resp, dict):
        return True
    status = resp.get("status")
    return status in (429, 500, 502, 503, 504)


def _mp_call_with_timeout(callable_, *args):
    timeout = _mp_timeout_seconds()
    max_attempts = _mp_max_attempts()
    last_response = None

    for attempt in range(1, max_attempts + 1):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(callable_, *args)
                response = future.result(timeout=timeout)
        except FuturesTimeoutError:
            response = {
                "status": 504,
                "response": {
                    "message": f"timeout_after_{timeout}s",
                    "status_detail": "gateway_timeout",
                },
            }
        except Exception as exc:
            response = {"status": 500, "response": {"message": str(exc)}}

        last_response = response
        if not _mp_should_retry(response):
            break
        if attempt < max_attempts:
            logger.warning(
                "Retry de chamada Mercado Pago (tentativa %s/%s).",
                attempt + 1,
                max_attempts,
            )
    return last_response or {"status": 500, "response": {"message": "empty_response"}}


def _email_paciente_por_cpf(cpf):
    return (
        User.objects.filter(username=cpf)
        .values_list("email", flat=True)
        .first()
        or ""
    ).strip()


def _mp_payer_email_forbidden(resp):
    if not isinstance(resp, dict):
        return False
    if resp.get("status") != 403:
        return False
    body = resp.get("response") or {}
    message = (body.get("message") or "").lower()
    if "payer email forbidden" in message:
        return True
    for cause in body.get("cause") or []:
        desc = str((cause or {}).get("description", "")).lower()
        if "payer email forbidden" in desc:
            return True
    return False


def _mp_email_coletor(sdk):
    me = _mp_call_with_timeout(sdk.user().get)
    if me.get("status") != 200:
        return ""
    return (me.get("response") or {}).get("email", "").strip().lower()


def _mp_internal_error_retryable(resp):
    if not isinstance(resp, dict):
        return False
    status = resp.get("status")
    if not isinstance(status, int) or status < 500:
        return False
    message = str((resp.get("response") or {}).get("message", "")).lower()
    return "internal_error" in message or message == ""


# =================================================================
# 1. REGRAS DE NEGÓCIO (LÓGICA DE DESCONTOS E FINANCEIRO)
# =================================================================

def calcular_valor_com_desconto(paciente, valor_base):
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
@staff_member_required
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
@staff_member_required
def cliente_edit(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    
    if request.method == 'POST':
        try:
            paciente.nome_completo = request.POST.get('nome_completo')
            paciente.cpf = request.POST.get('cpf')
            paciente.telefone = request.POST.get('telefone')
            paciente.endereco = request.POST.get('endereco')
            paciente.save()
            messages.success(request, f"Paciente {paciente.nome_completo} atualizado com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar: {e}")
    return redirect('sistema_interno:cliente_list')

@login_required
@staff_member_required
def cliente_list(request):
    q = request.GET.get('q', '')
    pacientes = Paciente.objects.filter(responsavel__isnull=True).order_by('-data_cadastro')
    
    if q:
        pacientes = pacientes.filter(Q(nome_completo__icontains=q) | Q(cpf__icontains=q))

    context = {
        'pacientes': pacientes,
        'planos': Plano.objects.all(),
        'query': q
    }
    return render(request, 'cliente_list.html', context)

@login_required
@staff_member_required
def cliente_create(request):
    if request.method == 'POST':
        from django.contrib.auth.models import User
        plano_id = request.POST.get('plano')
        cpf = request.POST.get('cpf')
        email_form = request.POST.get('email')
        venc_input = request.POST.get('vencimento_plano')
        vencimento = venc_input if venc_input else (timezone.now().date() + timedelta(days=365))

        user, _ = User.objects.get_or_create(username=cpf)
        if email_form:
            user.email = email_form
            user.save()

        titular = Paciente.objects.create(
            nome_completo=request.POST.get('nome_completo'),
            cpf=cpf,
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
# 4. FINANCEIRO E MERCADO PAGO (CHECKOUT TRANSPARENTE)
# =================================================================

def checkout_pagamento(request, paciente_id, plano_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    plano = get_object_or_404(Plano, id=plano_id)
    
    valor_a_cobrar = float(plano.valor_anual)
    if valor_a_cobrar < 100:
        valor_a_cobrar = valor_a_cobrar * 12

    fatura = Fatura.objects.create(
        paciente=paciente,
        valor=valor_a_cobrar,
        data_vencimento=timezone.now().date(),
        status='PENDENTE',
        metodo_pagamento='PIX/CARTAO'
    )

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
    webhook_url = request.build_absolute_uri(reverse("sistema_interno:mp_webhook"))
    painel_url = request.build_absolute_uri(reverse("sistema_interno:painel_paciente"))
    email_paciente = _email_paciente_por_cpf(paciente.cpf)

    preference_data = {
        "items": [
            {
                "id": str(fatura.id),
                "title": f"Plano {plano.nome} - ANUIDADE",
                "quantity": 1,
                "unit_price": float(valor_a_cobrar),
                "currency_id": "BRL",
            }
        ],
        "payer": {
            "name": paciente.nome_completo,
            "identification": {
                "type": "CPF",
                "number": _mp_limpar_cpf(paciente.cpf),
            },
        },
        "back_urls": {
            "success": painel_url,
            "failure": painel_url,
        },
        "auto_return": "approved",
        "external_reference": str(fatura.id),
        "notification_url": webhook_url,
    }
    if email_paciente and not _mp_credencial_teste():
        preference_data["payer"]["email"] = email_paciente

    pref_res = _mp_call_with_timeout(sdk.preference().create, preference_data)
    
    if pref_res["status"] in [200, 201]:
        preference = pref_res["response"]
        return render(request, 'checkout.html', {
            'preference_id': preference['id'],
            'public_key': settings.MERCADO_PAGO_PUBLIC_KEY,
            'paciente': paciente,
            'plano': plano,
            'fatura': fatura,
            'mp_sandbox': _mp_credencial_teste(),
            'mp_test_payer_email': _mp_email_comprador_sandbox(),
            'payer_email': email_paciente if not _mp_credencial_teste() else "",
        })
    return HttpResponse(f"Erro Mercado Pago: {pref_res['response'].get('message', 'Erro desconhecido')}")

@csrf_exempt
def processar_pagamento_brick(request):
    if settings.DEBUG:
        logger.debug("Inicio do processamento do Payment Brick.")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if settings.DEBUG:
                logger.debug(
                    "Metodo recebido no Brick: %s", data.get("payment_method_id")
                )
            
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

            fatura_id = data.get("external_reference")
            fatura = get_object_or_404(Fatura, id=fatura_id)
            paciente = fatura.paciente
            payer = _mp_payer_do_payload(data, paciente)
            if settings.DEBUG:
                logger.debug("Payer email enviado ao MP: %s", payer.get("email"))
            pm_id = data.get("payment_method_id")
            token = data.get("token")
            descricao = f"Plano {paciente.plano.nome if paciente.plano else 'Ultramed'}"

            if pm_id == "pix":
                payment_data = {
                    "transaction_amount": float(fatura.valor),
                    "description": descricao,
                    "payment_method_id": "pix",
                    "payer": payer,
                    "external_reference": str(fatura_id),
                }
            elif token and pm_id:
                payment_data = {
                    "transaction_amount": float(fatura.valor),
                    "token": token,
                    "description": descricao,
                    "installments": _mp_installments(data.get("installments", 1)),
                    "payment_method_id": pm_id,
                    "payer": payer,
                    "external_reference": str(fatura_id),
                }
                issuer_id = data.get("issuer_id")
                if issuer_id is not None and str(issuer_id).strip() != "":
                    payment_data["issuer_id"] = str(issuer_id)
            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "detail": "Pagamento incompleto: use cartão com dados válidos ou PIX.",
                    },
                    status=400,
                )

            req_opts = RequestOptions(
                custom_headers={"x-idempotency-key": str(uuid.uuid4())}
            )

            if settings.DEBUG:
                logger.debug("Enviando pagamento para Mercado Pago.")
            payment_response = _mp_call_with_timeout(
                sdk.payment().create, payment_data, req_opts
            )
            if _mp_credencial_teste() and _mp_payer_email_forbidden(payment_response):
                email_fallback = _mp_email_coletor(sdk)
                email_atual = (
                    ((payment_data.get("payer") or {}).get("email") or "").strip().lower()
                )
                if email_fallback and email_fallback != email_atual:
                    logger.info(
                        "Fallback sandbox aplicado: retry com e-mail da conta coletora."
                    )
                    payment_data["payer"]["email"] = email_fallback
                    req_opts = RequestOptions(
                        custom_headers={"x-idempotency-key": str(uuid.uuid4())}
                    )
                    payment_response = _mp_call_with_timeout(
                        sdk.payment().create, payment_data, req_opts
                    )
            retries_interno = 0
            while _mp_internal_error_retryable(payment_response) and retries_interno < 2:
                retries_interno += 1
                logger.warning(
                    "Retry sandbox por erro interno do MP (tentativa %s).",
                    retries_interno,
                )
                req_opts = RequestOptions(
                    custom_headers={"x-idempotency-key": str(uuid.uuid4())}
                )
                payment_response = _mp_call_with_timeout(
                    sdk.payment().create, payment_data, req_opts
                )
            payment = payment_response.get("response") or {}
            logger.info("Status de resposta do Mercado Pago: %s", payment_response.get("status"))

            if payment_response.get("status") in [200, 201]:
                status_mp = payment.get("status")
                logger.info("Pagamento finalizado no MP com status: %s", status_mp)
                fatura.status = 'PAGO' if status_mp == "approved" else 'PENDENTE'
                fatura.data_pagamento = timezone.now().date() if status_mp == "approved" else None
                fatura.mercadopago_id = str(payment.get("id"))
                fatura.save()
                
                if status_mp == "approved":
                    hoje = timezone.now().date()
                    base = paciente.vencimento_plano if paciente.vencimento_plano and paciente.vencimento_plano > hoje else hoje
                    novo_vencimento = base + timedelta(days=365)
                    paciente.vencimento_plano = novo_vencimento
                    paciente.save()
                    Paciente.objects.filter(responsavel=paciente).update(vencimento_plano=novo_vencimento)

                return JsonResponse({"status": status_mp, "id": payment.get("id")})
            
            detalhe = (
                payment.get("status_detail")
                or payment.get("message")
                or "Dados inválidos"
            )
            logger.warning("Pagamento rejeitado pelo MP: %s", detalhe)
            return JsonResponse(
                {"status": "rejected", "detail": detalhe},
                status=200,
            )
            
        except Exception as e:
            logger.exception("Erro ao processar pagamento no Brick: %s", str(e))
            if hasattr(e, "response"):
                logger.error("Detalhe tecnico da resposta MP: %s", e.response)
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"status": "error"}, status=405)

@csrf_exempt
def mercadopago_webhook(request):
    if request.method == "POST":
        payment_id = None
        ctype = (request.content_type or "").lower()
        if "application/json" in ctype and request.body:
            try:
                payload = json.loads(request.body)
                inner = payload.get("data") or {}
                payment_id = inner.get("id")
            except json.JSONDecodeError:
                payment_id = None
        if not payment_id:
            payment_id = (
                request.GET.get("id")
                or request.GET.get("data.id")
                or request.POST.get("data.id")
            )
        if payment_id:
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            payment_info = _mp_call_with_timeout(sdk.payment().get, payment_id)
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
@master_member_required
def mp_healthcheck(request):
    has_public_key = bool((settings.MERCADO_PAGO_PUBLIC_KEY or "").strip())
    has_access_token = bool((settings.MERCADO_PAGO_ACCESS_TOKEN or "").strip())
    is_test_token = _mp_credencial_teste()

    checks = {
        "env_public_key": has_public_key,
        "env_access_token": has_access_token,
        "mode": "sandbox" if is_test_token else "production",
    }

    if not has_public_key or not has_access_token:
        return JsonResponse({"ok": False, "checks": checks}, status=500)

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
    me = _mp_call_with_timeout(sdk.user().get)
    checks["mp_user_status"] = me.get("status")
    checks["collector_id"] = (me.get("response") or {}).get("id")

    ok = me.get("status") == 200
    return JsonResponse({"ok": ok, "checks": checks}, status=200 if ok else 502)

@login_required
@master_member_required
def fatura_create(request):
    return render(request, 'fatura_form.html', {
        'pacientes': Paciente.objects.all().order_by('nome_completo'),
        'today': timezone.now()
    })

@login_required
@master_member_required
def fatura_store(request):
    if request.method == 'POST':
        pac_id = request.POST.get('paciente')
        if not pac_id:
            messages.error(request, "Selecione um paciente.")
            return redirect('sistema_interno:fatura_create')
            
        paciente = get_object_or_404(Paciente, id=pac_id)
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
            base = paciente.vencimento_plano if paciente.vencimento_plano and paciente.vencimento_plano > hoje else hoje
            novo_vencimento = base + timedelta(days=365)
            paciente.vencimento_plano = novo_vencimento
            paciente.save()
            Paciente.objects.filter(responsavel=paciente).update(vencimento_plano=novo_vencimento)
            
    return redirect('sistema_interno:master_dashboard')

@login_required
@recepcao_ou_master_required
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

@login_required
@master_member_required
def master_dashboard(request):
    hoje = timezone.now().date()
    doenca_filtro = request.GET.get('doenca')
    q_busca = request.GET.get('q', '')
    mes_ref = request.GET.get('mes_referencia')
    ano_ref = request.GET.get('ano_referencia', hoje.year)
    
    pacientes_lista = Paciente.objects.filter(is_titular=True)
    
    if doenca_filtro:
        pacientes_lista = pacientes_lista.filter(doencas_cronicas__icontains=doenca_filtro)
    
    if q_busca:
        pacientes_lista = pacientes_lista.filter(
            Q(nome_completo__icontains=q_busca) | Q(cpf__icontains=q_busca)
        )
    
    faturas_pago = Fatura.objects.filter(status='PAGO')
    if mes_ref:
        faturas_pago = faturas_pago.filter(data_pagamento__month=mes_ref, data_pagamento__year=ano_ref)
    else:
        faturas_pago = faturas_pago.filter(data_pagamento__month=hoje.month, data_pagamento__year=hoje.year)

    pago_total = faturas_pago.aggregate(Sum('valor'))['valor__sum'] or 0
    alertas = Paciente.objects.filter(vencimento_plano__range=[hoje, hoje + timedelta(days=30)], is_titular=True)
    leads = LeadSite.objects.filter(atendido=False).order_by('-id')
    total_pacientes = Paciente.objects.count()
    total_cronicos = Paciente.objects.filter(is_cronico=True).count()
    porcentagem_cronicos = round((total_cronicos / total_pacientes * 100), 1) if total_pacientes > 0 else 0

    return render(request, 'master_dashboard.html', {
        'pacientes_lista': pacientes_lista,
        'doenca_selecionada': doenca_filtro,
        'faturamento_total': pago_total, 
        'leads_recentes': leads, 
        'pacientes_vencendo': alertas,
        'boletos_recentes': Fatura.objects.filter(status='PAGO').order_by('-id')[:10],
        'porcentagem_cronicos': porcentagem_cronicos,
    })

@login_required
@recepcao_ou_master_required
def painel_colaborador(request):
    hoje = timezone.now().date()
    leads = LeadSite.objects.filter(atendido=False).order_by('-id')
    agendamentos_hoje = Agenda.objects.filter(data=hoje).order_by('hora')
    return render(request, 'painel_colaborador.html', {
        'leads_recentes': leads,
        'agendamentos_hoje': agendamentos_hoje
    })

@login_required
@staff_member_required
def painel_medico(request):
    if not _is_medico_user(request.user):
        messages.error(request, "Acesso restrito ao médico.")
        return _staff_home_redirect(request.user)
    espera = Agenda.objects.filter(data=timezone.now().date(), status='CHEGOU').order_by('hora')
    return render(request, 'painel_medico.html', {'pacientes_espera': espera})

@login_required
def painel_paciente(request):
    if _is_staff_user(request.user):
        return _staff_home_redirect(request.user)
    paciente = get_object_or_404(Paciente, cpf=request.user.username)
    hoje = timezone.now().date()
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

@login_required
@recepcao_ou_master_required
def baixar_lead(request, lead_id):
    lead = get_object_or_404(LeadSite, id=lead_id)
    lead.atendido = True
    lead.save()
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return redirect(referer)
    return redirect("sistema_interno:painel_colaborador")

@login_required
@csrf_exempt
def solicitar_renovacao_api(request):
    if _is_staff_user(request.user):
        return JsonResponse(
            {"success": False, "detail": "Endpoint exclusivo do paciente."},
            status=403,
        )
    try:
        paciente = Paciente.objects.get(cpf=request.user.username)
        LeadSite.objects.create(
            nome=paciente.nome_completo,
            telefone=paciente.telefone,
            interesse=f"RENOVAÇÃO DE RECEITA - ID: {paciente.id}",
            atendido=False,
        )
        return JsonResponse({"success": True})
    except Paciente.DoesNotExist:
        return JsonResponse({"success": False, "detail": "Paciente não encontrado."}, status=404)
    except Exception:
        return JsonResponse({"success": False}, status=400)

@login_required
@staff_member_required
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
    if not _pode_ver_dados_clinicos_paciente(request.user, paciente_id):
        return JsonResponse(
            {"success": False, "detail": "Acesso negado."},
            status=403,
        )
    ultima = (
        Receita.objects.filter(paciente_id=paciente_id)
        .order_by("-data_emissao")
        .first()
    )
    if ultima:
        return JsonResponse({"success": True, "conteudo": ultima.conteudo})
    return JsonResponse({"success": False})

@login_required
@staff_member_required
def api_buscar_paciente(request):
    q = request.GET.get('q', '')
    pacientes = Paciente.objects.filter(Q(nome_completo__icontains=q) | Q(cpf__icontains=q))[:10]
    results = [{'id': p.id, 'text': f"{p.nome_completo} ({p.cpf})"} for p in pacientes]
    return JsonResponse({'results': results})

@login_required
@staff_member_required
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
@staff_member_required
def prontuario_view(request, paciente_id):
    if not _is_medico_user(request.user):
        messages.error(
            request,
            "Acesso negado: apenas médicos podem acessar o prontuário.",
        )
        return redirect("sistema_interno:cliente_list")

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

@login_required
@master_member_required
def fatura_baixar(request, fatura_id):
    f = get_object_or_404(Fatura, id=fatura_id)
    f.status = "PAGO"
    f.data_pagamento = timezone.now().date()
    f.save()
    return redirect("sistema_interno:master_dashboard")


@login_required
@master_member_required
def plan_create(request):
    return redirect("sistema_interno:master_dashboard")

def cadastro_plano_completo(request, plano_nome):
    if request.method == 'POST':
        nome = request.POST.get('titular_nome') or request.POST.get('nome')
        cpf = request.POST.get('titular_cpf') or request.POST.get('cpf')
        tel = request.POST.get('titular_telefone') or request.POST.get('telefone')
        email = (request.POST.get('titular_email') or request.POST.get('email') or "").strip()
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
            if email:
                user, _ = User.objects.get_or_create(username=cpf)
                user.email = email
                user.save()
            plano = Plano.objects.filter(nome__icontains=plano_nome).first() or Plano.objects.first()
            return redirect('sistema_interno:checkout_pagamento', paciente_id=p.id, plano_id=plano.id)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'cadastro_plano.html', {'plano_selecionado': plano_nome})