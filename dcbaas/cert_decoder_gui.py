#!/usr/bin/env python3
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec
from cryptography.x509.oid import NameOID


# ---------- Decode logica (herbruikbaar) ----------

def load_cert_or_csr(data: bytes):
    """
    Probeert eerst PEM, dan DER, voor zowel Certificate als CSR.
    Return:
        ("cert", x509.Certificate) of ("csr", x509.CertificateSigningRequest)
    Raise:
        ValueError als niets lukt.
    """
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

    # DER proberen
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


def dict_to_table_text(title: str, mapping: dict) -> str:
    if not mapping:
        return f"{title}\n" + "-" * len(title) + "\n(geen gegevens)\n\n"

    max_key = max(len(k) for k in mapping.keys())
    lines = [title, "-" * len(title)]
    for k, v in mapping.items():
        lines.append(f"{k.ljust(max_key)}  {v}")
    lines.append("")  # lege lijn
    return "\n".join(lines) + "\n"


def decode_file_to_text(path: Path) -> str:
    try:
        data = path.read_bytes()
    except Exception as e:
        return f"FOUT: Kan bestand niet lezen: {e}"

    try:
        obj_type, obj = load_cert_or_csr(data)
    except ValueError as e:
        return f"FOUT: {e}"

    lines = []
    lines.append("=" * 80)
    lines.append(f"Bestand: {path}")
    lines.append("=" * 80)
    lines.append(f"Type: {'Certificate' if obj_type == 'cert' else 'CSR (Certificate Signing Request)'}")
    lines.append("")

    # Subject
    subj_map = subject_fields(obj.subject)
    lines.append(dict_to_table_text("Certificate Subject", subj_map))

    # Issuer
    if obj_type == "cert":
        issuer = obj.issuer
        issuer_map = {
            "Issuer Common Name":      get_name_attr(issuer, NameOID.COMMON_NAME),
            "Issuer emailAddress":     get_name_attr(issuer, NameOID.EMAIL_ADDRESS),
            "Issuer Organization":     get_name_attr(issuer, NameOID.ORGANIZATION_NAME),
            "Issuer Locality":         get_name_attr(issuer, NameOID.LOCALITY_NAME),
            "Issuer State or Province": get_name_attr(issuer, NameOID.STATE_OR_PROVINCE_NAME),
            "Issuer Country":          get_name_attr(issuer, NameOID.COUNTRY_NAME),
        }
        lines.append(dict_to_table_text("Certificate Issuer", issuer_map))
    else:
        block_title = "Certificate Issuer"
        lines.append(block_title)
        lines.append("-" * len(block_title))
        lines.append("CSR heeft geen issuer; dit wordt pas ingevuld na uitgifte van het certificaat.")
        lines.append("")

    # Properties
    public_key = obj.public_key()
    key_algo, key_size = get_key_info(public_key)
    sig_algo = get_signature_algorithm(obj)

    if obj_type == "cert":
        valid_from = obj.not_valid_before.isoformat()
        valid_to = obj.not_valid_after.isoformat()
        serial = hex(obj.serial_number).upper().replace("X", "x")
        thumb = compute_thumbprint(obj)
        issuer_str = format_name(obj.issuer)
    else:
        valid_from = "-"
        valid_to = "-"
        serial = "-"
        thumb = "-"
        issuer_str = "-"

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
    lines.append(dict_to_table_text("Certificate Properties", props))

    return "\n".join(lines)


# ---------- Tkinter GUI ----------

class CertDecoderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Certificate / CSR Decoder")
        self.geometry("900x600")

        # Bovenste frame
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.btn_open = tk.Button(top_frame, text="Bestand kiezen…", command=self.choose_file)
        self.btn_open.pack(side=tk.LEFT)

        self.lbl_file = tk.Label(top_frame, text="Geen bestand geselecteerd", anchor="w")
        self.lbl_file.pack(side=tk.LEFT, padx=10)

        # Tekstveld met scrollbar
        self.text = scrolledtext.ScrolledText(self, wrap=tk.NONE, font=("Consolas", 10))
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def choose_file(self):
        filetypes = [
            ("Alle ondersteunde bestanden", "*.crt *.cer *.pem *.csr"),
            ("Certificates", "*.crt *.cer *.pem"),
            ("Certificate Signing Requests", "*.csr"),
            ("Alle bestanden", "*.*"),
        ]
        filename = filedialog.askopenfilename(
            title="Kies een certificaat of CSR",
            filetypes=filetypes
        )
        if not filename:
            return

        path = Path(filename)
        self.lbl_file.config(text=str(path))

        result = decode_file_to_text(path)

        # Output tonen
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, result)


def main():
    app = CertDecoderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
