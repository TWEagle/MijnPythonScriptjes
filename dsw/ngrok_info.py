#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ngrok_info.py – snelle ngrok-check + notificatie

- Leest tunnels via get_ngrok_tunnels() uit local_scan.py
- Print overzicht naar console
- Stuurt een bericht via notify.send_notifications (Telegram / Signal / Pushover / Matrix)
"""

import os
from pathlib import Path

# Zorg dat we in de projectroot zitten (waar local_scan.py & notify.py liggen)
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

from local_scan import get_ngrok_tunnels, DASHBOARD_URL  # type: ignore

try:
    from notify import send_notifications  # type: ignore
except Exception:
    send_notifications = None


def build_message(tunnels: dict) -> str:
    ssh_url = tunnels.get("ssh") or "❌ Geen ngrok SSH tunnel (tcp 22)"
    http_url = tunnels.get("http") or "❌ Geen ngrok HTTP/HTTPS tunnel (poort 8080)"

    lines = [
        "🔍 CyNiT – ngrok status",
        "",
        f"📡 SSH via ngrok: {ssh_url}",
        f"🌐 Dashboard via ngrok: {http_url}",
    ]

    if DASHBOARD_URL:
        lines.append(f"📊 Dashboard URL: {DASHBOARD_URL}")

    return "\n".join(lines)


def main():
    print("🔎 Ngrok tunnels ophalen via lokale API...")
    tunnels = get_ngrok_tunnels()

    ssh_url = tunnels.get("ssh") or "❌ Geen ngrok SSH tunnel (tcp 22)"
    http_url = tunnels.get("http") or "❌ Geen ngrok HTTP/HTTPS tunnel (poort 8080)"

    print("\n=== Ngrok status ===")
    print(f"SSH   : {ssh_url}")
    print(f"HTTP  : {http_url}")
    print(f"Dash  : {DASHBOARD_URL}")
    print("====================\n")

    msg = build_message(tunnels)

    if send_notifications:
        print("📨 Verstuur ngrok-status via notify.py...")
        try:
            send_notifications(msg)
            print("✅ Notificatie verstuurd.")
        except Exception as e:
            print(f"⚠️ Kon notificatie niet versturen: {e}")
    else:
        print("ℹ️ notify.py niet beschikbaar, geen notificaties verstuurd.")


if __name__ == "__main__":
    main()
