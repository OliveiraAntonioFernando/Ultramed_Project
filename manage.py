# NOVO CÓDIGO FINAL E DEFINITIVO PARA manage.py
#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""
import os
import sys

# [!!! INSERÇÃO CRÍTICA AQUI !!!]
# Garante que o diretório atual do projeto (/app) esteja no caminho de busca do Python.
if '/app' not in sys.path:
    sys.path.append('/app')
# [!!! FIM DA INSERÇÃO CRÍTICA !!!]

def main():
    """Run administrative tasks."""
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ultramed_app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
