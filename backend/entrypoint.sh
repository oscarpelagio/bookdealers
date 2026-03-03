#!/bin/sh

# Salir inmediatamente si hay un error
set -e

#  Correr migraciones en el futuro.

echo "Iniciando servidor Uvicorn..."

# Lanza la app en el puerto 8000 y permite recarga en caliente (reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
