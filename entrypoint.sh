#!/bin/sh

# entrypoint.sh

echo "⏳ Aguardando o banco de dados estar pronto..."
sleep 10

echo "🚀 Aplicando as migrações do banco de dados..."
python manage.py migrate

echo "🎨 Coletando arquivos estáticos..."
python manage.py collectstatic --clear

# --- CRIAÇÃO DO SUPERUSUÁRIO AUTOMÁTICA ---
echo "🔐 Verificando e criando superusuário..."
python manage.py create_initial_superuser

# -----------------------------------------

echo "🚀 Iniciando o servidor..."
exec "$@"