#!/bin/bash

echo "🚀 Iniciando Sistema de Detecção de Incêndios..."

# Inicia Docker
sudo docker compose up -d

# Ativa venv e roda detecção
source .venv/bin/activate
python detect.py &

# Aguarda e abre Grafana
sleep 5
xdg-open http://localhost:3000
