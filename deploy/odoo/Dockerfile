FROM python:3.12-slim-bookworm

LABEL maintainer="Inmobi <info@inmobi.com.ec>"

# ── Dependencias del sistema ───────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev build-essential libxml2-dev libxslt1-dev libldap2-dev \
    libsasl2-dev libssl-dev libjpeg-dev libfreetype-dev liblcms2-dev \
    libwebp-dev zlib1g-dev libffi-dev node-less git curl ca-certificates \
    fonts-noto-cjk fonts-liberation npm \
    # wkhtmltopdf para PDF
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# ── Odoo 19 Community desde GitHub ────────────────────────────────────────────
RUN git clone --depth 1 --branch 19.0 \
    https://github.com/odoo/odoo.git /opt/odoo-src \
    && pip install --no-cache-dir -r /opt/odoo-src/requirements.txt

# ── Dependencias extra del proyecto ───────────────────────────────────────────
COPY requirements-custom.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-custom.txt

# ── Usuario sin privilegios ────────────────────────────────────────────────────
RUN useradd -ms /bin/bash -d /var/lib/odoo odoo \
    && mkdir -p /var/lib/odoo /opt/odoo-addons \
    && chown -R odoo:odoo /var/lib/odoo /opt/odoo-addons

USER odoo
WORKDIR /opt/odoo-src

EXPOSE 8069 8072

CMD ["/opt/odoo-src/odoo-bin", "-c", "/etc/odoo/odoo.conf"]
