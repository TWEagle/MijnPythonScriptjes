import tkinter as tk
from tkinter import filedialog
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

def load_certificate(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    # Probeer PEM eerst
    try:
        cert = x509.load_pem_x509_certificate(data, default_backend())
        return cert
    except Exception:
        pass

    # Probeer DER
    try:
        cert = x509.load_der_x509_certificate(data, default_backend())
        return cert
    except Exception:
        pass

    # Probeer CSR PEM
    try:
        csr = x509.load_pem_x509_csr(data, default_backend())
        return csr
    except Exception:
        pass

    # Probeer CSR DER
    try:
        csr = x509.load_der_x509_csr(data, default_backend())
        return csr
    except Exception:
        pass

    raise ValueError("Kan het bestand niet als certificaat of CSR inlezen.")

def print_cert_info(cert_or_csr):
    # Afhankelijk of het een certificaat of CSR is:
    if isinstance(cert_or_csr, x509.Certificate):
        subject = cert_or_csr.subject
        issuer = cert_or_csr.issuer
        print("Certificaat gevonden:")
        print(f"Subject:")
        for attr in subject:
            print(f"  {attr.oid._name}: {attr.value}")
        print(f"Issuer:")
        for attr in issuer:
            print(f"  {attr.oid._name}: {attr.value}")
        print(f"Serial Number: {cert_or_csr.serial_number}")
        print(f"Not valid before: {cert_or_csr.not_valid_before}")
        print(f"Not valid after: {cert_or_csr.not_valid_after}")

    elif isinstance(cert_or_csr, x509.CertificateSigningRequest):
        subject = cert_or_csr.subject
        print("Certificate Signing Request (CSR) gevonden:")
        print("Subject:")
        for attr in subject:
            print(f"  {attr.oid._name}: {attr.value}")

    else:
        print("Onbekend certificaat object.")

    # Specifiek CN tonen (als aanwezig)
    cn_attributes = subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if cn_attributes:
        print(f"\nCommon Name (CN): {cn_attributes[0].value}")
    else:
        print("\nCommon Name (CN) niet gevonden.")

def main():
    root = tk.Tk()
    root.withdraw()  # Verberg het hoofdvenster

    file_path = filedialog.askopenfilename(
        title="Selecteer een certificaatbestand",
        filetypes=[("Certificate files", "*.csr *.crt *.pem *.der"), ("All files", "*.*")]
    )

    if not file_path:
        print("Geen bestand geselecteerd.")
        return

    try:
        cert_or_csr = load_certificate(file_path)
        print_cert_info(cert_or_csr)
    except Exception as e:
        print(f"Fout bij inlezen: {e}")

if __name__ == "__main__":
    main()
