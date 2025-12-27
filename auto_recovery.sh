#!/bin/bash
# Caminho para a pasta do projeto
cd /root/ultramed

# 1. Backup do Banco de Dados (Segurança extra)
# O arquivo será gerado com data para você ter vários pontos de retorno
docker exec ultramed-db mysqldump -uultramed_user -pV#aldeca0lock70 ultramed_db > db_backup_$(date +%Y%m%d_%H%M).sql

# 2. Sincronização com o Git (Ponto de Recuperação)
git add .
git commit -m "Ponto de Recuperação Automático: $(date +'%Y-%m-%d %H:%M:%S')"
git push origin main
