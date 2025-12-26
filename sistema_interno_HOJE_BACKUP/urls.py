from django.urls import path
from . import views

app_name = 'sistema_interno'

urlpatterns = [
    # Login e Logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Painéis de Controlo
    path('painel-master/', views.painel_master, name='painel_master'),
    path('painel-colaborador/', views.painel_colaborador, name='painel_colaborador'),
    path('painel-medico/', views.painel_medico, name='painel_medico'),
    path('painel-cliente/', views.painel_cliente, name='painel_cliente'),

    # Gestão de Pacientes (Clientes)
    path('pacientes/', views.cliente_list, name='cliente_list'),
    path('pacientes/novo/', views.cliente_create, name='cliente_create'),
    path('pacientes/<int:pk>/', views.cliente_detail, name='cliente_detail'),

    # Agenda
    path('agenda/', views.agenda, name='agenda'),

    # Financeiro
    path('faturas/', views.fatura_list, name='fatura_list'),
    path('faturas/<int:pk>/', views.fatura_detail, name='fatura_detail'),
    path('faturas/gerar/', views.gerar_fatura, name='gerar_fatura'),

    # APIs (Essencial para a busca e captura de leads)
    path('api/buscar-paciente/', views.api_buscar_paciente, name='api_buscar_paciente'),
    path('api/lead-capture/', views.api_lead_capture, name='api_lead_capture'),
]
