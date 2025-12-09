#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
notify_test.py – CyNiT notificatie test
---------------------------------------
Stuurt een testbericht naar alle geconfigureerde kanalen
(Telegram, Signal, Pushover, Matrix) via notify.py.
"""

import os
from datetime import datetime
from pathlib import Path

from notify import send_notifications  # gebruikt .env automatisch

# Optioneel: zorg dat we in de projectroot zitten (waar .env ligt)
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)


def build_test_message() -> str:
    """Maak een nette testmelding, met dashboard- en ngrok-info."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dashboard_url = os.getenv("CYNIT_DASHBOARD_URL", "http://localhost:8080")
    ngrok_info = os.getenv("NGROK_INFO", "").strip()

    lines = [
        "🔔 CyNiT DNS Scanner – TEST notificatie",
        f"Tijdstip: {ts}",
        "",
        f"Dashboard: {dashboard_url}",
    ]

    if ngrok_info:
        lines.append(f"ngrok: {ngrok_info}")

    return "\n".join(lines)


def main():
    msg = build_test_message()
    print("🔔 Stuur testnotificaties...")
    send_notifications(msg)
    print("🎯 Klaar.")


if __name__ == "__main__":
    main()
