#!/usr/bin/env bash
# Asistente de primer arranque (macOS / Linux): pide la configuración y crea el archivo .env.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  read -r -p "Ya existe un archivo .env. ¿Sobrescribirlo? [s/N] " ans
  [[ "$ans" =~ ^[sSyY]$ ]] || { echo "Sin cambios."; exit 0; }
fi

echo "== Configuración de Evaluación Inmobiliaria =="
echo "(Enter acepta el valor entre corchetes)"
echo

read -r -p "Nombre de la base de datos [evaluacion_inmobiliaria]: " db
db=${db:-evaluacion_inmobiliaria}
read -r -p "Usuario de la base de datos [evaluacion]: " user
user=${user:-evaluacion}

while true; do
  read -r -s -p "Contraseña de la base de datos (Enter = generar una segura): " pass; echo
  if [ -z "$pass" ]; then
    pass=$(openssl rand -hex 16)
    echo "Contraseña generada y guardada en .env"
    break
  fi
  if [[ "$pass" =~ ^[A-Za-z0-9_.-]+$ ]]; then break; fi
  echo "Usa solo letras, números, '_', '.' o '-'."
done

read -r -p "Puerto de la aplicación [8000]: " port
port=${port:-8000}
read -r -p "¿Crear la plantilla demo en el primer arranque? [S/n] " demo
if [[ "$demo" =~ ^[nN]$ ]]; then seed=false; else seed=true; fi

umask 077
cat > .env <<EOF
POSTGRES_USER=$user
POSTGRES_DB=$db
POSTGRES_PASSWORD=$pass
APP_PORT=$port
SEED_ON_STARTUP=$seed
EOF
echo
echo "Archivo .env creado."

read -r -p "¿Levantar la aplicación ahora con Docker? [S/n] " go
if [[ ! "$go" =~ ^[nN]$ ]]; then
  docker compose up --build -d
  echo "Listo: http://localhost:$port"
else
  echo "Cuando quieras: docker compose up --build -d"
fi
