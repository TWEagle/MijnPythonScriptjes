import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import boto3

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# =========================
#  BASIS-CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "run_log.txt"
PROGRESS_FILE = BASE_DIR / "progress.json"
LOCAL_SCAN_SCRIPT = BASE_DIR / "local_scan.py"

# Venv-python (zoals je nu ook gebruikt)
VENV_PYTHON = BASE_DIR / "venv" / "bin" / "python3"
if not VENV_PYTHON.exists():
    # fallback
    VENV_PYTHON = Path(sys.executable)

# S3-config
AWS_BUCKET = os.getenv("AWS_BUCKET", "dns-scanner-data")
FILES_TO_UPLOAD = ["domeinen.txt", "scan_log.txt", "progress.json"]

# =========================
#  HULPFUNCTIES
# =========================

def log(msg: str) -> None:
    """Schrijf naar console + logbestand."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Logging mag nooit het script doen crashen
        pass


def load_env() -> None:
    """Laad .env uit de projectroot (indien aanwezig)."""
    env_path = BASE_DIR / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)
        log("📦 .env variabelen geladen.")
    else:
        if not env_path.exists():
            log("ℹ️ Geen .env gevonden, gebruik alleen OS environment.")
        else:
            log("ℹ️ python-dotenv niet geïnstalleerd; .env wordt niet automatisch geladen.")


def get_status_interval_minutes() -> int:
    """Lees STATUS_INTERVAL_MINUTES uit .env, default = 60."""
    raw = os.getenv("STATUS_INTERVAL_MINUTES", "60")
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError()
        return value
    except Exception:
        log(f"⚠️ STATUS_INTERVAL_MINUTES='{raw}' ongeldig, val terug op 60.")
        return 60


def detect_ngrok_ssh() -> str | None:
    """
    Probeer de huidige ngrok TCP-tunnel voor SSH te detecteren via 127.0.0.1:4040.
    Retourneert bv. 'tcp tcp://0.tcp.eu.ngrok.io:19239 → localhost:22' of None.
    """
    if requests is None:
        log("ℹ️ requests niet beschikbaar, ngrok-detectie wordt overgeslagen.")
        return None

    api_url = "http://127.0.0.1:4040/api/tunnels"
    try:
        resp = requests.get(api_url, timeout=2)
        resp.raise_for_status()
        data = resp.json()

        tunnels = data.get("tunnels", [])
        for t in tunnels:
            pub = t.get("public_url", "")
            proto = t.get("proto", "")
            cfg = t.get("config", {})
            addr = cfg.get("addr", "")
            if proto == "tcp" and addr.endswith(":22"):
                # Mooie weergave
                return f"tcp {pub} → {addr}"
    except Exception as e:
        log(f"ℹ️ ngrok-detectie mislukt: {e}")

    return None


def find_and_kill_old_processes():
    """
    Zoek naar oude run_pi_scan.py / local_scan.py processen en kill ze,
    behalve het huidige PID.
    """
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:
        log(f"⚠️ Kon ps aux niet uitvoeren: {e}")
        return

    current_pid = os.getpid()
    lines = result.stdout.splitlines()

    for line in lines:
        if "run_pi_scan.py" in line or "local_scan.py" in line:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                continue

            if pid == current_pid:
                continue

            # Kill het proces
            try:
                subprocess.run(["kill", "-9", str(pid)], check=False)
                if "run_pi_scan.py" in line:
                    log(f"➡️ Kill oude run_pi_scan.py (PID {pid})")
                elif "local_scan.py" in line:
                    log(f"➡️ Kill local_scan.py (PID {pid})")
            except Exception as e:
                log(f"⚠️ Kon proces {pid} niet killen: {e}")


# =========================
#  WEEKLY / AGE-BASED RESET
# =========================

def maybe_reset_progress():
    """
    Reset-logica:
    - Als WEEKLY_RESET=1 in environment: altijd progress.json verwijderen.
    - Als progress.json ouder is dan 36 uur: ook progress.json verwijderen.
    TXT / XLSX / CSV laten we ongemoeid; local_scan maakt zelf zijn dumps.
    """
    reason = None

    # 1) Force reset via weekly cron
    if os.getenv("WEEKLY_RESET") == "1":
        reason = "WEEKLY_RESET=1 (wekelijkse scan via cron)"

    # 2) Automatische reset bij oude progress.json
    elif PROGRESS_FILE.exists():
        try:
            mtime = datetime.fromtimestamp(PROGRESS_FILE.stat().st_mtime)
            age_hours = (datetime.now() - mtime).total_seconds() / 3600.0
            if age_hours > 36:
                reason = f"progress.json is {age_hours:.1f} uur oud (>36u)"
        except Exception as e:
            log(f"[INIT] ⚠️ Kon leeftijd van progress.json niet bepalen: {e}")

    if not reason:
        # Niets te resetten
        return

    log(f"[INIT] 🔁 Progress reset geactiveerd: {reason}")

    try:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
            log("[INIT] 🧹 Oude progress.json verwijderd.")
        else:
            log("[INIT] ℹ️ Geen progress.json gevonden om te verwijderen.")
    except Exception as e:
        log(f"[INIT] ⚠️ Kon progress.json niet verwijderen: {e}")


# =========================
#  HELPER: STATUS
# =========================

def print_status_summary():
    """
    Helper om snel de huidige scannerstatus te inspecteren.

    Gebruik:
      python3 run_pi_scan.py --status

    Toont:
    - of progress.json bestaat
    - hoe oud hij is
    - of bij een volgende run een reset zou gebeuren
    - wanneer de wekelijkse cron-run is gepland (fixed: maandag 06:00)
    """
    log("ℹ️ Status-overzicht (helper)")

    if PROGRESS_FILE.exists():
        mtime = datetime.fromtimestamp(PROGRESS_FILE.stat().st_mtime)
        age = datetime.now() - mtime
        age_hours = age.total_seconds() / 3600.0
        print(f"📄 progress.json bestaat: {PROGRESS_FILE}")
        print(f"   Laatst gewijzigd : {mtime}")
        print(f"   Leeftijd         : {age_hours:.1f} uur")
        auto_reset = age_hours > 36
        print(f"   >36u?            : {'JA' if auto_reset else 'nee'}")
    else:
        print("📄 progress.json bestaat NIET (volgende run = verse start).")

    weekly_flag = os.getenv("WEEKLY_RESET")
    print(f"\nEnv WEEKLY_RESET    : {weekly_flag!r} (alleen relevant als je deze zelf zet bij run)")
    print("Wekelijkse cron-run : elke maandag om 06:00 (zoals ingesteld in crontab).")

    # Simuleer of er een reset zou gebeuren
    will_reset = False
    if weekly_flag == "1":
        will_reset = True
    elif PROGRESS_FILE.exists():
        mtime = datetime.fromtimestamp(PROGRESS_FILE.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600.0
        if age_hours > 36:
            will_reset = True

    print(f"\nBij een volgende run via dit script zou resetten: {'JA' if will_reset else 'nee'}")


# =========================
#  LOCAL SCAN STARTEN
# =========================

def run_local_scan():
    """
    Start local_scan.py via de venv Python.
    """
    status_interval = get_status_interval_minutes()
    log(f"⏱️ Status-notificaties elke {status_interval} minuut/minuten.")

    ngrok_info = detect_ngrok_ssh()
    if ngrok_info:
        log(f"🌐 ngrok gedetecteerd: {ngrok_info}")
    else:
        log("🌐 ngrok niet gedetecteerd of niet actief.")

    cmd = [str(VENV_PYTHON), str(LOCAL_SCAN_SCRIPT)]
    log(f"▶️ Start lokale scan via: {' '.join(cmd)}")

    try:
        # local_scan.py doet zelf dashboard, notificaties en FULL dump
        subprocess.run(cmd, check=True)
        log("ℹ️ local_scan.py geëindigd met exit code 0")
    except subprocess.CalledProcessError as e:
        log(f"⚠️ local_scan.py gaf een fout (exit code {e.returncode})")
    except Exception as e:
        log(f"⚠️ Fout bij starten van local_scan.py: {e}")


# =========================
#  S3 UPLOAD
# =========================

def upload_to_s3():
    """
    Upload geselecteerde bestanden naar S3 (indien credentials aanwezig).
    """
    log(f"☁️ Upload naar S3 bucket: {AWS_BUCKET}")
    try:
        s3 = boto3.client("s3")
    except Exception as e:
        log(f"⚠️ Kon S3 client niet initialiseren: {e}")
        return

    for file in FILES_TO_UPLOAD:
        path = BASE_DIR / file
        if path.exists():
            try:
                log(f"⬆️ Upload {file} naar s3://{AWS_BUCKET}/{file}")
                s3.upload_file(str(path), AWS_BUCKET, file)
            except Exception as e:
                log(f"⚠️ Upload mislukt voor {file}: {e}")
        else:
            log(f"⏩ Bestand niet gevonden, overslaan: {file}")


# =========================
#  NOTIFICATIE BIJ EIND
# =========================

def send_final_notification():
    """
    Stuur een eindnotificatie via notify.py (als die aanwezig is).
    """
    try:
        import notify  # type: ignore
    except Exception as e:
        log(f"ℹ️ notify.py niet beschikbaar ({e}), sla eindnotificatie over.")
        return

    # Bouw een beknopte samenvatting; local_scan stuurt zelf ook al detailmeldingen
    msg_lines = [
        "🎉 CyNiT DNS Scan afgerond (launcher)",
        "",
        f"- Tijdstip: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Bucket: {AWS_BUCKET}",
        "",
        "Dit is de afsluitende melding van run_pi_scan.py.",
    ]
    message = "\n".join(msg_lines)

    log("📨 Verstuur eindnotificatie...")
    try:
        notify.send_notifications(message)
        log("📤 Eindnotificatie verzonden.")
    except Exception as e:
        log(f"⚠️ Eindnotificatie mislukt: {e}")


# =========================
#  MAIN
# =========================

def main():
    start_time = time.time()
    log("🚀 CyNiT DNS Scanner launcher gestart.")

    load_env()
    find_and_kill_old_processes()
    maybe_reset_progress()

    run_local_scan()
    upload_to_s3()
    send_final_notification()

    duration = round(time.time() - start_time, 2)
    log(f"🏁 Launcher klaar in {duration} seconden.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CyNiT DNS Scanner launcher (run_pi_scan.py)")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Toon status-overzicht (progress.json leeftijd, reset-gedrag, cron-info) en stop.",
    )
    args = parser.parse_args()

    if args.status:
        print_status_summary()
        sys.exit(0)

    main()
