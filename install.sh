#!/usr/bin/env bash
# Script de instalación reproducible para el sistema Inmobiliario (Odoo 19).
# Asume que tienes ya: PostgreSQL, Python 3.12+, Odoo 19 clonado en ~/Documentos/odoo19.
#
# Uso:
#   bash install.sh [DB_NAME]
# Default DB: tesis_odoo19

set -euo pipefail

DB_NAME="${1:-tesis_odoo19}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv19"
ODOO_BIN="${HOME}/Documentos/odoo19/odoo-bin"
CONF="${PROJECT_DIR}/odoo19.conf"

cyan()  { echo -e "\033[36m$*\033[0m"; }
green() { echo -e "\033[32m$*\033[0m"; }
red()   { echo -e "\033[31m$*\033[0m"; }

# ── 1. Verificar prerequisitos ────────────────────────────────────────────────
cyan "[1/5] Verificando prerequisitos..."
command -v python3 >/dev/null   || { red "Falta python3"; exit 1; }
command -v psql >/dev/null      || { red "Falta postgresql-client"; exit 1; }
[[ -x "${ODOO_BIN}" ]]          || { red "Falta odoo-bin en ${ODOO_BIN}"; exit 1; }
[[ -f "${CONF}" ]]              || { red "Falta ${CONF}"; exit 1; }

# ── 2. Crear / activar venv ──────────────────────────────────────────────────
cyan "[2/5] Configurando entorno virtual..."
if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
    green "  ✓ venv creado"
fi
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

# ── 3. Instalar dependencias Python ──────────────────────────────────────────
cyan "[3/5] Instalando dependencias Python..."
pip install --quiet --upgrade pip
pip install --quiet \
    qrcode[pil] \
    google-generativeai \
    openai \
    openpyxl \
    psycopg2-binary \
    requests
# Requirements del propio Odoo
if [[ -f "${HOME}/Documentos/odoo19/requirements.txt" ]]; then
    pip install --quiet -r "${HOME}/Documentos/odoo19/requirements.txt"
fi
green "  ✓ dependencias instaladas"

# ── 4. Crear DB si no existe ─────────────────────────────────────────────────
cyan "[4/5] Verificando base de datos '${DB_NAME}'..."
if psql -lqt | cut -d '|' -f 1 | grep -qw "${DB_NAME}"; then
    green "  ✓ DB '${DB_NAME}' ya existe"
else
    createdb "${DB_NAME}"
    green "  ✓ DB '${DB_NAME}' creada"
fi

# ── 5. Instalar todos los módulos custom ─────────────────────────────────────
cyan "[5/5] Instalando módulos custom (esto puede tardar 1-2 minutos)..."
python "${ODOO_BIN}" -c "${CONF}" -d "${DB_NAME}" \
    -i estate_management,estate_crm,estate_reports,estate_ai_agent,estate_document,estate_calendar,estate_social,estate_portal,estate_wordpress \
    --stop-after-init \
    --without-demo=all

green ""
green "════════════════════════════════════════════════════════════════"
green "  ✓ Instalación completada correctamente"
green "════════════════════════════════════════════════════════════════"
green ""
green "Para arrancar el servidor:"
green "  source ${VENV_DIR}/bin/activate"
green "  python ${ODOO_BIN} -c ${CONF}"
green ""
green "Acceder en: http://localhost:8070"
