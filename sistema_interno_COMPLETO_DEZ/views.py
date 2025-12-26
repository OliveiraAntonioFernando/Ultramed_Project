from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# IMPORTS DE BANCO DE DADOS CORRIGIDOS
from django.db import connection             # Para SQL Puro
from django.db.models import Q                # Para buscas complexas
from .models import Paciente, Agendamento, LeadCapture, Fatura, Plano, User

# --- AUTENTICAÇÃO ---
def login_view(request):
    if request.user.is_authenticated: return redirect('sistema_interno:dashboard')
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            return redirect('sistema_interno:dashboard')
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, 'sistema_interno/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing_page')

@login_required(login_url='sistema_interno:login')
def dashboard(request):
    role = getattr(request.user, 'role', 'COLABORADOR')
    destinos = {'MASTER': 'sistema_interno:painel_master', 'MEDICO': 'sistema_interno:painel_medico'}
    return redirect(destinos.get(role, 'sistema_interno:painel_colaborador'))

# --- PAINÉIS ---
@login_required(login_url='sistema_interno:login')
def painel_colaborador(request):
    pacientes = Paciente.objects.all().order_by('-id')[:10]
    return render(request, 'sistema_interno/painel_colaborador.html', {'pacientes': pacientes, 'perfil': 'EQUIPE'})

@login_required(login_url='sistema_interno:login')
def painel_master(request): return painel_colaborador(request)
@login_required(login_url='sistema_interno:login')
def painel_medico(request): return painel_colaborador(request)
@login_required(login_url='sistema_interno:login')
def painel_cliente(request): return painel_colaborador(request)

# --- VENDA DE PLANO (SQL PURO COM SEXO E DATA DOS DEPENDENTES) ---
@login_required(login_url='sistema_interno:login')
def plan_create(request):
    if request.method == 'POST':
        # Captura Titular
        titular = request.POST.get('titular_nome')
        cpf = request.POST.get('titular_cpf')
        sexo = request.POST.get('titular_sexo', 'M')
        rg = request.POST.get('titular_rg', 'Não informado')
        nascimento = request.POST.get('titular_nascimento') or "2000-01-01"
        tipo = request.POST.get('plano_tipo', 'ESSENCIAL')
        telefone = request.POST.get('titular_telefone', '')
        cidade = request.POST.get('titular_cidade', 'São Félix do Xingu')
        bairro = request.POST.get('titular_bairro', 'Centro')
        rua = request.POST.get('titular_endereco', '')

        # Captura Listas de Dependentes
        dep_nomes = request.POST.getlist('dep_nome[]')
        dep_cpfs = request.POST.getlist('dep_cpf[]')
        dep_sexos = request.POST.getlist('dep_sexo[]')
        dep_nascimentos = request.POST.getlist('dep_nascimento[]')

        if titular and cpf:
            try:
                # 1. Grava o Plano (ORM)
                Plano.objects.update_or_create(
                    name=titular,
                    defaults={'plan_type': tipo.upper()}
                )

                # 2. Grava Titular via SQL PURO
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM sistema_interno_paciente WHERE cpf = %s", [cpf])
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE sistema_interno_paciente
                            SET nome_completo=%s, telefone=%s, convenio=%s, data_nascimento=%s, endereco=%s, cidade=%s, bairro=%s, sexo=%s
                            WHERE cpf=%s
                        """, [titular, telefone, f"PLANO {tipo.upper()}", nascimento, rua, cidade, bairro, sexo, cpf])
                    else:
                        cursor.execute("""
                            INSERT INTO sistema_interno_paciente
                            (nome_completo, cpf, telefone, convenio, data_nascimento, endereco, cidade, bairro, data_cadastro, sexo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                        """, [titular, cpf, telefone, f"PLANO {tipo.upper()}", nascimento, rua, cidade, bairro, sexo])

                # 3. Grava Dependentes via SQL PURO
                for n, c, s, dn in zip(dep_nomes, dep_cpfs, dep_sexos, dep_nascimentos):
                    if n and c:
                        data_dep = dn if dn else "2000-01-01"
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT id FROM sistema_interno_paciente WHERE cpf = %s", [c])
                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO sistema_interno_paciente
                                    (nome_completo, cpf, convenio, data_nascimento, endereco, cidade, bairro, data_cadastro, sexo)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                                """, [n, c, f"DEP: {titular}", data_dep, rua, cidade, bairro, s])

                messages.success(request, "Venda Gravada com Sucesso!")
                return redirect('sistema_interno:plan_create')
            except Exception as e:
                print(f">>> ERRO AO GRAVAR: {e}")
                messages.error(request, f"Erro: {e}")
        else:
            messages.error(request, "Nome e CPF são obrigatórios!")

    return render(request, 'sistema_interno/cadastro_plano.html')

# --- ROTAS DE APOIO ---
@login_required(login_url='sistema_interno:login')
def api_buscar_paciente(request):
    term = request.GET.get('term', '')
    pacs = Paciente.objects.filter(Q(nome_completo__icontains=term) | Q(cpf__icontains=term))[:10]
    return JsonResponse({'success': True, 'results': [{'nome': p.nome_completo, 'cpf': p.cpf} for p in pacs]})

def agenda(request): return render(request, 'sistema_interno/agenda.html')
def agendamento_list(request): return render(request, 'sistema_interno/agendamento_list.html', {'agendamentos': Agendamento.objects.all()})
def agendamento_create(request): return agenda(request)
def cliente_list(request): return render(request, 'sistema_interno/cliente_list.html', {'pacientes': Paciente.objects.all()})
def cliente_create(request): return redirect('sistema_interno:dashboard')
def plan_list(request): return render(request, 'sistema_interno/plan_list.html', {'planos': Plano.objects.all()})
def fatura_list(request): return render(request, 'sistema_interno/fatura_list.html')
def landing_page(request): return render(request, 'sistema_interno/landing_page.html')

@csrf_exempt
def api_lead_capture(request):
    return JsonResponse({'success': True})
