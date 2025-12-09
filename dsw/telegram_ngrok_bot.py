#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
telegram_ngrok_bot.py – Telegram-bot voor ngrok + scanstatus op de CyNiT-Pi

Commands (alleen jouw chat – TELEGRAM_CHAT_ID – is toegestaan):
  /help         → toon uitleg
  /ngrok        → toon huidige ngrok-tunnels
  /ngrokstart  → zorg dat ngrok tcp 22 + http 8080 draaien, toon links
  /status       → toon DNS-scanstatus uit dashboard.json
"""

import os
import time
import json
import subprocess
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_FILE = BASE_DIR / "dashboard.json"


def load_env():
    """
    Simpele .env loader (KEY=VALUE per lijn).
    """
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print(f"⚠️ Fout bij lezen .env: {e}")


def run_ngrok(args):
    """
    Start ngrok met gegeven args.
    Probeert in volgorde:
      1. NGROK_BIN uit env
      2. /usr/local/bin/ngrok
      3. ngrok (uit PATH)

    Returns:
        True als een van de pogingen succesvol is gestart (Popen ok),
        False als alles faalt.
    """
    candidates = []
    env_bin = os.getenv("NGROK_BIN")
    if env_bin:
        candidates.append(env_bin)
    candidates.append("/usr/local/bin/ngrok")
    candidates.append("ngrok")

    last_err = None

    for binpath in candidates:
        try:
            print(f"ℹ️ Probeer ngrok te starten met: {binpath} {' '.join(args)}")
            subprocess.Popen(
                [binpath] + args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"✅ ngrok gestart: {binpath} {' '.join(args)}")
            return True
        except FileNotFoundError as e:
            last_err = e
            print(f"⚠️ ngrok-binary niet gevonden: {binpath} ({e})")
        except Exception as e:
            last_err = e
            print(f"⚠️ Kon ngrok niet starten met {binpath}: {e}")

    print(f"❌ Kon ngrok helemaal niet starten. Laatste fout: {last_err}")
    return False


def get_ngrok_tunnels():
    """
    Haal huidige ngrok-tunnels op via 127.0.0.1:4040/api/tunnels.

    Return:
        dict met:
        {
            "ssh": "tcp://x.tcp.eu.ngrok.io:12345" of None,
            "http": "https://subdomain.ngrok.io" of None,
        }
    """
    tunnels = {"ssh": None, "http": None}
    url = "http://127.0.0.1:4040/api/tunnels"

    try:
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"⚠️ Kon ngrok API niet bereiken op {url}: {e}")
        return tunnels

    print("ℹ️ ngrok API response ontvangen, tunnels parsen...")

    for t in data.get("tunnels", []):
        proto = t.get("proto")
        public = t.get("public_url", "")
        config = t.get("config", {}) or {}
        addr = str(config.get("addr", ""))

        print(f"  → Tunnel gevonden: proto={proto}, public={public}, addr={addr}")

        # SSH tunnel = tcp naar poort 22
        if proto == "tcp" and (addr.endswith(":22") or addr == "22" or ":22" in addr):
            tunnels["ssh"] = public

        # Dashboard tunnel = http/https naar poort 8080
        if proto in ("http", "https") and ("8080" in addr or addr.endswith(":8080")):
            tunnels["http"] = public

    print(f"ℹ️ Geparste tunnels: {tunnels}")
    return tunnels


def ensure_ngrok_running():
    """
    Zorgt dat zowel de SSH-tunnel als de HTTP-tunnel draaien.
    Start indien nodig:
      - ngrok tcp 22
      - ngrok http 8080

    Retourneert daarna opnieuw get_ngrok_tunnels().
    """
    print("🔁 ensure_ngrok_running: check huidige tunnels...")
    tunnels = get_ngrok_tunnels()
    started_any = False

    if tunnels["ssh"] is None:
        print("ℹ️ Geen SSH-tunnel gevonden. Probeer ngrok tcp 22 te starten...")
        if run_ngrok(["tcp", "22"]):
            started_any = True

    if tunnels["http"] is None:
        print("ℹ️ Geen HTTP/HTTPS-tunnel gevonden. Probeer ngrok http 8080 te starten...")
        if run_ngrok(["http", "8080"]):
            started_any = True

    if started_any:
        print("⏳ Even wachten zodat ngrok tijd heeft om op te starten...")
        time.sleep(5)

    tunnels = get_ngrok_tunnels()
    print(f"✅ Tunnels na ensure_ngrok_running: {tunnels}")
    return tunnels


def format_ngrok_message(tunnels: dict) -> str:
    ssh_url = tunnels.get("ssh") or "❌ Geen ngrok SSH tunnel (tcp 22)"
    http_url = tunnels.get("http") or "❌ Geen ngrok HTTP/HTTPS tunnel (poort 8080)"
    dashboard_url = os.getenv("CYNIT_DASHBOARD_URL", "http://localhost:8080")

    lines = [
        "🔍 *CyNiT – ngrok status*",
        "",
        f"📡 SSH via ngrok: `{ssh_url}`" if "ngrok" in ssh_url else f"📡 SSH via ngrok: {ssh_url}",
        f"🌐 Dashboard via ngrok: `{http_url}`" if "ngrok" in http_url else f"🌐 Dashboard via ngrok: {http_url}",
        "",
        f"📊 Lokale dashboard-URL: `{dashboard_url}`",
    ]
    return "\n".join(lines)


def read_dashboard():
    """
    Leest dashboard.json en geeft dict terug, of None bij fout/missing.
    """
    if not DASHBOARD_FILE.exists():
        print(f"ℹ️ {DASHBOARD_FILE} bestaat nog niet.")
        return None

    try:
        with DASHBOARD_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"ℹ️ dashboard.json gelezen: keys={list(data.keys())}")
            return data
    except Exception as e:
        print(f"⚠️ Kon {DASHBOARD_FILE} niet lezen: {e}")
        return None


def format_status_message(d: dict) -> str:
    """
    Bouw een nette status-tekst op basis van de dashboard-data.
    """
    status = d.get("status", "onbekend")
    processed = d.get("processed", 0)
    total = d.get("total", 0)
    valid = d.get("valid", 0)
    new_this_run = d.get("new_this_run", 0)
    speed = d.get("speed", 0)
    eta = d.get("eta", "onbekend")
    start_time = d.get("start_time", "-")
    last_save = d.get("last_save", "-")
    end_time = d.get("end_time")
    merk = d.get("merk")

    lines = [
        "📊 *CyNiT DNS Scan status*",
        "",
        f"Status: *{status}*",
        f"Verwerkt: {processed}/{total} combinaties",
        f"Unieke domeinen totaal: {valid}",
        f"Nieuwe domeinen deze run: {new_this_run}",
        f"Snelheid: {speed} combi/s",
        f"ETA: {eta}",
        "",
        f"Start: `{start_time}`",
        f"Laatst opgeslagen: `{last_save}`",
    ]

    if end_time:
        lines.append(f"Einde: `{end_time}`")
    if merk:
        lines.append(f"Huidig merk: `{merk}`")

    return "\n".join(lines)


def send_telegram_message(token: str, chat_id: str, text: str):
    """
    Stuurt bericht naar Telegram én print altijd wat er verstuurd wordt.
    """
    print("\n================ TELEGRAM OUT =================")
    print(f"→ chat_id: {chat_id}")
    print("→ message:")
    print(text)
    print("==============================================\n")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        print("✅ Telegram-bericht succesvol verstuurd.")
    except Exception as e:
        print(f"❌ Kon Telegram-bericht niet versturen: {e}")


def handle_command(text: str, token: str, chat_id: str):
    """
    Verwerkt een binnenkomend command en stuurt het juiste antwoord.
    Logt ook wat er gebeurt.
    """
    text = (text or "").strip()
    print("\n================ TELEGRAM IN ==================")
    print(f"← chat_id: {chat_id}")
    print(f"← text   : {text!r}")
    print("==============================================\n")

    if text in ("/start", "/help"):
        msg = (
            "🤖 *CyNiT ngrok & status-bot*\n\n"
            "Beschikbare commands:\n"
            "  • `/ngrok` – toon huidige ngrok-tunnels\n"
            "  • `/ngrokstart` – zorg dat ngrok tcp 22 + http 8080 draaien, toon links\n"
            "  • `/status` – toon DNS-scanstatus uit dashboard.json\n"
        )
        send_telegram_message(token, chat_id, msg)
        return

    if text.startswith("/ngrokstart"):
        print("ℹ️ Command: /ngrokstart → ensure_ngrok_running()...")
        tunnels = ensure_ngrok_running()
        msg = "🚀 ngrok (her)gestart en status opgehaald:\n\n" + format_ngrok_message(tunnels)
        send_telegram_message(token, chat_id, msg)
        return

    if text.startswith("/ngrok"):
        print("ℹ️ Command: /ngrok → get_ngrok_tunnels()...")
        tunnels = get_ngrok_tunnels()
        msg = format_ngrok_message(tunnels)
        send_telegram_message(token, chat_id, msg)
        return

    if text.startswith("/status"):
        print("ℹ️ Command: /status → read_dashboard()...")
        d = read_dashboard()
        if not d:
            msg = (
                "ℹ️ Geen dashboard-data beschikbaar.\n"
                "Is de scanner al gestart en heeft hij al één keer opgeslagen?"
            )
        else:
            msg = format_status_message(d)

        send_telegram_message(token, chat_id, msg)
        return

    # Onbekend command
    msg = (
        "❓ Onbekend command.\n\n"
        "Gebruik `/help` om de beschikbare commands te zien."
    )
    send_telegram_message(token, chat_id, msg)


def main():
    load_env()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID")  # zelfde als in notify.py

    if not token or not allowed_chat_id:
        print("❌ TELEGRAM_BOT_TOKEN of TELEGRAM_CHAT_ID ontbreekt. Vul deze in je .env in.")
        return

    print("🤖 CyNiT ngrok/status-bot gestart. Wachten op Telegram-commands...")
    base_url = f"https://api.telegram.org/bot{token}"

    offset = None

    while True:
        try:
            params = {
                "timeout": 30,
                "allowed_updates": json.dumps(["message"]),
            }
            if offset is not None:
                params["offset"] = offset

            resp = requests.get(f"{base_url}/getUpdates", params=params, timeout=35)
            resp.raise_for_status()
            data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = str(message["chat"]["id"])
                text = message.get("text", "")

                # Alleen commands uit jouw chat toelaten
                if chat_id != allowed_chat_id:
                    print(f"⚠️ Update uit andere chat ({chat_id}), genegeerd.")
                    continue

                handle_command(text, token, chat_id)

        except Exception as e:
            print(f"⚠️ Fout in polling-loop: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
