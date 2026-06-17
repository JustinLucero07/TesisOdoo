#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Backup automático de Odoo (base de datos + filestore)
# Genera un .zip restaurable y mantiene solo los últimos N backups.
# Uso:   ./backup_odoo.sh
# Cron:  0 2 * * *  /home/justin/Documentos/Tesis/scripts/backup_odoo.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuración ────────────────────────────────────────────────────────────
DB_NAME="tesis_odoo19"
DB_USER="justin"
DB_HOST="/var/run/postgresql"               # socket (auth peer, sin password)
FILESTORE="$HOME/.local/share/Odoo/filestore/$DB_NAME"
BACKUP_DIR="$HOME/odoo_backups"
RETENTION=14                                 # cuántos backups conservar
LOG="$BACKUP_DIR/backup.log"

# ── Preparación ──────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" | tee -a "$LOG"; }

log "── Inicio backup de '$DB_NAME' ──"

# ── 1. Dump de la base de datos (SQL plano, compatible con restore de Odoo) ──
pg_dump -h "$DB_HOST" -U "$DB_USER" --no-owner --no-privileges \
        "$DB_NAME" > "$WORK/dump.sql"
log "Base de datos exportada ($(du -h "$WORK/dump.sql" | cut -f1))"

# ── 2. Copia del filestore (adjuntos, imágenes, PDFs) ───────────────────────
if [ -d "$FILESTORE" ]; then
    cp -a "$FILESTORE" "$WORK/filestore"
    log "Filestore copiado ($(du -sh "$WORK/filestore" | cut -f1))"
else
    log "AVISO: no se encontró el filestore en $FILESTORE (se omite)"
    mkdir -p "$WORK/filestore"
fi

# ── 3. Empaquetar en un .zip restaurable ────────────────────────────────────
OUT="$BACKUP_DIR/${DB_NAME}_${STAMP}.zip"
( cd "$WORK" && zip -rq "$OUT" dump.sql filestore )
log "Backup creado: $OUT ($(du -h "$OUT" | cut -f1))"

# ── 4. Retención: borrar los más antiguos, conservar los últimos N ──────────
mapfile -t OLD < <(ls -1t "$BACKUP_DIR"/${DB_NAME}_*.zip 2>/dev/null | tail -n +$((RETENTION + 1)))
for f in "${OLD[@]:-}"; do
    [ -n "$f" ] && rm -f "$f" && log "Eliminado backup antiguo: $(basename "$f")"
done

log "── Backup OK. Total en disco: $(du -sh "$BACKUP_DIR" | cut -f1) ──"
