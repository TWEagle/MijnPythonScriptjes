#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import subprocess
import os
import datetime
import glob
import sys
from pathlib import Path
from notify import send_telegram_message, send_signal_message

# === Config ===
BASE_DIR = Path("/home/tweagle/dns-scanner-webapp")
RESULTS_DIR = BASE_DIR / "results"
TOKEN_FILE = Path.home() / ".github_token"
ADMIN_PW_FILE = Path.home() / ".beheer_pw"
SCANNER_PATH = BASE_DIR / "pi" / "pi_scanner.py"

st.set_page_config(page_title="CyNiT Pi Webinterface", layout="wide")
st.title("🧩 CyNiT Pi Domein & DNS Platform")

tabs = st.tabs(["🔍 Scanner", "⚙️ Beheer", "📱 Meldingen", "📘 Documentatie"])

# --- Helper functies ---
def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr

def push_to_github():
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    os.chdir(BASE_DIR)
    subprocess.run(["git", "config", "user.name", "pi-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "info@tweagle.eu"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
    subprocess.run(["git", "add", "."], check=True)
    msg = f"Pi Web Update – {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    subprocess.run(["git", "commit", "-m", msg], check=False)
    subprocess.run(["git", "push", f"https://{token}@github.com/TWEagle/dns-scanner-webapp.git", "main"], check=True)
    subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/TWEagle/dns-scanner-webapp.git"], check=True)
    return "✅ Gesynchroniseerd met GitHub."

def scan_brands():
    cmd = f"{BASE_DIR}/venv/bin/python3 {SCANNER_PATH}"
    return run_command(cmd)

# --- Scanner tab ---
with tabs[0]:
    st.header("🔍 Start Merkdomein- en DNS-scan")
    st.write("Voer een merk- en domeinscan uit vanuit de Pi-omgeving.")
    if st.button("🚀 Start volledige scan"):
        st.info("Scan gestart… dit kan even duren.")
        output = scan_brands()
        st.code(output)
        st.success("✅ Scan uitgevoerd. Resultaten vind je in /results/")

    st.markdown("---")
    latest = sorted(glob.glob(str(RESULTS_DIR / "*.xlsx")))
    if latest:
        st.download_button("📥 Laatste resultaten downloaden",
                           open(latest[-1], "rb"), file_name=os.path.basename(latest[-1]))
        st.dataframe(pd.read_excel(latest[-1]))

# --- Beheer tab ---
with tabs[1]:
    st.header("⚙️ Beheerinstellingen")

    if not ADMIN_PW_FILE.exists():
        st.warning("Nog geen beheerderswachtwoord ingesteld. Maak dit bestand aan met het gewenste wachtwoord.")
        st.stop()

    if "admin_ok" not in st.session_state:
        pw = st.text_input("Beheerderswachtwoord:", type="password")
        if pw == ADMIN_PW_FILE.read_text().strip():
            st.session_state.admin_ok = True
        else:
            st.stop()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬆️ Push wijzigingen naar GitHub"):
            st.code(push_to_github())

    with col2:
        if st.button("🔁 Herlaad GitHub-repo"):
            out = run_command(f"cd {BASE_DIR} && git pull")
            st.code(out)

    st.markdown("### 🧭 Status")
    status = run_command("systemctl is-active streamlit-app.service").strip()
    st.info(f"Streamlit-service status: {status}")

# --- Meldingen tab ---
with tabs[2]:
    st.header("📱 Telegram & Signal-meldingen")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📨 Testbericht (Telegram)"):
            msg = send_telegram_message("🔔 Test van CyNiT Pi Webinterface")
            st.success(msg)
    with col2:
        if st.button("📨 Testbericht (Signal)"):
            msg = send_signal_message("💬 Test van CyNiT Pi Webinterface")
            st.success(msg)

# --- Documentatie tab ---
with tabs[3]:
    st.header("📘 Handleidingen")
    docs = list(BASE_DIR.glob("docs/*.md")) + list(BASE_DIR.glob("*.md"))
    if not docs:
        st.info("Geen documentatie gevonden.")
    else:
        file = st.selectbox("Kies een bestand:", [d.name for d in docs])
        content = Path(BASE_DIR / "docs" / file).read_text(errors="ignore") if (BASE_DIR / "docs" / file).exists() else Path(BASE_DIR / file).read_text(errors="ignore")
        st.markdown(content)
st.caption("CyNiT © 2025 – Pi Hybrid Web Console")
