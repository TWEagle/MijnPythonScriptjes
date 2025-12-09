#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNS Scanner v5.4 – CyNiT "Full Dump + Notifier + Dashboard Link Edition"
------------------------------------------------------------------------
✅ Parallelle DNS-checks met echte resolutie
✅ TXT als 'bron van waarheid' (1 domein per lijn, split per 10.000)
✅ Bij nieuwe run: alleen nieuwe domeinen gezocht (oude worden overgeslagen)
✅ XLSX & CSV op het einde: volledige dump (alle domeinen)
✅ Oude XLSX/CSV worden bij start ingelezen en opgeschoond
✅ Dashboard met samenvatting + download-knoppen
✅ Notificaties naar Telegram / Signal / Matrix / Pushover
✅ UURLIJKSE status-update met voortgang + ngrok- & dashboard-info
✅ Single-instance lock: oudere runs worden gekilled
"""

import os
import glob
import json
import time
import signal
import socket
import threading
import io
import zipfile

import requests
import pandas as pd
import dns.resolver
import subprocess

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from flask import Flask, jsonify, render_template_string, send_file
from flask_cors import CORS
from flask import Markup

# === Config ===
MERKEN_FILE = "merken.txt"

# TXT-output tijdens scan (gesplitst per 10.000 regels)
TXT_BASE = "domeinen"
TXT_MAX_LINES = 10000

# Finale XLSX/CSV na afloop (chunks van max 10.000 rijen)
RESULTS_XLSX_BASE = "domeinen"
RESULTS_CSV_BASE = "domeinen"

PROGRESS_FILE = "progress.json"
DASHBOARD_FILE = "dashboard.json"
SCAN_LOG = "scan_log.txt"
TLD_CACHE = "tlds.txt"
LOCK_FILE = "scanner.lock"

SAVE_INTERVAL = 300      # schrijf elke 300 nieuwe domeinen naar TXT
MAX_THREADS = 25         # parallelle DNS-checks
RESOLVER_TIMEOUT = 2.0   # DNS timeout

# Dashboard-URL (voor in notificaties)
DASHBOARD_URL = os.getenv("CYNIT_DASHBOARD_URL", "http://localhost:8080")

# === Globals ===
merken_done = set()
dashboard_data = {
    "merk": None,
    "processed": 0,
    "valid": 0,
    "total": 0,
    "eta": "00:00:00",
    "speed": 0,
    "last_save": None,
    "status": "initializing",
    "start_time": None,
    "end_time": None,
    "new_this_run": 0,
    "txt_files": 0,
    "xlsx_files": 0,
    "csv_files": 0,
}
lock = threading.Lock()

# TXT / domein-state
known_domains = set()     # alle domeinen die we al kennen (historisch + deze run)
txt_file_index = 1
txt_line_count = 0

# Gestructureerde data:
existing_rows = []        # rijen die al bestonden vóór deze run (uit XLSX/CSV + TXT)
results_new = []          # rijen die tijdens deze run nieuw gevonden worden

# === Flask Dashboard ===
app = Flask(__name__)
CORS(app)

# === Notificaties ===

def notify_telegram(message: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": message},
            timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        log(f"⚠️ Telegram notificatie mislukt: {e}")

def notify_pushover(message: str):
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    if not token or not user:
        return
    try:
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": token,
            "user": user,
            "message": message,
            "title": "CyNiT DNS Scanner"
        }
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log(f"⚠️ Pushover notificatie mislukt: {e}")

def notify_signal(message: str):
    api_url = os.getenv("SIGNAL_API_URL")
    sender = os.getenv("SIGNAL_SENDER")
    recipient = os.getenv("SIGNAL_RECIPIENT")
    if not api_url or not sender or not recipient:
        return
    try:
        url = api_url.rstrip("/") + "/v2/send"
        payload = {
            "message": message,
            "number": sender,
            "recipients": [recipient],
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log(f"⚠️ Signal notificatie mislukt: {e}")

def notify_matrix(message: str):
    homeserver = os.getenv("MATRIX_HOMESERVER")
    token = os.getenv("MATRIX_ACCESS_TOKEN")
    room_id = os.getenv("MATRIX_ROOM_ID")
    if not homeserver or not token or not room_id:
        return
    try:
        txn_id = int(time.time())
        url = (
            f"{homeserver.rstrip('/')}"
            f"/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
            f"?access_token={token}"
        )
        payload = {"msgtype": "m.text", "body": message}
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log(f"⚠️ Matrix notificatie mislukt: {e}")

def send_notifications(message: str):
    """Stuur bericht naar alle geconfigureerde kanalen."""
    log(f"🔔 Notificatie: {message}")
    notify_telegram(message)
    notify_pushover(message)
    notify_signal(message)
    notify_matrix(message)

def format_status_message(prefix: str = "Status update"):
    """Maak een nette status-samenvatting voor notificaties."""
    ngrok_info = os.getenv("NGROK_INFO", "").strip()
    d = dashboard_data.copy()
    lines = [
        f"{prefix}",
        f"Status: {d.get('status')}",
        f"Verwerkt: {d.get('processed')}/{d.get('total')} combinaties",
        f"Unieke domeinen totaal: {d.get('valid')}",
        f"Nieuwe domeinen deze run: {d.get('new_this_run')}",
        f"Snelheid: {d.get('speed')} combi/s",
        f"ETA: {d.get('eta')}",
        f"Start: {d.get('start_time')}",
        f"Laatst opgeslagen: {d.get('last_save')}",
    ]
    if d.get("end_time"):
        lines.append(f"Einde: {d.get('end_time')}")
    if d.get("status") == "done":
        lines.append(
            f"TXT/XLSX/CSV: {d.get('txt_files')} / "
            f"{d.get('xlsx_files')} / {d.get('csv_files')}"
        )

    # Dashboard-link
    if DASHBOARD_URL:
        lines.append("")
        lines.append(f"Dashboard: {DASHBOARD_URL}")

    # ngrok-info (bv. tcp://7.tcp.eu.ngrok.io:19125)
    if ngrok_info:
        lines.append("")
        lines.append(f"ngrok: {ngrok_info}")

    return "\n".join(lines)

def status_notifier():
    """
    Stuurt periodiek (default elk uur) een statusupdate zolang de scan nog loopt.
    Interval aanpasbaar via STATUS_INTERVAL_MINUTES.
    """
    try:
        interval_min = int(os.getenv("STATUS_INTERVAL_MINUTES", "60"))
    except ValueError:
        interval_min = 60
    if interval_min <= 0:
        return

    # Eerste sleep zodat start-notificatie niet dubbel komt
    while True:
        time.sleep(interval_min * 60)
        status = dashboard_data.get("status")
        if status in ("done", "error"):
            break
        msg = format_status_message(prefix="⏱️ Uurlijkse statusupdate CyNiT DNS Scan")
        send_notifications(msg)

# === Logging & Helpers ===

def log(msg, console=True):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    if console:
        print(line)
    with open(SCAN_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def save_dashboard():
    with lock:
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2)

def release_lock():
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass
    except Exception as e:
        log(f"⚠️ Kon lock-bestand niet verwijderen: {e}")

def save_progress():
    """Veilig opslaan, zodat leeg progress.json nooit voorkomt."""
    temp_file = PROGRESS_FILE + ".tmp"
    data = {"merken_done": list(merken_done)}
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, PROGRESS_FILE)

def safe_exit(*args):
    log("🛑 Script gestopt, data veilig opslaan...")
    save_progress()
    save_dashboard()
    release_lock()
    send_notifications(
        f"CyNiT DNS Scan voortijdig gestopt (SIGINT/SIGTERM).\n"
        f"Dashboard: {DASHBOARD_URL}"
    )
    os._exit(0)

signal.signal(signal.SIGINT, safe_exit)
signal.signal(signal.SIGTERM, safe_exit)

def ensure_single_instance():
    """
    Zorg dat er maar één instantie draait:
    - Als LOCK_FILE bestaat en proces leeft nog -> killen.
    - Schrijf eigen PID in LOCK_FILE.
    """
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip() or "0")
        except Exception:
            old_pid = 0

        if old_pid > 0 and old_pid != os.getpid():
            log(f"⚠️ Vorige instantie gedetecteerd (PID {old_pid}), probeer te killen...")
            try:
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(3)
                # check of hij nog leeft
                try:
                    os.kill(old_pid, 0)
                except ProcessLookupError:
                    old_pid = 0
                else:
                    log("⚠️ Vorige instantie leeft nog, stuur SIGKILL...")
                    os.kill(old_pid, signal.SIGKILL)
            except ProcessLookupError:
                log("ℹ️ Vorige instantie was al gestopt.")
            except Exception as e:
                log(f"⚠️ Kon vorige instantie niet killen: {e}")

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    log(f"🔒 Lock verkregen (PID {os.getpid()}).")

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f).get("merken_done", []))
            except Exception:
                return set()
    return set()

# === DNS Resolver ===

def check_domain_exists(domain):
    try:
        r = dns.resolver.Resolver()
        r.timeout = RESOLVER_TIMEOUT
        r.lifetime = RESOLVER_TIMEOUT
        r.nameservers = ["8.8.8.8", "1.1.1.1"]
        r.resolve(domain, "A")
        return True
    except Exception:
        try:
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False

# === TLD Loader ===

def load_tlds():
    if os.path.exists(TLD_CACHE):
        log(f"📂 Gebruik lokale cache ({TLD_CACHE})")
        with open(TLD_CACHE) as f:
            return [t.strip().lower() for t in f if t.strip()]
    try:
        url = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
        resp = requests.get(url, timeout=15, verify=True)
        resp.raise_for_status()
        tlds = [t.lower() for t in resp.text.splitlines() if not t.startswith("#")]
        with open(TLD_CACHE, "w") as f:
            f.write("\n".join(tlds))
        log(f"✅ {len(tlds)} TLD's geladen.")
        return tlds
    except Exception as e:
        log(f"⚠️ TLD-lijst niet beschikbaar: {e}")
        if os.path.exists(TLD_CACHE):
            with open(TLD_CACHE) as f:
                return [t.strip().lower() for t in f if t.strip()]
        return ["com", "be", "nl", "org", "net"]

# === Gestructureerde state (bestaande XLSX/CSV inlezen) ===

def init_structured_state_from_excel_csv():
    """
    Lees bestaande XLSX/CSV-bestanden in:
    - vul existing_rows
    - vul known_domains
    Excel/CSV worden later gewist en aan het einde opnieuw opgebouwd.
    """
    global known_domains, existing_rows

    patterns = [
        f"{RESULTS_XLSX_BASE}.xlsx",
        f"{RESULTS_XLSX_BASE}_*.xlsx",
        f"{RESULTS_CSV_BASE}.csv",
        f"{RESULTS_CSV_BASE}_*.csv",
    ]

    files = []
    for pattern in patterns:
        files.extend(sorted(glob.glob(pattern)))

    if not files:
        log("ℹ️ Geen bestaande XLSX/CSV-exports gevonden.")
        return

    total_rows = 0
    for path in files:
        try:
            if path.lower().endswith(".xlsx"):
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)
        except Exception as e:
            log(f"⚠️ Kon {path} niet lezen: {e}")
            continue

        for _, row in df.iterrows():
            domein = str(row.get("Domein", "")).strip()
            if not domein:
                continue
            domein_lower = domein.lower()
            if domein_lower in known_domains:
                continue
            known_domains.add(domein_lower)
            existing_rows.append({
                "Merk": str(row.get("Merk", "")).strip(),
                "Domein": domein_lower,
                "Laatste scan": str(row.get("Laatste scan", "")).strip()
            })
            total_rows += 1

    log(
        "📂 Gestructureerde state geladen uit XLSX/CSV: "
        f"{total_rows} rijen, {len(known_domains)} unieke domeinen."
    )

# === TXT state (bestaande domeinen laden) ===

def init_txt_state():
    """
    Lees bestaande domeinen.txt / domeinen_*.txt in:
    - vul known_domains (indien nog niet via XLSX/CSV)
    - vul existing_rows (zonder Merk / Laatste scan als we die niet kennen)
    - stel txt_file_index + txt_line_count in zodat we netjes verder schrijven
    """
    global known_domains, txt_file_index, txt_line_count, existing_rows

    main_file = f"{TXT_BASE}.txt"
    pattern_other = f"{TXT_BASE}_*.txt"

    files = []
    if os.path.exists(main_file):
        files.append(main_file)
    files.extend(sorted(glob.glob(pattern_other)))

    if not files:
        log("ℹ️ Geen bestaande TXT-bestanden gevonden, start vers.")
        txt_file_index = 1
        txt_line_count = 0
        return

    total_lines = 0
    for idx, filename in enumerate(files, start=1):
        with open(filename, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        total_lines += len(lines)

        for d in lines:
            domein_lower = d.lower()
            if domein_lower not in known_domains:
                known_domains.add(domein_lower)
                existing_rows.append({
                    "Merk": "",
                    "Domein": domein_lower,
                    "Laatste scan": ""
                })

        # laatste file bepaalt index + line count
        if idx == len(files):
            if filename == main_file:
                txt_file_index = 1
            else:
                try:
                    suffix = filename.replace(f"{TXT_BASE}_", "").replace(".txt", "")
                    txt_file_index = int(suffix)
                except Exception:
                    txt_file_index = 1
            txt_line_count = len(lines) % TXT_MAX_LINES
            if txt_line_count == 0 and len(lines) > 0:
                # start volgende bestand bij nieuwe write
                txt_file_index += 1
                txt_line_count = 0

    log(
        "📂 TXT-state geladen: "
        f"{len(files)} bestand(en), {total_lines} regels, "
        f"{len(known_domains)} unieke domeinen totaal."
    )

# === TXT helper ===

def get_txt_filename():
    """Bepaal de huidige TXT-bestandsnaam op basis van de teller."""
    global txt_file_index, txt_line_count
    if txt_line_count >= TXT_MAX_LINES:
        txt_file_index += 1
        txt_line_count = 0
    if txt_file_index == 1:
        # eerste bestand: domeinen.txt
        return f"{TXT_BASE}.txt"
    else:
        # volgende: domeinen_2.txt, domeinen_3.txt, ...
        return f"{TXT_BASE}_{txt_file_index}.txt"

# === File writing tijdens scan (alleen TXT voor nieuwe domeinen) ===

def append_to_files(batch):
    """
    Schrijf alleen nieuwe domeinen naar TXT tijdens de scan.
    Maximaal TXT_MAX_LINES per bestand, dan roteren.
    batch: lijst van dicts met minstens de sleutel 'Domein'.
    """
    global txt_line_count

    if not batch:
        return

    filename = get_txt_filename()
    with open(filename, "a", encoding="utf-8") as f:
        for row in batch:
            domein = str(row.get("Domein", "")).strip()
            if domein:
                f.write(domein + "\n")
                txt_line_count += 1

    dashboard_data["last_save"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_dashboard()

# === Finale XLSX/CSV output na scan (volledige dump) ===

def update_file_summary_in_dashboard():
    """Tel aantal TXT/XLSX/CSV-bestanden en zet in dashboard_data."""
    txt_files = glob.glob(f"{TXT_BASE}.txt") + glob.glob(f"{TXT_BASE}_*.txt")
    xlsx_files = glob.glob(f"{RESULTS_XLSX_BASE}.xlsx") + glob.glob(f"{RESULTS_XLSX_BASE}_*.xlsx")
    csv_files = glob.glob(f"{RESULTS_CSV_BASE}.csv") + glob.glob(f"{RESULTS_CSV_BASE}_*.csv")

    dashboard_data["txt_files"] = len(txt_files)
    dashboard_data["xlsx_files"] = len(xlsx_files)
    dashboard_data["csv_files"] = len(csv_files)
    save_dashboard()

def write_final_outputs():
    """
    Maak aan het einde van de scan XLSX- en CSV-bestanden
    op basis van ALLE bekende domeinen (existing_rows + results_new).
    Chunks van max 10.000 rijen per bestand.
    """
    all_rows = existing_rows + results_new
    if not all_rows:
        log("ℹ️ Geen domeinen bekend; XLSX/CSV worden niet aangemaakt.")
        return

    df = pd.DataFrame(all_rows)
    # Zorg dat domeinen uniek zijn: 1 rij per domein (we houden de eerste)
    df["Domein"] = df["Domein"].astype(str).str.lower()
    df = df.drop_duplicates(subset=["Domein"], keep="first")

    total = len(df)
    chunksize = 10000
    num_chunks = (total + chunksize - 1) // chunksize

    log(f"📊 Finale FULL dump genereren voor {total} domeinen in {num_chunks} chunk(s).")

    for i in range(num_chunks):
        start = i * chunksize
        end = min((i + 1) * chunksize, total)
        chunk = df.iloc[start:end]

        suffix = ""
        if num_chunks > 1:
            suffix = f"_{i+1}"

        xlsx_name = f"{RESULTS_XLSX_BASE}{suffix}.xlsx"
        csv_name = f"{RESULTS_CSV_BASE}{suffix}.csv"

        chunk.to_excel(xlsx_name, index=False)
        chunk.to_csv(csv_name, index=False)

        log(f"📁 Geschreven: {xlsx_name} en {csv_name} ({len(chunk)} rijen)")

    log("✅ Alle XLSX- en CSV-bestanden (FULL dump) zijn aangemaakt.")
    update_file_summary_in_dashboard()

# === Opschonen oude XLSX/CSV ===

def cleanup_old_outputs():
    patterns = [
        f"{RESULTS_XLSX_BASE}.xlsx",
        f"{RESULTS_XLSX_BASE}_*.xlsx",
        f"{RESULTS_CSV_BASE}.csv",
        f"{RESULTS_CSV_BASE}_*.csv",
    ]
    removed = 0
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                os.remove(path)
                removed += 1
            except Exception as e:
                log(f"⚠️ Kon {path} niet verwijderen: {e}", console=True)
    if removed:
        log(f"🧹 Oude XLSX/CSV-bestanden opgeschoond ({removed} bestanden).")
    else:
        log("ℹ️ Geen oude XLSX/CSV-bestanden om op te schonen.")

# === ZIP helper voor downloads ===

def zip_files(patterns, zip_name="export.zip"):
    """Maak ZIP uit alle bestanden die matchen."""
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for pattern in patterns:
            for path in glob.glob(pattern):
                zf.write(path, os.path.basename(path))
    mem_zip.seek(0)
    return mem_zip

# === Flask routes ===

@app.route("/")
def dashboard():
    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="5">
        <title>CyNiT DNS Dashboard</title>
        <style>
            body { font-family: Arial; background: #101010; color: #ddd; padding: 30px; }
            h1 { color: #4CAF50; }
            h2 { color: #4CAF50; margin-top: 20px; }
            .stat { margin: 6px 0; }
            .label { color: #4CAF50; font-weight: bold; }
            .btn {
                display: inline-block;
                padding: 10px 15px;
                background: #4CAF50;
                color: black;
                border-radius: 6px;
                margin-right: 10px;
                text-decoration: none;
                font-weight: bold;
                margin-top: 10px;
            }
            .btn:hover { background: #45a049; }
            .summary-box {
                background: #181818;
                padding: 15px;
                border-radius: 8px;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <h1>🌍 CyNiT DNS Scanner Dashboard</h1>

        <div class="stat"><span class="label">Status:</span> {{d.status}}</div>
        <div class="stat"><span class="label">Huidig merk:</span> {{d.merk}}</div>
        <div class="stat"><span class="label">Verwerkte combinaties:</span> {{d.processed}} / {{d.total}}</div>
        <div class="stat"><span class="label">Unieke domeinen totaal:</span> {{d.valid}}</div>
        <div class="stat"><span class="label">Nieuwe domeinen deze run:</span> {{d.new_this_run}}</div>
        <div class="stat"><span class="label">Snelheid:</span> {{d.speed}} domeinen/s</div>
        <div class="stat"><span class="label">ETA:</span> {{d.eta}}</div>
        <div class="stat"><span class="label">Laatste save:</span> {{d.last_save}}</div>
        <div class="stat"><span class="label">Starttijd:</span> {{d.start_time}}</div>
        <div class="stat"><span class="label">Eindtijd:</span> {{d.end_time}}</div>

        <div class="summary-box">
            <h2>📊 Samenvatting</h2>
            <div class="stat"><span class="label">TXT-bestanden:</span> {{d.txt_files}}</div>
            <div class="stat"><span class="label">XLSX-bestanden:</span> {{d.xlsx_files}}</div>
            <div class="stat"><span class="label">CSV-bestanden:</span> {{d.csv_files}}</div>
        </div>

        {% if d.status == "done" %}
            <h2>📥 Downloads</h2>
            <a class="btn" href="/download/txt">TXT Export (ZIP)</a>
            <a class="btn" href="/download/xlsx">XLSX Export (ZIP)</a>
            <a class="btn" href="/download/csv">CSV Export (ZIP)</a>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(html, d=dashboard_data)

@app.route("/status")
def status():
    return jsonify(dashboard_data)

@app.route("/download/txt")
def download_txt():
    patterns = [f"{TXT_BASE}.txt", f"{TXT_BASE}_*.txt"]
    mem_zip = zip_files(patterns, "txt_export.zip")
    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name="txt_export.zip",
    )

@app.route("/download/xlsx")
def download_xlsx():
    patterns = [f"{RESULTS_XLSX_BASE}.xlsx", f"{RESULTS_XLSX_BASE}_*.xlsx"]
    mem_zip = zip_files(patterns, "xlsx_export.zip")
    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name="xlsx_export.zip",
    )

@app.route("/download/csv")
def download_csv():
    patterns = [f"{RESULTS_CSV_BASE}.csv", f"{RESULTS_CSV_BASE}_*.csv"]
    mem_zip = zip_files(patterns, "csv_export.zip")
    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name="csv_export.zip",
    )

@app.route("/status")
def status_page():
    """
    Toont de output van: python3 run_pi_scan.py --status
    in een nette HTML <pre>-weergave.
    """

    try:
        result = subprocess.run(
            ["python3", "run_pi_scan.py", "--status"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR  # zodat paths juist zijn
        )
        output = result.stdout + "\n" + result.stderr
    except Exception as e:
        output = f"Kon status niet ophalen: {e}"

    html = f"""
    <html>
    <head>
        <title>CyNiT Scanner – Status</title>
        <style>
            body {{
                background-color: #111;
                color: #eee;
                font-family: Consolas, monospace;
                padding: 20px;
            }}
            pre {{
                background: #222;
                padding: 20px;
                border-radius: 8px;
                overflow-x: auto;
                white-space: pre-wrap;
            }}
            a {{
                color: #0af;
            }}
        </style>
    </head>
    <body>
        <h1>📊 CyNiT Scanner – Status</h1>
        <p><a href="/">⬅ Terug naar Dashboard</a></p>
        <pre>{Markup(output)}</pre>
    </body>
    </html>
    """

    return html


def start_dashboard():
    log("🌐 Dashboard actief op http://localhost:8080")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

# === Main Scanner ===

def main():
    global dashboard_data

    ensure_single_instance()

    dashboard_data["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_dashboard()

    log(f"📁 Gebruikt progress-bestand: {os.path.abspath(PROGRESS_FILE)}")
    loaded_progress = load_progress()
    if loaded_progress:
        merken_done.update(loaded_progress)
        log(f"🔁 Hervat vorige sessie ({len(loaded_progress)} merken voltooid).")
    else:
        log("🆕 Nieuwe scan gestart — geen bestaande voortgang gevonden.")

    if not os.path.exists(MERKEN_FILE):
        log("❌ Geen merken.txt gevonden.")
        send_notifications(
            "CyNiT DNS Scan kon niet starten: geen merken.txt gevonden.\n"
            f"Dashboard: {DASHBOARD_URL}"
        )
        release_lock()
        return

    # 1) Gestructureerde state (XLSX/CSV) inlezen
    init_structured_state_from_excel_csv()

    # 2) TXT-state inlezen (vult known_domains & existing_rows verder aan)
    init_txt_state()

    dashboard_data["valid"] = len(known_domains)
    update_file_summary_in_dashboard()

    # 3) Oude XLSX/CSV verwijderen (we bouwen ze straks opnieuw op als FULL dump)
    cleanup_old_outputs()

    # 4) Merken & TLD's laden
    with open(MERKEN_FILE) as f:
        merken = [m.strip() for m in f if m.strip() and not m.startswith("#")]

    tlds = load_tlds()
    total = len(merken) * len(tlds)
    dashboard_data.update({"total": total, "status": "running"})
    save_dashboard()

    start_msg = (
        "🚀 CyNiT DNS Scan gestart.\n"
        f"Merken: {len(merken)}\n"
        f"TLD's: {len(tlds)}\n"
        f"Totale combinaties: {total}\n"
        f"Dashboard: {DASHBOARD_URL}"
    )
    send_notifications(start_msg)

    log(f"📦 {len(merken)} merken geladen — {len(tlds)} TLD’s actief.")
    start_time = time.time()
    processed = 0  # aantal combinaties (merk x TLD) die we behandeld hebben

    with tqdm(total=total, desc="🔍 Scannen", ncols=100, unit="combinaties") as pbar:
        for merk in merken:
            if merk in merken_done:
                continue

            merk_clean = merk.lower().replace(" ", "")
            domeinen = [f"{merk_clean}.{t}" for t in tlds]

            # We moeten alleen DNS-check doen voor domeinen die nog niet in known_domains zitten
            to_check = []
            for d in domeinen:
                d_lower = d.lower()
                if d_lower in known_domains:
                    # we kennen dit domein al, alleen progress omhoog
                    processed += 1
                    pbar.update(1)
                else:
                    to_check.append(d_lower)

            batch_valid = []
            merk_new = 0  # nieuwe domeinen voor dit merk (tijdens deze run)

            dashboard_data["merk"] = merk
            save_dashboard()

            # Parallel DNS-checks enkel voor de onbekende domeinen
            if to_check:
                with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
                    futures = {ex.submit(check_domain_exists, d): d for d in to_check}
                    for fut in as_completed(futures):
                        domein = futures[fut]
                        bestaat = fut.result()
                        processed += 1
                        pbar.update(1)

                        if bestaat and domein not in known_domains:
                            known_domains.add(domein)
                            row = {
                                "Merk": merk,
                                "Domein": domein,
                                "Laatste scan": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            batch_valid.append(row)
                            results_new.append(row)
                            merk_new += 1
                            dashboard_data["new_this_run"] = len(results_new)

                        # Dashboard bijwerken
                        elapsed = max(1, time.time() - start_time)
                        speed = round(processed / elapsed, 2)
                        eta = (total - processed) / speed if speed else 0
                        uren, rest = divmod(int(eta), 3600)
                        minuten, seconden = divmod(rest, 60)
                        dashboard_data.update({
                            "processed": processed,
                            "valid": len(known_domains),  # totaal unieke bekende domeinen
                            "speed": speed,
                            "eta": f"{uren:02d}:{minuten:02d}:{seconden:02d}"
                        })
                        save_dashboard()

                        if len(batch_valid) >= SAVE_INTERVAL:
                            append_to_files(batch_valid)
                            batch_valid.clear()
                            save_progress()

            # Na merk klaar
            if batch_valid:
                append_to_files(batch_valid)

            merken_done.add(merk)
            save_progress()
            log(
                f"✅ {merk}: {merk_new} nieuwe domeinen gevonden "
                f"(totaal nu {len(known_domains)})."
            )

    dashboard_data["status"] = "done"
    dashboard_data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_dashboard()
    log("🎉 Scan volledig afgerond, FULL dump wordt nu aangemaakt...")

    # Maak XLSX/CSV op basis van ALLE bekende domeinen (historisch + deze run)
    write_final_outputs()

    msg = format_status_message(prefix="🎉 CyNiT DNS Scan afgerond")
    send_notifications(msg)

    release_lock()
    log("🏁 Klaar.")

if __name__ == "__main__":
    threading.Thread(target=start_dashboard, daemon=True).start()
    threading.Thread(target=status_notifier, daemon=True).start()
    main()
