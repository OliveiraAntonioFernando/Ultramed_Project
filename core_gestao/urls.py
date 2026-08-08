from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'sistema_interno'

urlpatterns = [
    # Acesso e Painéis
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ajuda/', views.ajuda_equipe, name='ajuda_equipe'),
    
    # Painéis
    path('paciente/painel/', views.painel_paciente, name='painel_paciente'),
    path('colaborador/painel/', views.painel_colaborador, name='painel_colaborador'),
    path('medico/painel/', views.painel_medico, name='painel_medico'),
    path('medico/chamar/<int:paciente_id>/', views.chamar_paciente_tv, name='chamar_paciente_tv'),
    path('master/dashboard/', views.master_dashboard, name='master_dashboard'),
    path('master/licenca/', views.licenca_rinan, name='licenca_rinan'),
    path('master/licenca/pagar/<int:fatura_id>/', views.licenca_pagar, name='licenca_pagar'),
    path('master/licenca/retorno/', views.licenca_retorno, name='licenca_retorno'),
    path('master/licenca/baixar/<int:fatura_id>/', views.licenca_baixar, name='licenca_baixar'),
    path('tv-espera/', views.tv_espera, name='tv_espera'),

    # Gestão de Pacientes
    path('paciente/novo/', views.cliente_create, name='cliente_create'),
    path('paciente/editar/<int:paciente_id>/', views.cliente_edit, name='cliente_edit'),
    path('paciente/lista/', views.cliente_list, name='cliente_list'),
    path('paciente/prontuario/<int:paciente_id>/', views.prontuario_view, name='prontuario_view'),
    path('paciente/salvar-doencas/<int:paciente_id>/', views.salvar_doencas_cronicas, name='salvar_doencas'),
    path('paciente/upload-exame/', views.upload_exame, name='upload_exame'),
    
    # Contratação e Planos
    path('contratar-plano/<str:plano_nome>/', views.cadastro_plano_completo, name='cadastro_plano'),
    path('plano/venda/', views.plan_create, name='plan_create'),

    # Agenda
    path('agenda/', views.agenda_view, name='agenda_view'),
    
    # Gestão de Leads
    path('leads/baixar/<int:lead_id>/', views.baixar_lead, name='baixar_lead'),

    # Financeiro e Mercado Pago
    path('financeiro/fatura/nova/', views.fatura_create, name='fatura_create'),
    path('financeiro/fatura/salvar/', views.fatura_store, name='fatura_store'),
    path('financeiro/fatura/baixar/<int:fatura_id>/', views.fatura_baixar, name='fatura_baixar'),
    path('financeiro/comprovante/<int:fatura_id>/', views.comprovante_fatura, name='comprovante_fatura'),
    path('planos/a-vencer/', views.planos_a_vencer, name='planos_a_vencer'),
    path('carteirinha/v/<str:token>/', views.validar_carteirinha, name='validar_carteirinha'),
    path('carteirinha/ler/', views.ler_carteirinha, name='ler_carteirinha'),
    
    # Checkout
    path('checkout/pagamento/<int:paciente_id>/<int:plano_id>/', views.checkout_pagamento, name='checkout_pagamento'),
    
    # APIs (V1)
    path('api/v1/processar-pagamento/', views.processar_pagamento_brick, name='processar_pagamento_brick'),
    path('api/v1/status-pagamento/', views.consultar_status_pagamento, name='status_pagamento'),
    path('api/v1/mp/webhook/', views.mercadopago_webhook, name='mp_webhook'),
    path('api/v1/mp/webhook-rinan/', views.mercadopago_webhook_rinan, name='mp_webhook_rinan'),
    path('api/v1/mp/health/', views.mp_healthcheck, name='mp_healthcheck'),
    path('api/v1/solicitar-renovacao/', views.solicitar_renovacao_api, name='solicitar_renovacao_api'),
    path('api/v1/ultima-receita/<int:paciente_id>/', views.api_ultima_receita, name='api_ultima_receita'),
    path('api/v1/lead-capture/', views.api_lead_capture, name='lead_capture'),
    path('api/v1/buscar-paciente/', views.api_buscar_paciente, name='api_buscar_paciente'),
    path('api/v1/detalhes-paciente/<int:paciente_id>/', views.api_detalhes_paciente, name='api_detalhes_paciente'),
    path('api/v1/tv-chamada/', views.api_tv_chamada, name='api_tv_chamada'),
    path('api/v1/tv-stream/', views.api_tv_stream, name='api_tv_stream'),
    path('arquivo/exame/<int:exame_id>/', views.download_exame_arquivo, name='download_exame_arquivo'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)