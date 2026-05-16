#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  setup-vps.sh — Inicialización de VPS Hostinger para Inmobi
#  Ubuntu 24.04 · Ejecutar como root: bash setup-vps.sh
# ═══════════════════════════════════════════════════════════════
set -e

ODOO_DOMAIN="erp.tudominio.com"     # ← CAMBIA
N8N_DOMAIN="n8n.tudominio.com"      # ← CAMBIA
EMAIL="tucorreo@gmail.com"          # ← CAMBIA (para certbot)
INMOBI_DIR="/opt/inmobi"

echo "==> [1/7] Actualizando sistema..."
apt-get update && apt-get upgrade -y

echo "==> [2/7] Instalando Docker + Docker Compose..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "==> [3/7] Creando estructura de directorios..."
mkdir -p ${INMOBI_DIR}/{addons,data/postgres,data/odoo,data/n8n,logs/odoo}
chown -R 101:101 ${INMOBI_DIR}/data/odoo   # usuario odoo en el container

echo "==> [4/7] Configurando firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> [5/7] Clonando repositorio de addons (ajusta la URL)..."
# git clone git@github.com:tuusuario/inmobi-addons.git ${INMOBI_DIR}/addons
echo "    ⚠  Pendiente: clona o sube tus addons a ${INMOBI_DIR}/addons"

echo "==> [6/7] Copiando archivos de deploy..."
cp -r $(dirname "$0")/* ${INMOBI_DIR}/
cd ${INMOBI_DIR}
cp .env.example .env
echo "    ⚠  EDITA ${INMOBI_DIR}/.env con tus claves antes de continuar"

echo "==> [7/7] Levantando servicios (sin SSL primero)..."
# Primer arranque solo nginx en HTTP para que certbot valide
docker compose up -d db odoo n8n nginx

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " PASO SIGUIENTE: obtener certificados SSL"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  docker compose run --rm certbot certonly \\"
echo "    --webroot -w /var/www/certbot \\"
echo "    -d ${ODOO_DOMAIN} -d ${N8N_DOMAIN} \\"
echo "    --email ${EMAIL} --agree-tos --no-eff-email"
echo ""
echo "  Luego: docker compose restart nginx"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo " CREAR BASE DE DATOS inmobi_produccion:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  docker compose exec odoo /opt/odoo-src/odoo-bin \\"
echo "    -c /etc/odoo/odoo.conf \\"
echo "    -d inmobi_produccion \\"
echo "    -i estate_management,estate_crm,estate_wordpress,estate_social,estate_calendar,estate_document,estate_reports,estate_portal,estate_ai_agent \\"
echo "    --stop-after-init"
echo ""
