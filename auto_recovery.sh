#!/bin/bash
set -euo pipefail

cd /root/ultramed

if [[ ! -f .env ]]; then
    echo "Erro: .env não encontrado em /root/ultramed" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${SQL_USER:?SQL_USER não definido no .env}"
: "${SQL_PASSWORD:?SQL_PASSWORD não definido no .env}"
: "${SQL_DATABASE:?SQL_DATABASE não definido no .env}"

# 1. Backup do Banco de Dados (credenciais apenas via .env — nunca hardcode)
docker exec ultramed-db mysqldump \
    -u"${SQL_USER}" \
    -p"${SQL_PASSWORD}" \
    "${SQL_DATABASE}" > "db_backup_$(date +%Y%m%d_%H%M).sql"

# 2. Sincronização com o Git (Ponto de Recuperação)
git add .
git commit -m "Ponto de Recuperação Automático: $(date +'%Y-%m-%d %H:%M:%S')" || true
git push origin main
