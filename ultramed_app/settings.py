import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Carrega as variáveis do arquivo .env (Obrigatório para ler suas chaves)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Pega do .env, se não existir usa a padrão (Seguro para dev)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'f!#o4kk(_+=@oiwl1e-gr#en#pg8rmizv3$#+w-^u69y@m0g=k')

# Mantemos True para você ver os erros enquanto desenvolve
DEBUG = True 

ALLOWED_HOSTS = [
    'ultramedsaudexingu.com.br', 
    'www.ultramedsaudexingu.com.br', 
    '72.61.52.175', 
    'localhost', 
    '127.0.0.1'
]

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
# SEGURANÇA E CSRF (AJUSTADO PARA FUNCIONAR COM MERCADO PAGO)
# =================================================================

# Removi o "*" (wildcard) que o Django não aceita bem
CSRF_TRUSTED_ORIGINS = [
    'https://ultramedsaudexingu.com.br', 
    'https://www.ultramedsaudexingu.com.br',
    'http://ultramedsaudexingu.com.br',
    'http://72.61.52.175',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

CSRF_COOKIE_SECURE = False  
SESSION_COOKIE_SECURE = False 

# MUDANÇA VITAL: False permite que o JavaScript do Mercado Pago envie o pagamento
CSRF_COOKIE_HTTPONLY = False 

CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

# =================================================================
# REDIRECIONAMENTOS
# =================================================================
LOGIN_URL = 'sistema_interno:login' 
LOGIN_REDIRECT_URL = 'sistema_interno:painel_paciente'
LOGOUT_REDIRECT_URL = 'sistema_interno:login'

# =================================================================
# MERCADO PAGO - CREDENCIAIS (SINCRONIZADO COM .ENV)
# =================================================================
MERCADO_PAGO_PUBLIC_KEY = os.getenv('MERCADO_PAGO_PUBLIC_KEY', 'TEST-820749df-8dd8-471e-bf11-93e09709a0e0')
MERCADO_PAGO_ACCESS_TOKEN = os.getenv('MERCADO_PAGO_ACCESS_TOKEN', 'TEST-6753419192975396-030114-c38ea8b2f4fa6e920634c1d8ee8ce124-3235550241')