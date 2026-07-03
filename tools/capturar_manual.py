#!/usr/bin/env python3
"""Captura automática de pantallas de Inmobi para el Manual de Usuario.

Inicia sesión en el Odoo local, navega a las pantallas clave y guarda las
capturas en docs/manual_img/. Luego, `bash docs/build_manual_pdf.sh` genera el
PDF con esas imágenes embebidas.

Requisitos (ya presentes en el venv del proyecto): requests, websockets y
google-chrome instalado. Uso:

    source venv19/bin/activate
    python tools/capturar_manual.py                 # usa admin/admin y localhost:8070
    BASE=http://localhost:8070 DB=tesis_odoo19 \
        AI_LOGIN=admin AI_PASS=admin python tools/capturar_manual.py
"""
import asyncio, base64, json, os, subprocess, time, urllib.request
import requests
import websockets

BASE = os.environ.get("BASE", "http://localhost:8070")
DB = os.environ.get("DB", "tesis_odoo19")
LOGIN = os.environ.get("AI_LOGIN", "admin")
PASS = os.environ.get("AI_PASS", "admin")
PORT = int(os.environ.get("CDP_PORT", "9222"))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "manual_img")
os.makedirs(OUT, exist_ok=True)

# 1) Autenticación → cookies de sesión
s = requests.Session()
s.post(f"{BASE}/web/session/authenticate", json={"jsonrpc": "2.0", "params": {
    "db": DB, "login": LOGIN, "password": PASS}}, timeout=20)


def call_kw(model, method, args, kwargs=None):
    return s.post(f"{BASE}/web/dataset/call_kw", json={"jsonrpc": "2.0", "params": {
        "model": model, "method": method, "args": args, "kwargs": kwargs or {}}},
        timeout=30).json().get("result")


def xmlid(module, name):
    r = call_kw("ir.model.data", "search_read",
                [[["module", "=", module], ["name", "=", name]], ["res_id"]])
    return r[0]["res_id"] if r else None


act_prop = xmlid("estate_management", "estate_property_action")
act_crm = xmlid("crm", "crm_lead_action_pipeline")
act_board = xmlid("estate_reports", "estate_board_action")
prop = call_kw("estate.property", "search_read", [[["state", "!=", "draft"]], ["id"]], {"limit": 1}) \
    or call_kw("estate.property", "search_read", [[], ["id"]], {"limit": 1})
lead = call_kw("crm.lead", "search_read", [[["type", "=", "opportunity"]], ["id"]], {"limit": 1})
prop_id = prop[0]["id"] if prop else None
lead_id = lead[0]["id"] if lead else None

# (archivo, url, requiere_login)
shots = [("03_login.png", f"{BASE}/web/login", False)]
shots.append(("01_apps_home.png", f"{BASE}/odoo", True))
if act_prop:
    shots.append(("02_propiedades_lista.png", f"{BASE}/odoo/action-{act_prop}", True))
    if prop_id:
        shots.append(("04_propiedad_form.png", f"{BASE}/odoo/action-{act_prop}/{prop_id}", True))
if act_crm:
    shots.append(("05_crm_pipeline.png", f"{BASE}/odoo/action-{act_crm}", True))
    if lead_id:
        shots.append(("05b_lead_form.png", f"{BASE}/odoo/action-{act_crm}/{lead_id}", True))
if act_board:
    shots.append(("11_dashboard.png", f"{BASE}/odoo/action-{act_board}", True))

# 2) Chrome con depuración remota
prof = os.path.join(REPO, ".chrome_manual_prof")
chrome = subprocess.Popen([
    "google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
    f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}",
    "--hide-scrollbars", "--window-size=1500,950", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ws_url():
    for _ in range(15):
        try:
            data = json.loads(urllib.request.urlopen(f"http://localhost:{PORT}/json").read())
            pages = [t for t in data if t.get("type") == "page"]
            if pages:
                return pages[0]["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("No se pudo conectar al DevTools de Chrome")


async def main():
    async with websockets.connect(ws_url(), max_size=None) as ws:
        mid = 0

        async def cmd(method, params=None, tmo=40):
            nonlocal mid
            mid += 1
            myid = mid
            await ws.send(json.dumps({"id": myid, "method": method, "params": params or {}}))

            async def _w():
                while True:
                    m = json.loads(await ws.recv())
                    if m.get("id") == myid:
                        return m.get("result", {})
            try:
                return await asyncio.wait_for(_w(), timeout=tmo)
            except asyncio.TimeoutError:
                return {}

        await cmd("Page.enable")
        await cmd("Network.enable")
        await cmd("Emulation.setDeviceMetricsOverride",
                  {"width": 1500, "height": 950, "deviceScaleFactor": 1, "mobile": False})

        cookies_set = False
        for fname, url, need_login in shots:
            if need_login and not cookies_set:
                for c in s.cookies:
                    await cmd("Network.setCookie",
                              {"name": c.name, "value": c.value, "domain": "localhost", "path": "/"})
                cookies_set = True
            await cmd("Page.navigate", {"url": url})
            await asyncio.sleep(7)  # esperar render del SPA
            res = await cmd("Page.captureScreenshot", {"format": "png"})
            if res.get("data"):
                with open(os.path.join(OUT, fname), "wb") as f:
                    f.write(base64.b64decode(res["data"]))
                print("OK  ", fname)
            else:
                print("FALLO", fname)
    chrome.terminate()


asyncio.run(main())
print("\nListo. Imágenes en:", OUT)
print("Ahora genera el PDF:  bash docs/build_manual_pdf.sh")
