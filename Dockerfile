# Imagem base
FROM python:3.12-slim

# Define variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala as dependências, incluindo as bibliotecas C necessárias para mysqlclient
COPY requirements.txt /app/
# ... (Linha 12: COPY requirements.txt /app/)
RUN apt update && \
    apt install -y default-libmysqlclient-dev pkg-config gcc libmariadb3 && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apt purge -y default-libmysqlclient-dev pkg-config gcc && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copia o código do projeto para o container
COPY . /app/

# Expõe a porta que o Gunicorn vai usar
EXPOSE 8000
