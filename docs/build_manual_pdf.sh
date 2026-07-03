#!/bin/bash
# Genera el PDF del manual. Omite automáticamente las imágenes que aún no existan.
# Uso: bash docs/build_manual_pdf.sh   (ejecuta antes tools/capturar_manual.py para incluir capturas)
set -e
cd "$(dirname "$0")"
TMP=".manual_build.md"
python3 - "$TMP" <<'PY'
import os, re, sys
src=open('MANUAL_USUARIO_COMPLETO.md',encoding='utf-8').read()
def keep(m):
    path=m.group(1)
    return m.group(0) if os.path.exists(path) else ''  # quita la img si no existe
out=re.sub(r'!\[[^\]]*\]\(([^)]+)\)', keep, src)
open(sys.argv[1],'w',encoding='utf-8').write(out)
PY
pandoc "$TMP" \
  -o Manual_Usuario_Inmobi_Completo.pdf \
  --pdf-engine=wkhtmltopdf --toc --toc-depth=2 \
  --css=manual_style.css \
  --metadata title="Manual de Usuario — Inmobi" \
  -V margin-top=18mm -V margin-bottom=18mm -V margin-left=16mm -V margin-right=16mm \
  --pdf-engine-opt=--enable-local-file-access --pdf-engine-opt=--encoding --pdf-engine-opt=utf-8
rm -f "$TMP"
echo "PDF generado: docs/Manual_Usuario_Inmobi_Completo.pdf"
