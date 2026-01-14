from django.urls import path
from . import views

app_name = 'sistema_interno'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('meu-painel/', views.painel_paciente, name='painel_paciente'),
    path('painel/', views.painel_colaborador, name='painel_colaborador'),
    path('financeiro/novo-pagamento/', views.fatura_create, name='fatura_create'),
    path('financeiro/salvar/', views.fatura_store, name='fatura_store'), # Adicionada para o form de pagamento funcionar
    path('master-control/', views.master_dashboard, name='master_dashboard'),
    path('financeiro/baixar/<int:fatura_id>/', views.fatura_baixar, name='fatura_baixar'),
    path('paciente/novo/', views.cliente_create, name='cliente_create'),
    path('pacientes/lista/', views.cliente_list, name='cliente_list'),
    path('medico/', views.painel_medico, name='painel_medico'),
    path('prontuario/<int:paciente_id>/', views.prontuario_view, name='prontuario_view'),
    path('plano/venda/', views.plan_create, name='plan_create'),
    
    # AJUSTADO: Agora o nome coincide com o que o botão no Master Dashboard procura
    path('agenda/', views.agenda_view, name='agenda_view'),
    
    path('api/lead-capture/', views.api_lead_capture, name='lead_capture'),
    path('api/buscar-paciente/', views.api_buscar_paciente, name='api_buscar_paciente'),
    path('api/detalhes-paciente/<int:paciente_id>/', views.api_detalhes_paciente, name='api_detalhes_paciente'),	
]
