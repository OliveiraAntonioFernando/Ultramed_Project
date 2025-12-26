from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Paciente, Agendamento, LeadCapture, Fatura, Plano, User

# --- AUTENTICAÇÃO ---
def login_view(request):
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

@login_required
def dashboard(request):
    if request.user.role == 'MASTER':
        return redirect('sistema_interno:painel_master')
    return redirect('sistema_interno:painel_colaborador')

# --- PAINÉIS ---
@login_required
def painel_master(request):
    agendamentos = Agendamento.objects.all().order_by('-id')[:10]
    leads = LeadCapture.objects.all().order_by('-data_criacao')[:10]
    return render(request, 'sistema_interno/painel_master.html', {
        'agendamentos': agendamentos, 'leads': leads
    })

@login_required
def painel_colaborador(request):
    pacientes = Paciente.objects.all().order_by('-id')[:10]
    return render(request, 'sistema_interno/painel_colaborador.html', {'pacientes': pacientes})

@login_required
def painel_medico(request):
    fila = Agendamento.objects.filter(status='AGUARDANDO').order_by('hora')
    return render(request, 'sistema_interno/painel_medico.html', {'fila': fila})

# --- GESTÃO DE PLANOS ---
@login_required
@login_required
def plan_create(request):
    if request.method == 'POST':
        # TRATAMENTO DO PREÇO: Se vier vazio ou inválido, vira 0.0
        raw_price = request.POST.get('price', '0')
        try:
            # Remove possíveis vírgulas e converte para float
            clean_price = float(raw_price.replace(',', '.')) if raw_price else 0.0
        except ValueError:
            clean_price = 0.0

        Plano.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            price=clean_price,  # <--- Valor garantido como numérico
            plan_type=request.POST.get('plan_type'),
            max_people=request.POST.get('max_people', 1)
        )
        return redirect('sistema_interno:plan_list')
    return render(request, 'sistema_interno/cadastro_plano.html')
@login_required
def plan_list(request):
    planos = Plano.objects.all()
    return render(request, 'sistema_interno/plan_list.html', {'planos': planos})

# --- AGENDAMENTOS (RESOLVE O ERRO AGENDAMENTO_CREATE) ---
@login_required
def agenda(request):
    if request.method == 'POST':
        nome = request.POST.get('paciente_nome')
        v_str = request.POST.get('valor', '0')
        valor_base = float(v_str) if v_str else 0.0
        
        paciente = Paciente.objects.filter(nome_completo=nome).first()
        valor_final = valor_base
        
        if paciente:
            conv = (paciente.convenio or "").upper()
            if "ESSENCIAL" in conv:
                ja_agendou = Agendamento.objects.filter(paciente_nome=nome).exists()
                valor_final = 0.00 if not ja_agendou else valor_base * 0.70
            elif "MASTER" in conv:
                valor_final = valor_base * 0.50

        Agendamento.objects.create(
            paciente_nome=nome,
            medico=request.POST.get('medico'),
            tipo=request.POST.get('tipo'),
            exame_nome=request.POST.get('exame_nome'),
            data=request.POST.get('data'),
            hora=request.POST.get('hora'),
            valor_consulta=valor_final
        )
        return JsonResponse({'success': True, 'valor_final': valor_final})
    return render(request, 'sistema_interno/agenda.html')

@login_required
def agendamento_create(request):
    """Resolve a rota agendamento/novo/ do urls.py"""
    return agenda(request)

@login_required
def agendamento_list(request):
    agendamentos = Agendamento.objects.all().order_by('-data', '-hora')
    return render(request, 'sistema_interno/agendamento_list.html', {'agendamentos': agendamentos})

# --- PACIENTES ---
@login_required
def cliente_create(request):
    if request.method == 'POST':
        Paciente.objects.create(
            nome_completo=request.POST.get('nome_completo'),
            cpf=request.POST.get('cpf'),
            telefone=request.POST.get('telefone'),
            convenio=request.POST.get('convenio', 'PARTICULAR')
        )
        return redirect('sistema_interno:cliente_list')
    return render(request, 'sistema_interno/cliente_create.html')

@login_required
def cliente_list(request):
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'sistema_interno/cliente_list.html', {'pacientes': pacientes})

# --- FINANCEIRO ---
@login_required
def fatura_list(request):
    faturas = Fatura.objects.all().order_by('-id')
    return render(request, 'sistema_interno/fatura_list.html', {'faturas': faturas})

# --- OUTROS ---
def landing_page(request):
    return render(request, 'landing_page.html')

@csrf_exempt
def api_lead_capture(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        LeadCapture.objects.create(nome=data.get('nome'), telefone=data.get('telefone'), interesse=data.get('interesse'))
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})
