#!/usr/bin/env python3
"""
decode_cert_info.py

Gebruik:
    python decode_cert_info.py pad/naar/bestand1.crt pad/naar/bestand2.csr ...

Ondersteunt:
    - X.509 certificaten (PEM/DER)  -> .crt, .cer, .pem
    - CSRs (PEM/DER)                -> .csr

Toont info in tabelvorm:
    - Certificate Subject
    - Certificate Issuer (indien cert)
    - Certificate Properties
"""

import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec
from cryptography.x509.oid import NameOID


# ---------- Helper functies ----------

def load_cert_or_csr(data: bytes):
    """
    Probeert eerst PEM, dan DER, voor zowel Certificate als CSR.
    Return:
        ("cert", x509.Certificate) of ("csr", x509.CertificateSigningRequest)
    Raise:
        ValueError als niets lukt.
    """
    # Eerst PEM proberen
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

    if text and "BEGIN" in text:
        # Iets anders PEM-achtig maar niet herkend
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
        "Common Name":        get_name_attr(name, NameOID.COMMON_NAME),
        "emailAddress":       get_name_attr(name, NameOID.EMAIL_ADDRESS),
        "Organizational Unit": get_name_attr(name, NameOID.ORGANIZATIONAL_UNIT_NAME),
        "Organization":       get_name_attr(name, NameOID.ORGANIZATION_NAME),
        "Locality":           get_name_attr(name, NameOID.LOCALITY_NAME),
        "State or Province":  get_name_attr(name, NameOID.STATE_OR_PROVINCE_NAME),
        "Country":            get_name_attr(name, NameOID.COUNTRY_NAME),
    }


def format_name(name: x509.Name) -> str:
    # Mooie, compacte weergave van volledige Subject/Issuer
    parts = []
    for rdn in name.rdns:
        for attr in rdn:
            parts.append(f"{attr.oid._name}={attr.value}")
    return ", ".join(parts) if parts else "-"


def get_key_info(public_key) -> tuple[str, str]:
    """
    Bepaal Key Algorithm & Key Size.
    """
    if isinstance(public_key, rsa.RSAPublicKey):
        return "RSA", str(public_key.key_size)
    if isinstance(public_key, dsa.DSAPublicKey):
        return "DSA", str(public_key.key_size)
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        # Soms wil je de curve, maar jij vraagt Key Size:
        try:
            size = public_key.key_size
        except Exception:
            size = "-"
        return f"EC ({public_key.curve.name})", str(size)
    # fallback
    return public_key.__class__.__name__, "-"


def get_signature_algorithm(obj) -> str:
    """
    Voor certificaten: signature + hash.
    Voor CSR is signature_hash_algorithm ook beschikbaar.
    """
    try:
        sig_hash = obj.signature_hash_algorithm.name
    except Exception:
        sig_hash = "-"

    # Bij cert is er ook signature_algorithm_oid
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


def print_section(title: str):
    print(title)
    print("-" * len(title))


def print_table(mapping: dict):
    """
    Eenvoudige tabel met Field | Value.
    """
    if not mapping:
        print("  (geen gegevens)")
        print()
        return

    col_width = max(len(k) for k in mapping.keys()) + 2
    for key, val in mapping.items():
        print(f"{key.ljust(col_width)} {val}")
    print()


# ---------- Hoofdlogica per bestand ----------

def process_file(path: Path):
    print("=" * 80)
    print(f"Bestand: {path} ")
    print("=" * 80)

    try:
        data = path.read_bytes()
    except Exception as e:
        print(f"FOUT: Kan bestand niet lezen: {e}")
        print()
        return

    try:
        obj_type, obj = load_cert_or_csr(data)
    except ValueError as e:
        print(f"FOUT: {e}")
        print()
        return

    print(f"Type: {'Certificate' if obj_type == 'cert' else 'CSR (Certificate Signing Request)'}")
    print()

    # Subject
    subj = obj.subject
    subj_map = subject_fields(subj)

    print_section("Certificate Subject")
    print_table(subj_map)

    # Issuer (alleen bij certificaat)
    if obj_type == "cert":
        issuer = obj.issuer
        issuer_map = {
            "Issuer Common Name":   get_name_attr(issuer, NameOID.COMMON_NAME),
            "Issuer emailAddress":  get_name_attr(issuer, NameOID.EMAIL_ADDRESS),
            "Issuer Organization":  get_name_attr(issuer, NameOID.ORGANIZATION_NAME),
            "Issuer Locality":      get_name_attr(issuer, NameOID.LOCALITY_NAME),
            "Issuer State or Province": get_name_attr(issuer, NameOID.STATE_OR_PROVINCE_NAME),
            "Issuer Country":       get_name_attr(issuer, NameOID.COUNTRY_NAME),
        }

        print_section("Certificate Issuer")
        print_table(issuer_map)
    else:
        print_section("Certificate Issuer")
        print("  (CSR heeft geen issuer; dit wordt pas ingevuld na uitgifte van het certificaat.)")
        print()

    # Properties
    public_key = obj.public_key()
    key_algo, key_size = get_key_info(public_key)
    sig_algo = get_signature_algorithm(obj)

    if obj_type == "cert":
        valid_from = obj.not_valid_before
        valid_to = obj.not_valid_after
        serial = hex(obj.serial_number).upper().replace("X", "x")  # mooi hex
        thumb = compute_thumbprint(obj)
    else:
        valid_from = "-"
        valid_to = "-"
        serial = "-"
        thumb = "-"

    props = {
        "Subject":        format_name(obj.subject),
        "Issuer":         format_name(obj.issuer) if obj_type == "cert" else "-",
        "Valid From":     valid_from if isinstance(valid_from, str) else (valid_from.isoformat() if valid_from != "-" else "-"),
        "Valid To":       valid_to if isinstance(valid_to, str) else (valid_to.isoformat() if valid_to != "-" else "-"),
        "Key Size":       key_size,
        "Key Algorithm":  key_algo,
        "Sig. Algorithm": sig_algo,
        "Serial Number":  serial,
        "Thumbprint":     thumb,
    }

    print_section("Certificate Properties")
    print_table(props)


def main(argv: list[str]):
    if len(argv) < 2:
        print("Gebruik:")
        print(f"  {Path(argv[0]).name} <cert_of_csr_bestand1> [bestand2 ...]")
        print()
        print("Voorbeelden:")
        print(f"  {Path(argv[0]).name} server.crt")
        print(f"  {Path(argv[0]).name} request.csr intermediate.pem root.cer")
        sys.exit(1)

    for arg in argv[1:]:
        path = Path(arg)
        process_file(path)


if __name__ == "__main__":
    main(sys.argv)
