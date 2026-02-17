from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'sistema_interno'

urlpatterns = [
    # Acesso e Painéis
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('meu-painel/', views.painel_paciente, name='painel_paciente'),
    path('painel/', views.painel_colaborador, name='painel_colaborador'),
    path('master-control/', views.master_dashboard, name='master_dashboard'),
    path('medico/', views.painel_medico, name='painel_medico'),

    # Gestão de Pacientes
    path('paciente/novo/', views.cliente_create, name='cliente_create'),
    path('pacientes/lista/', views.cliente_list, name='cliente_list'),
    path('prontuario/<int:paciente_id>/', views.prontuario_view, name='prontuario_view'),
    path('paciente/salvar-doencas/<int:paciente_id>/', views.salvar_doencas_cronicas, name='salvar_doencas'),
    path('paciente/upload-exame/', views.upload_exame, name='upload_exame'),
    
    # ROTA QUE ESTÁ CAUSANDO O ERRO (Garantir o nome 'cadastro_plano')
    path('contratar-plano/<str:plano_nome>/', views.cadastro_plano_completo, name='cadastro_plano'),

    # Agenda e Planos
    path('agenda/', views.agenda_view, name='agenda_view'),
    path('plano/venda/', views.plan_create, name='plan_create'),

    # Financeiro e Mercado Pago
    path('financeiro/novo-pagamento/', views.fatura_create, name='fatura_create'),
    path('financeiro/salvar/', views.fatura_store, name='fatura_store'),
    path('financeiro/baixar/<int:fatura_id>/', views.fatura_baixar, name='fatura_baixar'),
    
    # Fluxo de Pagamento Online
    path('pagamento/<int:paciente_id>/<int:plano_id>/', views.checkout_pagamento, name='checkout_pagamento'),
    path('api/v1/mp/webhook/', views.mercadopago_webhook, name='mp_webhook'),

    # APIs
    path('api/lead-capture/', views.api_lead_capture, name='lead_capture'),
    path('api/buscar-paciente/', views.api_buscar_paciente, name='api_buscar_paciente'),
    path('api/detalhes-paciente/<int:paciente_id>/', views.api_detalhes_paciente, name='api_detalhes_paciente'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)