#!/bin/bash
# Script para iniciar o Redis

# Verifica se o Redis está instalado
if ! command -v redis-server &> /dev/null; then
    echo "Redis não está instalado. Por favor, instale o Redis:"
    echo "  - Ubuntu/Debian: sudo apt-get install redis-server"
    echo "  - macOS: brew install redis"
    exit 1
fi

# Verifica se o Redis já está rodando
if redis-cli ping &> /dev/null; then
    echo "Redis já está rodando."
else
    echo "Iniciando Redis..."
    redis-server --daemonize yes
    echo "Redis iniciado com sucesso."
fi

# Verifica se o Redis está respondendo
if redis-cli ping | grep -q "PONG"; then
    echo "Redis está funcionando corretamente (PONG)."
else
    echo "Erro: Redis não está respondendo."
    exit 1
fi
