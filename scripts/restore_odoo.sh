#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Restaura un backup de Odoo (.zip generado por backup_odoo.sh)
# Uso:  ./restore_odoo.sh <archivo.zip> [nombre_db_destino]
# Ej:   ./restore_odoo.sh ~/odoo_backups/tesis_odoo19_20260613_020000.zip
#       ./restore_odoo.sh ~/odoo_backups/....zip tesis_restore
# ⚠ DETÉN el servidor Odoo antes de restaurar sobre la BD en uso.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ZIP="${1:?Indica el archivo .zip de backup}"
DEST_DB="${2:-tesis_odoo19}"
DB_USER="justin"
DB_HOST="/var/run/postgresql"
FILESTORE_BASE="$HOME/.local/share/Odoo/filestore"

[ -f "$ZIP" ] || { echo "No existe: $ZIP"; exit 1; }

echo "⚠ Esto REEMPLAZA la base '$DEST_DB' y su filestore. Ctrl+C para cancelar."
read -r -p "Escribe 'SI' para continuar: " ok
[ "$ok" = "SI" ] || { echo "Cancelado."; exit 0; }

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
unzip -q "$ZIP" -d "$WORK"

# Recrear la base
dropdb   -h "$DB_HOST" -U "$DB_USER" --if-exists "$DEST_DB"
createdb -h "$DB_HOST" -U "$DB_USER" "$DEST_DB"
psql     -h "$DB_HOST" -U "$DB_USER" -q "$DEST_DB" < "$WORK/dump.sql"
echo "✓ Base de datos restaurada en '$DEST_DB'"

# Restaurar filestore
if [ -d "$WORK/filestore" ]; then
    rm -rf "${FILESTORE_BASE:?}/$DEST_DB"
    mkdir -p "$FILESTORE_BASE"
    cp -a "$WORK/filestore" "$FILESTORE_BASE/$DEST_DB"
    echo "✓ Filestore restaurado en $FILESTORE_BASE/$DEST_DB"
fi
echo "Listo. Inicia Odoo y verifica."
