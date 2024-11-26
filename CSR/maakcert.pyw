import tkinter as tk
from tkinter import filedialog, messagebox
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import CertificateSigningRequestBuilder
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
import OpenSSL
import os

# Functie om RSA sleutel te genereren
def generate_rsa_key(key_name):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(f"{key_name}.pem", "wb") as key_file:
        key_file.write(pem_key)
    return private_key

# Functie voor CSR generatie
def generate_csr(private_key, common_name):
    csr = CertificateSigningRequestBuilder().subject_name(
        x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
    ).sign(private_key, hashes.SHA256())
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    with open(f"{common_name}.csr", "wb") as csr_file:
        csr_file.write(csr_pem)

# Functie voor PKCS#12 generatie
def generate_p12(cert, private_key, password):
    pkcs12 = OpenSSL.crypto.PKCS12()
    pkcs12.set_privatekey(private_key)
    pkcs12.set_certificate(cert)

    p12_data = pkcs12.export(password.encode())
    with open(f"output.p12", "wb") as p12_file:
        p12_file.write(p12_data)

# Functie om certificaat te laden en te combineren
def load_certificate_and_create_p12(certificate_path, private_key_path, password):
    # Laad het certificaat en de private key
    with open(certificate_path, "rb") as cert_file:
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_file.read())
    
    with open(private_key_path, "rb") as key_file:
        private_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_file.read())
    
    # Genereer het p12 bestand
    generate_p12(cert, private_key, password)

# GUI setup
def create_gui():
    root = tk.Tk()
    root.title("Certificaat en Key Manager")

    # Bestand selectie en invoervelden
    def select_file():
        filename = filedialog.askopenfilename(title="Selecteer X.509 Certificaat")
        entry_cert_file.delete(0, tk.END)
        entry_cert_file.insert(0, filename)

    def submit():
        key_name = entry_key_name.get()
        num_files = int(entry_num_files.get())
        cert_file = entry_cert_file.get()
        key_file = f"{key_name}.pem"

        # Maak RSA Key en CSR
        private_key = generate_rsa_key(key_name)
        generate_csr(private_key, key_name)

        # Laad het certificaat
        load_certificate_and_create_p12(cert_file, key_file, password_entry.get())

        messagebox.showinfo("Success", f"Bestanden zijn opgeslagen voor {num_files} items!")

    # GUI elementen
    tk.Label(root, text="Aantal bestanden:").grid(row=0, column=0)
    entry_num_files = tk.Entry(root)
    entry_num_files.grid(row=0, column=1)

    tk.Label(root, text="Naam RSA Key:").grid(row=1, column=0)
    entry_key_name = tk.Entry(root)
    entry_key_name.grid(row=1, column=1)

    tk.Label(root, text="Selecteer X.509 Certificaat:").grid(row=2, column=0)
    entry_cert_file = tk.Entry(root)
    entry_cert_file.grid(row=2, column=1)
    tk.Button(root, text="Bestand kiezen", command=select_file).grid(row=2, column=2)

    tk.Label(root, text="Wachtwoord voor .p12:").grid(row=3, column=0)
    password_entry = tk.Entry(root, show="*")
    password_entry.grid(row=3, column=1)

    tk.Button(root, text="Opslaan", command=submit).grid(row=4, column=0, columnspan=3)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
