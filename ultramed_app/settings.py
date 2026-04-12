import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DEBUG", "False").strip().lower() in ("1", "true", "yes", "on")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-defina-django-secret-key-no-env"
    else:
        raise ImproperlyConfigured(
            "Produção exige DJANGO_SECRET_KEY definida no ambiente (.env ou compose)."
        )

_env_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
if _env_hosts:
    ALLOWED_HOSTS = [h.strip() for h in _env_hosts.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = [
        "ultramedsaudexingu.com.br",
        "www.ultramedsaudexingu.com.br",
        "72.61.52.175",
        "localhost",
        "127.0.0.1",
    ]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core_gestao",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ultramed_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "core_gestao/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ultramed_app.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("SQL_DATABASE", "ultramed_db"),
        "USER": os.getenv("SQL_USER", "ultramed_user"),
        "PASSWORD": os.getenv("SQL_PASSWORD", ""),
        "HOST": os.getenv("SQL_HOST", "db"),
        "PORT": os.getenv("SQL_PORT", "3306"),
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Belem"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static_content")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media_content")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =================================================================
# SEGURANÇA E CSRF (HTTPS atrás do Nginx + Mercado Pago)
# =================================================================

CSRF_TRUSTED_ORIGINS = [
    "https://ultramedsaudexingu.com.br",
    "https://www.ultramedsaudexingu.com.br",
    "http://ultramedsaudexingu.com.br",
    "http://72.61.52.175",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# False: JS do checkout pode ler o cookie CSRF para o header X-CSRFToken
CSRF_COOKIE_HTTPONLY = False

CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# =================================================================
# REDIRECIONAMENTOS
# =================================================================
LOGIN_URL = "sistema_interno:login"
LOGIN_REDIRECT_URL = "sistema_interno:painel_paciente"
LOGOUT_REDIRECT_URL = "sistema_interno:login"

# =================================================================
# MERCADO PAGO (credenciais apenas via ambiente em produção)
# =================================================================
def _mp_env(key: str, default: str) -> str:
    """Docker/.env costumam definir variável vazia; tratar como 'não definida' e usar default."""
    raw = os.getenv(key)
    if raw is None:
        return default
    raw = raw.strip()
    return raw if raw else default


MERCADO_PAGO_PUBLIC_KEY = _mp_env(
    "MERCADO_PAGO_PUBLIC_KEY",
    "TEST-820749df-8dd8-471e-bf11-93e09709a0e0" if DEBUG else "",
)
MERCADO_PAGO_ACCESS_TOKEN = _mp_env(
    "MERCADO_PAGO_ACCESS_TOKEN",
    "TEST-6753419192975396-030114-c38ea8b2f4fa6e920634c1d8ee8ce124-3235550241"
    if DEBUG
    else "",
)
# Sandbox: e-mail deve ser de comprador teste (@testuser.com) criado na sua aplicação MP.
MERCADO_PAGO_TEST_PAYER_EMAIL = os.getenv("MERCADO_PAGO_TEST_PAYER_EMAIL", "").strip()
