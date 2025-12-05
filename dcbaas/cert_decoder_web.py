#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, request, render_template_string

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec
from cryptography.x509.oid import NameOID


# ---- Zelfde decode helpers als in GUI (iets ingekort) ----

def load_cert_or_csr(data: bytes):
    text = None
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        pass

    if text and "BEGIN CERTIFICATE REQUEST" in text:
        try:
            csr = x509.load_pem_x509_csr(data)
            return "csr", csr
        except Exception:
            pass

    if text and "BEGIN CERTIFICATE" in text:
        try:
            cert = x509.load_pem_x509_certificate(data)
            return "cert", cert
        except Exception:
            pass

    try:
        cert = x509.load_der_x509_certificate(data)
        return "cert", cert
    except Exception:
        pass

    try:
        csr = x509.load_der_x509_csr(data)
        return "csr", csr
    except Exception:
        pass

    raise ValueError("Bestand is geen geldige X.509 certificate of CSR (PEM/DER).")


def get_name_attr(name: x509.Name, oid) -> str:
    try:
        attrs = name.get_attributes_for_oid(oid)
        if attrs:
            return attrs[0].value
    except Exception:
        pass
    return "-"


def subject_fields(name: x509.Name) -> dict:
    return {
        "Common Name":         get_name_attr(name, NameOID.COMMON_NAME),
        "emailAddress":        get_name_attr(name, NameOID.EMAIL_ADDRESS),
        "Organizational Unit": get_name_attr(name, NameOID.ORGANIZATIONAL_UNIT_NAME),
        "Organization":        get_name_attr(name, NameOID.ORGANIZATION_NAME),
        "Locality":            get_name_attr(name, NameOID.LOCALITY_NAME),
        "State or Province":   get_name_attr(name, NameOID.STATE_OR_PROVINCE_NAME),
        "Country":             get_name_attr(name, NameOID.COUNTRY_NAME),
    }


def issuer_fields(issuer: x509.Name) -> dict:
    return {
        "Issuer Common Name":      get_name_attr(issuer, NameOID.COMMON_NAME),
        "Issuer emailAddress":     get_name_attr(issuer, NameOID.EMAIL_ADDRESS),
        "Issuer Organization":     get_name_attr(issuer, NameOID.ORGANIZATION_NAME),
        "Issuer Locality":         get_name_attr(issuer, NameOID.LOCALITY_NAME),
        "Issuer State or Province": get_name_attr(issuer, NameOID.STATE_OR_PROVINCE_NAME),
        "Issuer Country":          get_name_attr(issuer, NameOID.COUNTRY_NAME),
    }


def format_name(name: x509.Name) -> str:
    parts = []
    for rdn in name.rdns:
        for attr in rdn:
            parts.append(f"{attr.oid._name}={attr.value}")
    return ", ".join(parts) if parts else "-"


def get_key_info(public_key):
    if isinstance(public_key, rsa.RSAPublicKey):
        return "RSA", str(public_key.key_size)
    if isinstance(public_key, dsa.DSAPublicKey):
        return "DSA", str(public_key.key_size)
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        try:
            size = public_key.key_size
        except Exception:
            size = "-"
        return f"EC ({public_key.curve.name})", str(size)
    return public_key.__class__.__name__, "-"


def get_signature_algorithm(obj) -> str:
    try:
        sig_hash = obj.signature_hash_algorithm.name
    except Exception:
        sig_hash = "-"

    algo_name = "-"
    try:
        algo_name = obj.signature_algorithm_oid._name
    except Exception:
        pass

    if algo_name == "-":
        return sig_hash if sig_hash != "-" else "-"
    if sig_hash != "-":
        return f"{algo_name} ({sig_hash})"
    return algo_name


def compute_thumbprint(cert: x509.Certificate) -> str:
    try:
        fp = cert.fingerprint(hashes.SHA1())
        return fp.hex().upper()
    except Exception:
        return "-"


def decode_for_web(data: bytes):
    obj_type, obj = load_cert_or_csr(data)

    subj = subject_fields(obj.subject)

    if obj_type == "cert":
        issuer_map = issuer_fields(obj.issuer)
        valid_from = obj.not_valid_before.isoformat()
        valid_to = obj.not_valid_after.isoformat()
        serial = hex(obj.serial_number).upper().replace("X", "x")
        thumb = compute_thumbprint(obj)
        issuer_str = format_name(obj.issuer)
    else:
        issuer_map = None
        valid_from = "-"
        valid_to = "-"
        serial = "-"
        thumb = "-"
        issuer_str = "-"

    pub = obj.public_key()
    key_algo, key_size = get_key_info(pub)
    sig_algo = get_signature_algorithm(obj)

    props = {
        "Subject":        format_name(obj.subject),
        "Issuer":         issuer_str,
        "Valid From":     valid_from,
        "Valid To":       valid_to,
        "Key Size":       key_size,
        "Key Algorithm":  key_algo,
        "Sig. Algorithm": sig_algo,
        "Serial Number":  serial,
        "Thumbprint":     thumb,
    }

    return obj_type, subj, issuer_map, props


# ---- Flask app ----

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Certificate / CSR Decoder</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { margin-bottom: 10px; }
    table { border-collapse: collapse; margin-bottom: 20px; min-width: 400px; }
    th, td { border: 1px solid #aaa; padding: 4px 8px; }
    th { background: #eee; text-align: left; }
    .section-title { margin-top: 20px; }
    .error { color: red; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Certificate / CSR Decoder</h1>
  <form method="post" enctype="multipart/form-data">
    <label>Upload certificaat of CSR: 
      <input type="file" name="file">
    </label>
    <button type="submit">Decode</button>
  </form>

  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}

  {% if filename %}
    <h2>Bestand: {{ filename }}</h2>
    <p>Type: {{ obj_type_label }}</p>

    <h3 class="section-title">Certificate Subject</h3>
    <table>
      <tbody>
        {% for k, v in subject.items() %}
        <tr>
          <th>{{ k }}</th><td>{{ v }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <h3 class="section-title">Certificate Issuer</h3>
    {% if issuer %}
      <table>
        <tbody>
          {% for k, v in issuer.items() %}
          <tr>
            <th>{{ k }}</th><td>{{ v }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p>CSR heeft geen issuer; dit wordt pas ingevuld na uitgifte van het certificaat.</p>
    {% endif %}

    <h3 class="section-title">Certificate Properties</h3>
    <table>
      <tbody>
        {% for k, v in props.items() %}
        <tr>
          <th>{{ k }}</th><td>{{ v }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    filename = None
    obj_type_label = None
    subject = None
    issuer = None
    props = None

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            error = "Geen bestand geselecteerd."
        else:
            filename = file.filename
            try:
                data = file.read()
                obj_type, subject, issuer, props = decode_for_web(data)
                obj_type_label = "Certificate" if obj_type == "cert" else "CSR (Certificate Signing Request)"
            except Exception as e:
                error = f"Fout bij decoderen: {e}"

    return render_template_string(
        TEMPLATE,
        error=error,
        filename=filename,
        obj_type_label=obj_type_label,
        subject=subject,
        issuer=issuer,
        props=props,
    )


if __name__ == "__main__":
    # Start lokale webserver, bv. op http://127.0.0.1:5000
    app.run(debug=True)
