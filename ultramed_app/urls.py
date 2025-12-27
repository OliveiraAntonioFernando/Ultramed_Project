from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def landing_page(request):
    return render(request, 'landing_page.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='home'),
    path('sistema/', include('core_gestao.urls')),
]
