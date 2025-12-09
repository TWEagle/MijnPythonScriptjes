#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CyNiT – Merk- en domeinscanner voor Raspberry Pi
- Controleert merknamen over alle TLD’s
- Vergelijkt met vorige resultaten
- Synchroniseert automatisch met GitHub (pull + push)
- Houdt domeinen.xlsx up-to-date
"""

import os
import sys
import subprocess
from datetime import datetime

# === Auto-install checker ===
REQUIRED_PACKAGES = ["dnspython", "pandas", "requests", "openpyxl"]

def ensure_dependencies():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg if pkg != "dnspython" else "dns")
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"📦 Installeer ontbrekende packages: {', '.join(missing)} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("✅ Installatie voltooid!\n")
    else:
        print("✅ Alle vereisten aanwezig.\n")

ensure_dependencies()

# === Imports ===
import dns.resolver
import pandas as pd
import requests

# === Paden ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MERKEN_FILE = os.path.join(BASE_DIR, "merken.txt")
DOMAINS_FILE = os.path.join(BASE_DIR, "domeinen.xlsx")
TOKEN_FILE = os.path.expanduser("~/.github_token")
TLD_CACHE = os.path.join(BASE_DIR, "tlds.txt")

os.makedirs(RESULTS_DIR, exist_ok=True)

# === GitHub functies ===
def github_pull():
    """Haalt laatste updates op van GitHub."""
    if not os.path.exists(TOKEN_FILE):
        print("⚠️ Geen GitHub-token gevonden, pull overgeslagen.")
        return
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()

        os.chdir(BASE_DIR)
        remote_url = f"https://{token}@github.com/TWEagle/dns-scanner-webapp.git"
        subprocess.run(["git", "config", "user.name", "pi-bot"], check=True)
        subprocess.run(["git", "config", "user.email", "info@tweagle.eu"], check=True)
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
        print("🔄 Ophalen van laatste GitHub-wijzigingen...")
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=False)
        print("✅ Repository bijgewerkt met laatste wijzigingen.\n")
    except Exception as e:
        print(f"⚠️ Fout bij GitHub-pull: {e}")

def github_push():
    """Pusht resultaten en wijzigingen terug naar GitHub."""
    if not os.path.exists(TOKEN_FILE):
        print("⚠️ Geen GitHub-token gevonden, push overgeslagen.")
        return
    try:
        with open(TOKEN_FILE) as f:
            token = f.read().strip()

        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "results/", "domeinen.xlsx"], check=True)
        msg = f"Pi merkdomeinscan {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", msg], check=False)
        remote_url = f"https://{token}@github.com/TWEagle/dns-scanner-webapp.git"
        subprocess.run(["git", "push", remote_url, "main"], check=True)
        print("☁️ Resultaten geüpload naar GitHub.\n")
    except Exception as e:
        print(f"⚠️ Push naar GitHub mislukt: {e}")

# === DNS-scan functies ===
def load_tlds():
    if os.path.exists(TLD_CACHE) and (datetime.now().timestamp() - os.path.getmtime(TLD_CACHE) < 7 * 86400):
        with open(TLD_CACHE) as f:
            return [t.strip().lower() for t in f if t.strip()]
    try:
        print("🌍 Downloaden van actuele TLD-lijst...")
        resp = requests.get("https://data.iana.org/TLD/tlds-alpha-by-domain.txt", timeout=10)
        resp.raise_for_status()
        tlds = [l.strip().lower() for l in resp.text.splitlines() if l and not l.startswith("#")]
        with open(TLD_CACHE, "w") as f:
            f.write("\n".join(tlds))
        print(f"✅ TLD-lijst opgehaald ({len(tlds)} extensies).")
        return tlds
    except Exception as e:
        print(f"⚠️ Fout bij ophalen TLD’s: {e}")
        return []


def load_brands():
    if not os.path.exists(MERKEN_FILE):
        print("⚠️ merken.txt niet gevonden.")
        return []
    with open(MERKEN_FILE) as f:
        brands = [line.strip().lower() for line in f if line.strip()]
    print(f"📦 {len(brands)} merknamen geladen.")
    return brands


def check_domain_exists(domain):
    try:
        dns.resolver.resolve(domain, "A")
        return True
    except dns.resolver.NXDOMAIN:
        return False
    except Exception:
        return False


def get_latest_result_file():
    files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("merkcheck_") and f.endswith(".xlsx")]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(RESULTS_DIR, files[0])


def compare_with_previous(new_df):
    last_file = get_latest_result_file()
    if not last_file:
        print("🆕 Eerste scan – geen vorige resultaten.")
        return new_df, None
    try:
        old_df = pd.read_excel(last_file)
        merged = new_df.merge(old_df, on=["Merk", "Domein"], how="left", indicator=True)
        new_domains = merged[merged["_merge"] == "left_only"]
        if not new_domains.empty:
            print(f"🚨 Nieuwe domeinen ontdekt: {len(new_domains)}")
            print(new_domains[["Merk", "Domein"]])
        else:
            print("✅ Geen nieuwe domeinen sinds vorige run.")
        return new_df, new_domains
    except Exception as e:
        print(f"⚠️ Vergelijking mislukt: {e}")
        return new_df, None


def append_to_main_excel(new_domains):
    if new_domains is None or new_domains.empty:
        print("ℹ️ Geen nieuwe domeinen om toe te voegen.")
        return
    try:
        if os.path.exists(DOMAINS_FILE):
            df_main = pd.read_excel(DOMAINS_FILE)
        else:
            df_main = pd.DataFrame(columns=["domein"])
        existing = df_main["domein"].astype(str).tolist()
        to_add = [d for d in new_domains["Domein"].tolist() if d not in existing]
        if not to_add:
            print("✅ Geen nieuwe domeinen om toe te voegen (allemaal aanwezig).")
            return
        updated = pd.concat([df_main, pd.DataFrame({"domein": to_add})], ignore_index=True)
        updated.to_excel(DOMAINS_FILE, index=False)
        print(f"✅ {len(to_add)} nieuwe domeinen toegevoegd aan domeinen.xlsx.")
    except Exception as e:
        print(f"⚠️ Fout bij bijwerken domeinen.xlsx: {e}")


def run_brand_scan():
    github_pull()  # eerst altijd repo updaten

    brands = load_brands()
    if not brands:
        print("⏹️ Geen merknamen om te controleren.")
        return

    tlds = load_tlds()
    if not tlds:
        print("⏹️ Geen TLD’s beschikbaar.")
        return

    results = []
    for brand in brands:
        print(f"\n🔎 Controleren merk: {brand}")
        for tld in tlds:
            domain = f"{brand}.{tld}"
            if check_domain_exists(domain):
                print(f"✅ {domain} bestaat.")
                results.append({"Merk": brand, "Domein": domain, "Bestaat": "Ja"})

    if not results:
        print("ℹ️ Geen actieve domeinen gevonden.")
        return

    df = pd.DataFrame(results)
    df, new_domains = compare_with_previous(df)

    today = datetime.now().strftime("%Y-%m-%d")
    out_file = os.path.join(RESULTS_DIR, f"merkcheck_{today}.xlsx")
    df.to_excel(out_file, index=False)
    print(f"\n💾 Resultaten opgeslagen als: {out_file}")

    append_to_main_excel(new_domains)
    github_push()


if __name__ == "__main__":
    run_brand_scan()
