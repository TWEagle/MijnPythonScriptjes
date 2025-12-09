#!/usr/bin/env python3
import os
import subprocess
import dns.resolver
import pandas as pd
import requests
from datetime import datetime

# === Config ===
PI_USER = "tweagle"
REPO_DIR = f"/home/{PI_USER}/dns-scanner-webapp"
DOMAINS_FILE = os.path.join(REPO_DIR, "domeinen.xlsx")
MERKEN_FILE = os.path.join(REPO_DIR, "merken.txt")
TLD_CACHE = os.path.join(REPO_DIR, "tlds.txt")
LOG_FILE = os.path.join(REPO_DIR, "pi_scan.log")
TOKEN_FILE = os.path.expanduser("~/.github_token")
REMOTE_REPO = "https://github.com/TWEagle/dns-scanner-webapp.git"


def log(msg):
    """Schrijft bericht naar console en logbestand."""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run_cmd(cmd, check=False):
    """Voert shell-commando uit en logt output."""
    result = subprocess.run(cmd, shell=True, text=True,
                            capture_output=True)
    if result.stdout:
        log(result.stdout.strip())
    if result.stderr:
        log(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result


# === Stap 1 – Sync met GitHub ===
def git_sync():
    """Haalt laatste wijzigingen van GitHub binnen."""
    log("🔄 Sync met GitHub...")
    if not os.path.exists(TOKEN_FILE):
        log("❌ Geen GitHub-token gevonden!")
        return False

    with open(TOKEN_FILE) as f:
        token = f.read().strip()

    os.chdir(REPO_DIR)
    run_cmd(f"git config user.name 'dns-bot-pi'")
    run_cmd(f"git config user.email 'info@tweagle.eu'")
    run_cmd(f"git remote set-url origin https://{token}@github.com/TWEagle/dns-scanner-webapp.git")

    run_cmd("git fetch origin main", check=True)
    run_cmd("git reset --hard origin/main", check=True)
    run_cmd(f"git remote set-url origin {REMOTE_REPO}")
    log("✅ GitHub sync voltooid.")
    return True


# === Stap 2 – TLD’s laden ===
def load_tlds():
    """Haalt TLD-lijst van IANA (of gebruikt cache)."""
    if os.path.exists(TLD_CACHE) and (datetime.now().timestamp() -
                                      os.path.getmtime(TLD_CACHE) < 7 * 86400):
        with open(TLD_CACHE) as f:
            return [t.strip().lower() for t in f if t.strip()]

    try:
        resp = requests.get("https://data.iana.org/TLD/tlds-alpha-by-domain.txt", timeout=10)
        tlds = [line.strip().lower() for line in resp.text.splitlines()
                if line and not line.startswith("#")]
        with open(TLD_CACHE, "w") as f:
            f.write("\n".join(tlds))
        log(f"🌍 {len(tlds)} TLD’s geladen.")
        return tlds
    except Exception as e:
        log(f"⚠️ Kon TLD-lijst niet ophalen: {e}")
        return []


# === Stap 3 – Merken laden ===
def load_brands():
    """Leest merken.txt in."""
    if not os.path.exists(MERKEN_FILE):
        log("⚠️ merken.txt niet gevonden — geen merknamen om te controleren.")
        return []
    with open(MERKEN_FILE) as f:
        brands = [line.strip().lower() for line in f if line.strip()]
    log(f"📦 {len(brands)} merknamen geladen.")
    return brands


# === Stap 4 – Domeincontrole ===
def check_domain_exists(domain):
    """Controleert via DNS of domein bestaat."""
    try:
        dns.resolver.resolve(domain, "A")
        return True
    except dns.resolver.NXDOMAIN:
        return False
    except Exception:
        return False


# === Stap 5 – Resultaten bijwerken ===
def update_domains_file(new_domains):
    """Voegt nieuwe domeinen toe aan domeinen.xlsx."""
    if os.path.exists(DOMAINS_FILE):
        df = pd.read_excel(DOMAINS_FILE)
    else:
        df = pd.DataFrame(columns=["domein", "gevonden_op", "bron"])

    existing = set(df["domein"].str.lower())
    rows = []
    for d in new_domains:
        if d.lower() not in existing:
            rows.append({"domein": d, "gevonden_op": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "bron": "Pi merkcontrole"})

    if not rows:
        log("ℹ️ Geen nieuwe domeinen toegevoegd.")
        return

    new_df = pd.DataFrame(rows)
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_excel(DOMAINS_FILE, index=False)
    log(f"✅ {len(rows)} nieuwe domeinen toegevoegd aan domeinen.xlsx.")


# === Stap 6 – Push resultaten ===
def push_to_github():
    """Pusht nieuwe resultaten terug naar GitHub."""
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    os.chdir(REPO_DIR)
    run_cmd("git add domeinen.xlsx")
    run_cmd(f"git commit -m 'Auto-update domeinen.xlsx vanaf Pi - {datetime.now()}' || true")
    run_cmd(f"git push https://{token}@github.com/TWEagle/dns-scanner-webapp.git main")
    run_cmd(f"git remote set-url origin {REMOTE_REPO}")
    log("☁️ domeinen.xlsx gepusht naar GitHub.")


# === MAIN ===
if __name__ == "__main__":
    log("🚀 Start Pi merkdomeincontrole")

    if not git_sync():
        log("❌ GitHub sync mislukt. Script afgebroken.")
        exit(1)

    tlds = load_tlds()
    brands = load_brands()
    if not brands:
        log("⏹️ Geen merken om te controleren. Einde.")
        exit(0)

    discovered = []
    for brand in brands:
        for tld in ["be", "eu", "com", "net", "org"]:
            domain = f"{brand}.{tld}"
            if check_domain_exists(domain):
                log(f"✅ {domain} bestaat!")
                discovered.append(domain)
            else:
                log(f"❌ {domain} niet geregistreerd.")

    if discovered:
        update_domains_file(discovered)
        push_to_github()
    else:
        log("ℹ️ Geen actieve domeinen gevonden.")

    log("🏁 Pi scan afgerond.\n")
