from flask import Flask, request, redirect, url_for, render_template_string, session, flash
import os
from pathlib import Path
from datetime import datetime
import subprocess
import secrets
import string

try:
    import pyzipper
    HAS_PYZIPPER = True
except ImportError:
    HAS_PYZIPPER = False

# ===== CONFIG =====
OPENSSL_BIN = "openssl"   # pas aan als nodig
PASS_LENGTH = 24          # zet dit gelijk aan de lengte in jouw passgen.py
SECRET_KEY = "change-me-to-a-random-string"  # verander dit in iets unieks


app = Flask(__name__)
app.secret_key = SECRET_KEY


# ===== HELPERS =====

class CommandError(Exception):
    pass


def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CommandError(
            f"Commando gefaald: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


def generate_password(length=PASS_LENGTH) -> str:
    """Sterk wachtwoord zoals je passgen-script."""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%&*()-_=+;[{}]:,.<>?/"

    all_chars = lower + upper + digits + symbols

    pwd = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    pwd += [secrets.choice(all_chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


def validate_device_id(device_id: str) -> str:
    d = device_id.strip()
    if not d:
        raise ValueError("Toestelnummer mag niet leeg zijn.")
    return d


def build_cn(device_id: str, device_type: str) -> str:
    if device_type == "ip_phone":
        return f"{device_id}@gidphones.vlaanderen.be"
    else:
        return f"{device_id}.alfa.top.vlaanderen.be"


def init_device_dirs(base_dir: Path, date_str: str, device_id: str) -> dict:
    root = base_dir / date_str / device_id
    dirs = {
        "root": root,
        "keys": root / "keys",
        "csr": root / "csr",
        "certs": root / "certs",
        "exports": root / "exports",
        "logs": root / "logs",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


def generate_key_and_csr(device_id: str, device_type: str, dirs: dict):
    cn = build_cn(device_id, device_type)
    key_path = dirs["keys"] / f"{cn}.key.pem"
    csr_path = dirs["csr"] / f"{cn}.csr"

    subject = f"/CN={cn}"

    # key
    cmd_key = [OPENSSL_BIN, "genrsa", "-out", str(key_path), "2048"]
    run_cmd(cmd_key)

    # csr
    cmd_csr = [
        OPENSSL_BIN,
        "req",
        "-new",
        "-key",
        str(key_path),
        "-subj",
        subject,
        "-out",
        str(csr_path),
        "-sha256",
    ]
    run_cmd(cmd_csr)

    return key_path, csr_path, cn


def find_cert_for_device(device_cn: str, cert_dir: Path) -> Path | None:
    """
    We gaan ervan uit dat je je .cer/.crt/.pem in de 'certs' map zet.
    We zoeken eerst naar bestanden die de CN in de naam hebben,
    anders pakken we gewoon het meest recente bestand.
    """
    candidates = []
    # eerst poging: CN in bestandsnaam
    for ext in ("*.cer", "*.crt", "*.pem"):
        candidates.extend(cert_dir.glob(f"*{device_cn}*{ext[1:]}"))

    if not candidates:
        # fallback: alle cert-bestanden, recente eerst
        for ext in ("*.cer", "*.crt", "*.pem"):
            candidates.extend(cert_dir.glob(ext))

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def create_p12(device_cn: str, key_path: Path, cert_path: Path, password: str, dirs: dict) -> Path:
    exports = dirs["exports"]
    p12_path = exports / f"{device_cn}.p12"

    cmd = [
        OPENSSL_BIN,
        "pkcs12",
        "-export",
        "-inkey",
        str(key_path),
        "-in",
        str(cert_path),
        "-out",
        str(p12_path),
        "-passout",
        f"pass:{password}",
    ]
    run_cmd(cmd)
    return p12_path


def create_pem(device_cn: str, key_path: Path, cert_path: Path, dirs: dict) -> Path:
    exports = dirs["exports"]
    pem_path = exports / f"{device_cn}.pem"

    key = key_path.read_text()
    cert = cert_path.read_text()

    combined = key.rstrip() + "\n" + cert.strip() + "\n"
    pem_path.write_text(combined)
    return pem_path


def zip_pem(pem_files: list[Path], dirs: dict, password: str | None) -> Path | None:
    if not pem_files:
        return None
    exports = dirs["exports"]
    zip_path = exports.parent / "voica1_phones.zip"

    if not HAS_PYZIPPER or password is None:
        # gewone zip zonder sterke encryptie
        import zipfile
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in pem_files:
                zf.write(f, arcname=f.name)
        return zip_path

    with pyzipper.AESZipFile(zip_path, "w",
                             compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode("utf-8"))
        zf.setencryption(pyzipper.WZ_AES, nbits=128)
        for f in pem_files:
            zf.write(f, arcname=f.name)

    return zip_path


def build_devices_string(devices: list[str]) -> str:
    if not devices:
        return ""
    if len(devices) == 1:
        return devices[0]
    return "; ".join(devices[:-1]) + f" & {devices[-1]}"


# ===== TEMPLATES =====

INDEX_TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>CyNiT VOICA1 Tool</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#111; color:#eee; padding:20px; }
    .card { max-width: 900px; margin: 0 auto; background:#1e1e1e; padding:20px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,0.6);}
    label { display:block; margin-top:12px; font-weight:600; }
    input[type=text], textarea, select {
      width:100%; padding:8px 10px; border-radius:8px; border:1px solid #444; background:#111; color:#eee;
    }
    textarea { min-height:90px; font-family:monospace; }
    .btn { display:inline-block; margin-top:16px; padding:8px 16px; border-radius:999px; border:none;
           background:#facc15; color:#000; font-weight:700; cursor:pointer; }
    .btn:hover { background:#eab308; }
    .muted { color:#aaa; font-size:0.9em; }
    .row { display:flex; gap:16px; flex-wrap:wrap; }
    .col { flex:1 1 250px; }
    .flash { background:#7f1d1d; color:#fecaca; padding:8px 12px; border-radius:8px; margin-bottom:8px; }
    code { background:#000; padding:2px 4px; border-radius:4px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>CyNiT VOICA1 Tool</h1>
    <p class="muted">Genereer per device een eigen key + CSR, met één batch-wachtwoord voor alle .p12 / .pem.</p>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}
          <div class="flash">{{ m }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method="post" action="{{ url_for('generate') }}">
      <label>Basismap op server (bv. <code>C:\\VOICA1</code>)</label>
      <input type="text" name="base_dir" value="{{ base_dir or '' }}" required>

      <div class="row">
        <div class="col">
          <label>Type devices</label>
          <select name="device_type">
            <option value="pc" {% if device_type == 'pc' %}selected{% endif %}>PC / VM / Mac ( *.alfa.top.vlaanderen.be )</option>
            <option value="ip_phone" {% if device_type == 'ip_phone' %}selected{% endif %}>IP-telefoon ( Pxxxxx@gidphones.vlaanderen.be )</option>
          </select>
        </div>
      </div>

      <label>Devices (één per lijn)</label>
      <textarea name="devices" placeholder="S343880&#10;VM123456&#10;P602233">{{ devices or '' }}</textarea>
      <p class="muted">
        Elke lijn = één toestelnummer. Voor IP-telefoons: P-nummer (bv. <code>P602233</code>).<br>
        Voor PCs: S-nummer / VM-naam / M-naam / 7 cijfers.
      </p>

      <button type="submit" class="btn">Stap 1 – Maak key + CSR</button>
    </form>
  </div>
</body>
</html>
"""

STEP1_TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>VOICA1 – Stap 1</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#111; color:#eee; padding:20px;}
    .card { max-width: 1000px; margin: 0 auto; background:#1e1e1e; padding:20px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,0.6);}
    pre, code { background:#000; padding:6px 8px; border-radius:6px; overflow-x:auto; }
    .btn { display:inline-block; margin-top:16px; padding:8px 16px; border-radius:999px; border:none;
           background:#facc15; color:#000; font-weight:700; cursor:pointer; }
    .btn:hover { background:#eab308; }
    .muted { color:#aaa; font-size:0.9em; }
    .list { margin-top:10px; }
    .list li { margin-bottom:4px; }
  </style>
  <script>
    function copyText(id) {
      const el = document.getElementById(id);
      el.select();
      el.setSelectionRange(0, 99999);
      document.execCommand("copy");
    }
  </script>
</head>
<body>
  <div class="card">
    <h1>Stap 1 – Keys &amp; CSRs aangemaakt</h1>

    <p><strong>Batch-datum:</strong> {{ date_str }}<br>
       <strong>Basismap:</strong> {{ base_dir }}</p>

    <h2>Batch-wachtwoord</h2>
    <p class="muted">Dit wachtwoord wordt gebruikt voor alle .p12 (PC) en evt. ZIP (IP-telefoon) in deze batch.</p>
    <textarea id="pwd" style="width:100%;font-family:monospace;" rows="1" readonly>{{ password }}</textarea>
    <button class="btn" onclick="copyText('pwd')">Kopieer wachtwoord</button>

    <h2>Devices</h2>
    <ul class="list">
      {% for d in devices %}
        <li>{{ d }} → CN: {{ cns[d] }}</li>
      {% endfor %}
    </ul>

    <h3>Devices-string voor je mails</h3>
    <textarea id="devs" style="width:100%;font-family:monospace;" rows="2" readonly>{{ devices_str }}</textarea>
    <button class="btn" onclick="copyText('devs')">Kopieer devices-string</button>

    <h2>Waar staan de CSR's?</h2>
    <p class="muted">
      Voor elk device is er een submap:<br>
      <code>{{ base_dir }} / {{ date_str }} / DEVICE / csr / CN.csr</code>
    </p>

    <ul class="list">
      {% for d in devices %}
        <li>{{ d }} → {{ csr_paths[d] }}</li>
      {% endfor %}
    </ul>

    <h2>Volgende stap (manueel in AEG)</h2>
    <ol>
      <li>Open de AEG webtool (Request Certificate).</li>
      <li>Gebruik voor elk device de bijbehorende CSR (*.csr) uit de map hierboven.</li>
      <li>Download het certificaat per device en bewaar het in <code>.../DEVICE/certs/</code>.</li>
      <li>Naam van het cert mag vrij zijn, maar liefst herkenbaar.</li>
    </ol>

    <form method="post" action="{{ url_for('process') }}">
      <button type="submit" class="btn">Stap 2 – Verwerk gedownloade certificaten</button>
    </form>

    <p class="muted" style="margin-top:16px;">
      Je mag deze pagina open laten terwijl je in AEG werkt; klik op "Stap 2" als alle certificaten in de <code>certs</code>-mappen staan.
    </p>
  </div>
</body>
</html>
"""

STEP2_TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>VOICA1 – Resultaat</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#111; color:#eee; padding:20px;}
    .card { max-width: 1000px; margin: 0 auto; background:#1e1e1e; padding:20px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,0.6);}
    ul { margin-left:20px; }
    .ok { color:#bbf7d0; }
    .err { color:#fecaca; }
    textarea { width:100%; font-family:monospace; }
    .btn { display:inline-block; margin-top:16px; padding:8px 16px; border-radius:999px; border:none;
           background:#facc15; color:#000; font-weight:700; cursor:pointer; }
    .btn:hover { background:#eab308; }
    .muted { color:#aaa; font-size:0.9em; }
  </style>
  <script>
    function copyText(id) {
      const el = document.getElementById(id);
      el.select();
      el.setSelectionRange(0, 99999);
      document.execCommand("copy");
    }
  </script>
</head>
<body>
  <div class="card">
    <h1>Stap 2 – Certificaten verwerkt</h1>
    <p><strong>Type:</strong> {{ 'PC / .p12' if device_type == 'pc' else 'IP-telefoon / .pem' }}</p>

    <h2>Resultaten per device</h2>
    <ul>
    {% for r in results %}
      <li>
        {% if r.ok %}
          <span class="ok">[OK]</span>
        {% else %}
          <span class="err">[FOUT]</span>
        {% endif %}
        {{ r.device }} – {{ r.message }}
      </li>
    {% endfor %}
    </ul>

    {% if zip_path %}
      <h3>ZIP-bestand</h3>
      <p>{{ zip_path }}</p>
      <p class="muted">Als pyzipper geïnstalleerd is, is dit met AES-128 versleuteld; anders gewone ZIP.</p>
    {% endif %}

    <h2>Devices-string</h2>
    <textarea id="devs" rows="2" readonly>{{ devices_str }}</textarea>
    <button class="btn" onclick="copyText('devs')">Kopieer devices-string</button>

    <h2>Batch-wachtwoord</h2>
    <textarea id="pwd" rows="1" readonly>{{ password }}</textarea>
    <button class="btn" onclick="copyText('pwd')">Kopieer wachtwoord</button>

    <p class="muted" style="margin-top:16px;">
      Gebruik deze twee velden in je Espanso-snippets: <code>certmail</code>, <code>pkiots</code>, <code>pkiwa</code>, ...<br>
      Daarna kun je volgens je proces de .p12/.pem/.zip mailen en het ticket afsluiten.
    </p>

    <form method="get" action="{{ url_for('index') }}">
      <button class="btn" type="submit">Nieuwe batch starten</button>
    </form>
  </div>
</body>
</html>
"""


# ===== ROUTES =====

@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        INDEX_TEMPLATE,
        base_dir="",
        device_type="pc",
        devices=""
    )


@app.route("/generate", methods=["POST"])
def generate():
    base_dir_str = request.form.get("base_dir", "").strip()
    device_type = request.form.get("device_type", "pc")
    devices_raw = request.form.get("devices", "")

    if not base_dir_str:
        flash("Basismap is verplicht.")
        return redirect(url_for("index"))

    base_dir = Path(base_dir_str)
    base_dir.mkdir(parents=True, exist_ok=True)

    devices = [line.strip() for line in devices_raw.splitlines() if line.strip()]
    if not devices:
        flash("Voer minstens één device in.")
        return redirect(url_for("index"))

    date_str = datetime.now().strftime("%Y%m%d")
    password = generate_password()

    cns = {}
    csr_paths = {}

    for dev in devices:
        try:
            dev_id = validate_device_id(dev)
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("index"))

        dirs = init_device_dirs(base_dir, date_str, dev_id)
        try:
            key_path, csr_path, cn = generate_key_and_csr(dev_id, device_type, dirs)
        except CommandError as e:
            flash(f"Fout bij aanmaken key/CSR voor {dev_id}: {e}")
            return redirect(url_for("index"))

        cns[dev_id] = cn
        csr_paths[dev_id] = str(csr_path)

    devices_str = build_devices_string(devices)

    # info in session voor stap 2
    session["voica1"] = {
        "base_dir": str(base_dir),
        "device_type": device_type,
        "devices": devices,
        "date_str": date_str,
        "password": password,
    }

    return render_template_string(
        STEP1_TEMPLATE,
        base_dir=str(base_dir),
        device_type=device_type,
        devices=devices,
        cns=cns,
        csr_paths=csr_paths,
        date_str=date_str,
        password=password,
        devices_str=devices_str,
    )


@app.route("/process", methods=["POST"])
def process():
    data = session.get("voica1")
    if not data:
        flash("Geen open batch gevonden. Start opnieuw.")
        return redirect(url_for("index"))

    base_dir = Path(data["base_dir"])
    device_type = data["device_type"]
    devices = data["devices"]
    date_str = data["date_str"]
    password = data["password"]

    results = []
    pem_files = []
    any_dirs_for_zip = None  # voor ip-phone zip locatie

    for dev in devices:
        dev_id = dev
        dirs = init_device_dirs(base_dir, date_str, dev_id)  # bestaat al
        cn = build_cn(dev_id, device_type)

        key_path = dirs["keys"] / f"{cn}.key.pem"
        cert_path = find_cert_for_device(cn, dirs["certs"])

        if not cert_path:
            results.append({
                "device": dev_id,
                "ok": False,
                "message": f"Geen certificaat gevonden in {dirs['certs']}"
            })
            continue

        try:
            if device_type == "pc":
                out_path = create_p12(cn, key_path, cert_path, password, dirs)
                msg = f".p12 aangemaakt: {out_path}"
            else:
                pem_path = create_pem(cn, key_path, cert_path, dirs)
                pem_files.append(pem_path)
                any_dirs_for_zip = dirs
                msg = f"PEM aangemaakt: {pem_path}"
            results.append({"device": dev_id, "ok": True, "message": msg})
        except CommandError as e:
            results.append({"device": dev_id, "ok": False, "message": str(e)})

    zip_path = None
    if device_type == "ip_phone" and any_dirs_for_zip and pem_files:
        zip_path = zip_pem(pem_files, any_dirs_for_zip, password)
        if zip_path:
            results.append({
                "device": "ALLE IP-TOESTELLEN",
                "ok": True,
                "message": f"ZIP gemaakt: {zip_path}"
            })

    devices_str = build_devices_string(devices)

    return render_template_string(
        STEP2_TEMPLATE,
        device_type=device_type,
        results=results,
        zip_path=str(zip_path) if zip_path else None,
        devices_str=devices_str,
        password=password,
    )


if __name__ == "__main__":
    # run lokaal op bv. poort 5555, zoals je andere tools
    app.run(host="127.0.0.1", port=5445, debug=True)
