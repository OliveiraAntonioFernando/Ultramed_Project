from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from .models import Paciente, Fatura, Prontuario, LeadSite, Plano, Exame

# LOGIN MULTIPERFIL
def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            if user.groups.filter(name='Medico').exists(): return redirect('sistema_interno:painel_medico')
            if user.groups.filter(name='Recepcao').exists(): return redirect('sistema_interno:painel_colaborador')
            if user.is_superuser: return redirect('sistema_interno:master_dashboard')
            return redirect('sistema_interno:painel_paciente')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('sistema_interno:login')

# CAPTURA DE LEAD (LANDING PAGE)
@csrf_exempt
def api_lead_capture(request):
    if request.method == 'POST':
        nome, tel = request.POST.get('nome'), request.POST.get('telefone')
        if nome and tel:
            LeadSite.objects.create(nome=nome, telefone=tel, interesse=request.POST.get('interesse', 'Geral'))
            return JsonResponse({'status': 'sucesso'})
    return JsonResponse({'status': 'erro'}, status=400)

# DASHBOARD MASTER
@login_required
def master_dashboard(request):
    if not request.user.is_superuser: return redirect('sistema_interno:login')
    pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    leads = LeadSite.objects.filter(atendido=False).order_by('-data_solicitacao')
    return render(request, 'master_dashboard.html', {'faturamento_total': pago, 'leads_recentes': leads})

# PAINEL EQUIPE (RECEPÇÃO) - ACESSO USUÁRIO 'recepcao'
@login_required
def painel_colaborador(request):
    return render(request, 'painel_colaborador.html')

# PAINEL MÉDICO
@login_required
def painel_medico(request):
    return render(request, 'painel_medico.html', {'pacientes': Paciente.objects.all()})

@login_required
def prontuario_view(request, paciente_id):
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

# PAINEL PACIENTE (BLINDADO)
@login_required
def painel_paciente(request):
    paciente = Paciente.objects.filter(cpf=request.user.username).first()
    if not paciente: return redirect('sistema_interno:master_dashboard')
    return render(request, 'painel_paciente.html', {'paciente': paciente})

# OPERACIONAL
@login_required
def cliente_list(request): return render(request, 'cliente_list.html', {'pacientes': Paciente.objects.all()})
@login_required
def fatura_create(request): return render(request, 'fatura_form.html', {'pacientes': Paciente.objects.all()})
def cliente_create(request): return redirect('sistema_interno:cliente_list')
def fatura_baixar(request, fatura_id): return redirect('sistema_interno:master_dashboard')
def plan_create(request): return redirect('sistema_interno:master_dashboard')
def agenda_view(request): return render(request, 'agenda.html')
def api_buscar_paciente(request): return JsonResponse({'results': []})
