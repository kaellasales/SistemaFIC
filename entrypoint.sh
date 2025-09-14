#!/bin/sh

# entrypoint.sh

echo "🚀 Aplicando as migrações do banco de dados..."
python manage.py migrate --noinput

echo "🎨 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

# --- CRIAÇÃO DO SUPERUSUÁRIO AUTOMÁTICA ---
echo "🔐 Verificando e criando superusuário..."
python manage.py create_initial_superuser

# -----------------------------------------

echo "🚀 Iniciando o servidor..."
exec "$@"