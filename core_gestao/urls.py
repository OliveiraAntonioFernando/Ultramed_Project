from django.urls import path
from . import views

app_name = 'sistema_interno'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('painel/', views.painel_colaborador, name='painel_colaborador'),
    path('paciente/novo/', views.cliente_create, name='cliente_create'),
    path('agenda/', views.agenda_view, name='agenda'),
    path('plano/venda/', views.plan_create, name='plan_create'),
    path('api/lead-capture/', views.api_lead_capture, name='lead_capture'),
    path('api/buscar-paciente/', views.api_buscar_paciente, name='api_buscar_paciente'),
]
