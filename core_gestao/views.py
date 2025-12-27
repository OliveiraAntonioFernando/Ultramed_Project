from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Paciente, Plano, Fatura, Exame, Prontuario, LeadSite

def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            if user.is_superuser or user.is_staff:
                return redirect('sistema_interno:master_dashboard')
            return redirect('sistema_interno:painel_paciente')
        messages.error(request, "CPF ou Senha inválidos.")
    return render(request, 'login.html')

@login_required
def painel_paciente(request):
    paciente = get_object_or_404(Paciente, cpf=request.user.username)
    faturas = Fatura.objects.filter(paciente=paciente).order_by('-data_vencimento')
    exames = Exame.objects.filter(paciente=paciente).order_by('-data_solicitacao')
    return render(request, 'painel_paciente.html', {
        'paciente': paciente, 'faturas': faturas, 'exames': exames
    })

@login_required
def master_dashboard(request):
    if not (request.user.is_superuser or request.user.is_staff): return redirect('sistema_interno:login')
    pago = Fatura.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or 0
    atrasado = Fatura.objects.filter(status='ATRASADO').aggregate(Sum('valor'))['valor__sum'] or 0
    pendente = Fatura.objects.filter(status='PENDENTE').aggregate(Sum('valor'))['valor__sum'] or 0
    context = {
        'faturamento_total': pago, 'inadimplencia': atrasado, 'pendente_receber': pendente,
        'taxa_adimplencia': round((float(pago)/(float(pago)+float(atrasado)+float(pendente))*100),1) if (pago+atrasado+pendente)>0 else 0,
        'faturas_abertas': Fatura.objects.filter(status__in=['PENDENTE', 'ATRASADO']).order_by('data_vencimento'),
        'boletos_recentes': Fatura.objects.filter(status='PENDENTE').order_by('-data_vencimento')[:10],
    }
    return render(request, 'master_dashboard.html', context)

@login_required
def fatura_create(request):
    if request.method == 'POST':
        Fatura.objects.create(
            paciente_id=request.POST.get('paciente'), valor=request.POST.get('valor'),
            data_vencimento=request.POST.get('vencimento'), linha_digitavel=request.POST.get('linha_digitavel'),
            link_boleto=request.POST.get('link_boleto'), status='PENDENTE'
        )
        return redirect('sistema_interno:master_dashboard')
    return render(request, 'fatura_form.html', {'pacientes': Paciente.objects.all()})

@login_required
def logout_view(request): logout(request); return redirect('sistema_interno:login')
