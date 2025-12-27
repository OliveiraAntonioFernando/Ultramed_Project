FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instala dependências de sistema e mantém as libs de execução do MariaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    libmariadb3 \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Limpa apenas ferramentas de compilação, mantendo as bibliotecas compartilhadas
RUN apt-get purge -y pkg-config gcc && apt-get autoremove -y

COPY . .

EXPOSE 8000
