from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

from core_gestao.views import ajuda_paciente, privacidade, termos_uso


def landing_page(request):
    return render(request, 'landing_page.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='home'),
    path('ajuda/', ajuda_paciente, name='ajuda_paciente'),
    path('termos/', termos_uso, name='termos'),
    path('privacidade/', privacidade, name='privacidade'),
    # CENTRALIZAÇÃO: Tudo que vem do app core_gestao agora exige o prefixo sistema/
    path('sistema/', include('core_gestao.urls')), 
]