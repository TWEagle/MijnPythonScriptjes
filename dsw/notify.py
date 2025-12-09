#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
notify.py – CyNiT DNS Scanner notificaties
------------------------------------------
Stuurt meldingen naar:
- Telegram
- Signal (via signal-cli-rest-api container)
- Pushover
- Matrix

Configuratie via .env in dezelfde map:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID

  SIGNAL_API_URL
  SIGNAL_SENDER
  SIGNAL_RECIPIENT

  PUSHOVER_TOKEN
  PUSHOVER_USER

  MATRIX_HOMESERVER
  MATRIX_ACCESS_TOKEN
  MATRIX_ROOM_ID

Optioneel:
  CYNIT_DASHBOARD_URL
  NGROK_INFO
"""

import os
import time
import uuid
from pathlib import Path
from urllib.parse import quote

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


# --- .env laden uit de projectroot (de map waar notify.py staat) ---
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

if load_dotenv is not None and env_path.exists():
    load_dotenv(env_path)


# =======================
#  Helper voor links
# =======================

def _append_link_to_text(message: str, link: str | None, link_title: str | None) -> str:
    """
    Voeg optioneel een link toe aan platte tekst.
    """
    if not link:
        return message
    title = link_title or link
    return f"{message}\n\n🔗 {title}: {link}"


# =======================
#  Telegram
# =======================

def send_telegram_message(message: str,
                          link: str | None = None,
                          link_title: str | None = None) -> str:
    """
    Stuur een Telegram-bericht op basis van .env:
      TELEGRAM_BOT_TOKEN
      TELEGRAM_CHAT_ID
    """

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return "⚠️ Telegram niet geconfigureerd (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID ontbreekt)."

    # Voor Telegram gebruiken we HTML en een klikbare link indien aanwezig
    if link:
        title = link_title or link
        text = f'{message}\n\n🔗 <a href="{link}">{title}</a>'
        parse_mode = "HTML"
    else:
        text = message
        parse_mode = "HTML"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            return "✅ Telegram: bericht verzonden."
        else:
            return f"❌ Telegram-fout ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ Telegram-exceptie: {e}"


# =======================
#  Signal (REST / linked device)
# =======================

def send_signal_message(message: str,
                        link: str | None = None,
                        link_title: str | None = None) -> str:
    """
    Stuur een Signal-bericht via de signal-cli-rest-api (linked device).

    Vereist in .env:
      SIGNAL_API_URL   (bv. http://127.0.0.1:8081)
      SIGNAL_SENDER    (jouw eigen nummer, bv. +32486...)
      SIGNAL_RECIPIENT (één of meerdere nummers, komma-gescheiden)
    """

    api_url = os.getenv("SIGNAL_API_URL", "http://127.0.0.1:8081").rstrip("/")
    sender = os.getenv("SIGNAL_SENDER")
    recipients_raw = os.getenv("SIGNAL_RECIPIENT")

    if not sender or not recipients_raw:
        return "⚠️ Signal niet geconfigureerd (SIGNAL_SENDER / SIGNAL_RECIPIENT ontbreekt)."

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        return "⚠️ Signal-configuratie onvolledig (geen geldige recipients)."

    text = _append_link_to_text(message, link, link_title)

    url = f"{api_url}/v2/send"
    payload = {
        "number": sender,
        "recipients": recipients,
        "message": text,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        # signal-cli-rest-api geeft vaak 201 bij succes
        if resp.status_code in (200, 201, 202):
            try:
                data = resp.json()
                ts = data.get("timestamp")
                if ts:
                    return f"✅ Signal: bericht verzonden (ts={ts})."
            except Exception:
                pass
            return "✅ Signal: bericht verzonden."
        else:
            return f"❌ Signal-fout ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ Signal-exceptie: {e}"


# =======================
#  Pushover
# =======================

def send_pushover_message(message: str,
                          link: str | None = None,
                          link_title: str | None = None) -> str:
    """
    Verstuur Pushover-notificatie via .env:
      PUSHOVER_TOKEN
      PUSHOVER_USER
    """

    api_token = os.getenv("PUSHOVER_TOKEN")
    user_key = os.getenv("PUSHOVER_USER")

    if not api_token or not user_key:
        return "⚠️ Pushover niet geconfigureerd."

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": api_token,
        "user": user_key,
        "message": message,
        "title": "CyNiT DNS Scanner",
        "priority": 0,
    }

    if link:
        payload["url"] = link
        payload["url_title"] = link_title or link

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            return "✅ Pushover: bericht verzonden."
        else:
            return f"❌ Pushover-fout ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ Pushover-exceptie: {e}"


# =======================
#  Matrix
# =======================

def send_matrix_message(message: str,
                        link: str | None = None,
                        link_title: str | None = None) -> str:
    """
    Verstuur Matrix-bericht naar een room via officiële HTTP API.

    Vereist in .env:
      MATRIX_HOMESERVER  (bv. https://matrix-client.matrix.org)
      MATRIX_ACCESS_TOKEN
      MATRIX_ROOM_ID     (bv. !abcdefg123456:matrix.org)
    """

    homeserver = os.getenv("MATRIX_HOMESERVER")
    access_token = os.getenv("MATRIX_ACCESS_TOKEN")
    room_id = os.getenv("MATRIX_ROOM_ID")

    if not homeserver or not access_token or not room_id:
        return "⚠️ Matrix niet geconfigureerd (MATRIX_HOMESERVER / MATRIX_ACCESS_TOKEN / MATRIX_ROOM_ID ontbreekt)."

    homeserver = homeserver.rstrip("/")
    room_id_enc = quote(room_id, safe="")

    body = _append_link_to_text(message, link, link_title)

    # Unieke transaction ID (zoals in jouw curl)
    txn_id = str(int(time.time()))  # of met uuid erbij, maar dit is voldoende

    url = (
        f"{homeserver}/_matrix/client/v3/rooms/"
        f"{room_id_enc}/send/m.room.message/{txn_id}"
    )

    payload = {
        "msgtype": "m.text",
        "body": body,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.put(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            return "✅ Matrix: bericht verzonden."
        else:
            return f"❌ Matrix-fout ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ Matrix-exceptie: {e}"


# =======================
#  Verzamelaar
# =======================

def send_notifications(message: str,
                       link: str | None = None,
                       link_title: str | None = None) -> None:
    """
    Stuur naar alle geconfigureerde kanalen.
    (Telegram + Signal + Pushover + Matrix)

    `link` en `link_title` zijn optioneel en worden per kanaal
    zo mooi mogelijk verwerkt (klikbare link waar het kan).
    """

    print("📨 Verzenden van notificaties...")

    telegram_status = send_telegram_message(message, link, link_title)
    signal_status = send_signal_message(message, link, link_title)
    pushover_status = send_pushover_message(message, link, link_title)
    matrix_status = send_matrix_message(message, link, link_title)

    print(telegram_status)
    print(signal_status)
    print(pushover_status)
    print(matrix_status)


if __name__ == "__main__":
    # Kleine test als je deze file direct runt
    dash = os.getenv("CYNIT_DASHBOARD_URL", "http://localhost:8080")
    ngrok = os.getenv("NGROK_INFO", "").strip()

    base_msg = "🔔 CyNiT DNS Scanner – testnotificatie vanuit notify.py"
    if ngrok:
        base_msg += f"\nngrok: {ngrok}"

    send_notifications(base_msg, link=dash, link_title="Dashboard")
