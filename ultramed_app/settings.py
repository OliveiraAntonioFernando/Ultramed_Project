import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'f!#o4kk(_+=@oiwl1e-gr#en#pg8rmizv3$#+w-^u69y@m0g=k')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Ajuste de domínios permitidos
ALLOWED_HOSTS = ['ultramedsaudexingu.com.br', 'www.ultramedsaudexingu.com.br', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core_gestao',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ultramed_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'core_gestao/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ultramed_app.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('SQL_DATABASE', 'ultramed_db'),
        'USER': os.getenv('SQL_USER', 'ultramed_user'),
        'PASSWORD': os.getenv('SQL_PASSWORD', 'V#aldeca0lock70'),
        'HOST': os.getenv('SQL_HOST', 'db'),
        'PORT': os.getenv('SQL_PORT', '3306'),
    }
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Belem'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_content')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =================================================================
# SEGURANÇA, HTTPS E CORS (CORREÇÃO DEFINITIVA DO ERRO DE CONEXÃO)
# =================================================================
CSRF_TRUSTED_ORIGINS = [
    'https://ultramedsaudexingu.com.br', 
    'https://www.ultramedsaudexingu.com.br'
]

# Liberação para o JavaScript do navegador não bloquear o POST
CORS_ALLOW_ALL_ORIGINS = True 
CORS_ALLOW_CREDENTIALS = True

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Configurações de redirecionamento de acesso
LOGIN_URL = '/sistema/login/'
LOGIN_REDIRECT_URL = '/sistema/painel/'
LOGOUT_REDIRECT_URL = '/sistema/login/'

# =================================================================
# CONFIGURAÇÕES DO MERCADO PAGO
# =================================================================
MERCADO_PAGO_PUBLIC_KEY = os.getenv('MP_PUBLIC_KEY', 'AGUARDANDO_CHAVE_DO_CLIENTE')
MERCADO_PAGO_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', 'AGUARDANDO_CHAVE_DO_CLIENTE')