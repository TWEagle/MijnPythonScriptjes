import streamlit as st
import pandas as pd
import dns.resolver
import whois
from ipwhois import IPWhois
import socket
import ssl
import time
import subprocess
import sys
import os
import datetime
import glob
from notify import send_telegram_message, send_signal_message

# ----------------------
# Configuratie
# ----------------------
REPO_DIR = "/home/ubuntu/dns-scanner-webapp"
RESULTS_DIR = os.path.join(REPO_DIR, "results")
TOKEN_FILE = os.path.expanduser("~/.github_token")
ADMIN_PW_FILE = os.path.expanduser("~/.beheer_pw")

# ----------------------
# Hulpfuncties
# ----------------------
def get_dns_records(domain):
    record_types = ["A", "AAAA", "MX", "NS", "CNAME", "TXT", "SOA"]
    results = {}
    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(domain, rtype)
            results[rtype] = ", ".join([str(rdata.to_text()) for rdata in answers])
        except Exception:
            results[rtype] = None
    return results


def get_whois_info(domain):
    try:
        w = whois.whois(domain)
        return {
            "Registrar": w.registrar,
            "Creation Date": str(w.creation_date),
            "Expiration Date": str(w.expiration_date),
            "Status": str(w.status),
        }
    except Exception:
        return {"Registrar": None, "Creation Date": None, "Expiration Date": None, "Status": None}


def get_ip_info(domain):
    try:
        ip = socket.gethostbyname(domain)
        obj = IPWhois(ip)
        info = obj.lookup_rdap()
        return {
            "IP": ip,
            "ASN": info.get("asn"),
            "Org": info.get("asn_description"),
            "Country": info.get("asn_country_code"),
        }
    except Exception:
        return {"IP": None, "ASN": None, "Org": None, "Country": None}


def get_ssl_info(domain):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert["issuer"]).get("organizationName")
                valid_to = cert["notAfter"]
                return {"Cert_Issuer": issuer, "Cert_Valid_To": valid_to}
    except Exception:
        return {"Cert_Issuer": None, "Cert_Valid_To": None}


def run_install_checker():
    result = subprocess.run(
        [sys.executable, "install_requirements.py"],
        capture_output=True,
        text=True,
    )
    return result.stdout


def push_to_github():
    with open(TOKEN_FILE, "r") as f:
        token = f.read().strip()

    os.chdir(REPO_DIR)
    subprocess.run(["git", "config", "user.name", "dns-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "info@tweagle.eu"], check=True)

    remote_url = f"https://{token}@github.com/TWEagle/dns-scanner-webapp.git"
    subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)

    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
    subprocess.run(["git", "add", "."], check=True)
    commit_msg = f"Update vanaf webinterface - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=False)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    clean_url = "https://github.com/TWEagle/dns-scanner-webapp.git"
    subprocess.run(["git", "remote", "set-url", "origin", clean_url], check=True)
    return "✅ Push voltooid en repo gesynchroniseerd met GitHub!"

def run_command(cmd):
    cmd = f"sudo {cmd}" if not cmd.strip().startswith("sudo") else cmd
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()



# ----------------------
# Streamlit Tabs
# ----------------------
st.set_page_config(page_title="CyNiT Domein & DNS Scanner", layout="wide")
st.title("🌐 CyNiT Domein & DNS Scanner")

tabs = st.tabs(["🔍 Scanner", "⚙️ Beheer", "📱 Meldingen", "📘 Help & Documentatie"])

# ----------------------
# Tab 1 – Scanner
# ----------------------
with tabs[0]:
    st.write("Upload een Excel-bestand met een kolom genaamd `domein`.")
    uploaded_file = st.file_uploader("📁 Kies je Excel-bestand", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if "domein" not in df.columns:
            st.error("Excel moet een kolom 'domein' bevatten.")
        else:
            st.success(f"{len(df)} domeinen gevonden.")
            if st.button("🚀 Start Scan"):
                results = []
                progress = st.progress(0)
                for i, row in df.iterrows():
                    domain = row["domein"].strip()
                    st.write(f"🔍 Scannen: {domain}")

                    dns_data = get_dns_records(domain)
                    whois_data = get_whois_info(domain)
                    ip_data = get_ip_info(domain)
                    ssl_data = get_ssl_info(domain)

                    combined = {"Domein": domain}
                    combined.update(dns_data)
                    combined.update(whois_data)
                    combined.update(ip_data)
                    combined.update(ssl_data)
                    results.append(combined)

                    progress.progress((i + 1) / len(df))
                    time.sleep(0.1)

                results_df = pd.DataFrame(results)
                out_file = "scan_resultaten.xlsx"
                results_df.to_excel(out_file, index=False)
                with open(out_file, "rb") as f:
                    st.download_button("📥 Download resultaten", f, file_name=out_file)
                st.dataframe(results_df)

# ----------------------
# Tab 2 – Beheer
# ----------------------
with tabs[1]:
    st.subheader("🔐 Beheermodus")

    # Veilig beheerwachtwoord uit extern bestand
    try:
        with open(ADMIN_PW_FILE, "r") as f:
            admin_pw = f.read().strip()
    except FileNotFoundError:
        st.error("⚠️ Beheer wachtwoordbestand niet gevonden! Maak ~/.beheer_pw aan.")
        st.stop()

    if "authenticated_admin" not in st.session_state:
        st.session_state.authenticated_admin = False

    if not st.session_state.authenticated_admin:
        password = st.text_input("Beheer wachtwoord:", type="password")
        if password == admin_pw:
            st.session_state.authenticated_admin = True
            st.success("Welkom beheerder!")
        else:
            st.stop()
    else:
        st.info("Je bent aangemeld als beheerder.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Controleer vereiste packages")
        if st.button("🔧 Controleer installatie"):
            st.info("Even geduld... controleren en installeren waar nodig...")
            output = run_install_checker()
            st.code(output)
            st.success("✅ Controle voltooid!")

    with col2:
        st.subheader("☁️ GitHub Synchronisatie")
        if st.button("⬆️ Push lokale updates naar GitHub"):
            st.info("Synchroniseren met GitHub...")
            try:
                message = push_to_github()
                st.success(message)
            except Exception as e:
                st.error(f"Fout bij push: {e}")

    st.markdown("---")
    st.subheader("🖥️ Serverbeheer – Streamlit-service")

    col3, col4, col5 = st.columns(3)
    with col3:
        if st.button("🟢 Start Streamlit"):
            out = run_command("sudo systemctl start streamlit-app.service")
            st.success("✅ Streamlit gestart.")
            st.code(out)

    with col4:
        if st.button("🟡 Herstart Streamlit"):
            out = run_command("sudo systemctl restart streamlit-app.service")
            st.info("♻️ Streamlit herstart.")
            st.code(out)

    with col5:
        if st.button("🔴 Stop Streamlit"):
            out = run_command("sudo systemctl stop streamlit-app.service")
            st.warning("🛑 Streamlit gestopt.")
            st.code(out)

    st.markdown("### 📊 Huidige status")
    status = run_command("systemctl is-active streamlit-app.service").strip()

    if status in ["active"]:
        st.success("✅ Streamlit draait momenteel.")
    elif status in ["activating", "reloading"]:
        st.info("⏳ Streamlit is aan het starten of herladen...")
    elif status in ["deactivating"]:
        st.warning("⚠️ Streamlit wordt momenteel gestopt...")
    else:
        st.error("🛑 Streamlit is gestopt of niet actief.")
    if st.button("🔄 Vernieuw status"):
        st.rerun()


# ----------------------
# Tab 3 – Meldingen
# ----------------------
with tabs[2]:
    st.subheader("📱 Meldingen – Telegram & Signal")
    telegram_token = os.path.exists(os.path.expanduser("~/.telegram_token"))
    signal_conf = os.path.exists(os.path.expanduser("~/.signal_config"))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔔 Telegram")
        if telegram_token:
            st.success("✅ Telegram geconfigureerd")
            if st.button("📨 Stuur testbericht (Telegram)"):
                msg = send_telegram_message("🔔 Testbericht van CyNiT Webinterface")
                st.info(msg)
        else:
            st.warning("⚠️ Geen Telegram-token gevonden. Zie `telegram_setup.md` in Help-tab.")

    with col2:
        st.markdown("### 💬 Signal")
        if signal_conf:
            st.success("✅ Signal-configuratie gevonden")
            if st.button("📨 Stuur testbericht (Signal)"):
                msg = send_signal_message("🔔 Testbericht van CyNiT Webinterface")
                st.info(msg)
        else:
            st.warning("⚠️ Geen Signal-configuratie gevonden. Zie `signal_setup.md` in Help-tab.")

# ----------------------
# Tab 4 – Help & Documentatie
# ----------------------
with tabs[3]:
    st.subheader("📘 Projectdocumentatie en handleidingen")

    help_files = glob.glob(os.path.join(REPO_DIR, "*.md")) + glob.glob(os.path.join(REPO_DIR, "docs", "*.md"))
    if not help_files:
        st.info("Geen documentatiebestanden gevonden. Plaats je .md bestanden in /docs/")
    else:
        selected = st.selectbox("📄 Kies een handleiding:", [os.path.basename(f) for f in help_files])
        file_path = next((p for p in help_files if selected in p), None)
        if file_path:
            with open(file_path, "r") as f:
                st.markdown(f.read(), unsafe_allow_html=False)

st.markdown("---")
st.caption("CyNiT © 2025 – Domein Scanner | Veilig beheerd en geautomatiseerd 🛡️")
