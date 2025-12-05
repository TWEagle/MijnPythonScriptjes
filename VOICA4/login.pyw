import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import json

class CertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Certificaat Aanvraag")

        # Inlogvelden
        tk.Label(root, text="API Key:").grid(row=0, column=0)
        tk.Label(root, text="API Secret:").grid(row=1, column=0)

        self.api_key = tk.Entry(root, width=50)
        self.api_secret = tk.Entry(root, show="*", width=50)

        self.api_key.grid(row=0, column=1)
        self.api_secret.grid(row=1, column=1)

        # Certificaatbestanden
        tk.Button(root, text="Selecteer PFX", command=self.select_pfx).grid(row=2, column=0, pady=5)
        tk.Button(root, text="Selecteer PEM", command=self.select_pem).grid(row=3, column=0)

        self.pfx_path = tk.Label(root, text="Geen bestand gekozen")
        self.pem_path = tk.Label(root, text="Geen bestand gekozen")

        self.pfx_path.grid(row=2, column=1)
        self.pem_path.grid(row=3, column=1)

        # Login knop
        tk.Button(root, text="Login & Start", command=self.login).grid(row=4, column=0, columnspan=2, pady=10)

    def select_pfx(self):
        path = filedialog.askopenfilename(filetypes=[("PFX bestanden", "*.pfx")])
        self.pfx_path.config(text=path)

    def select_pem(self):
        path = filedialog.askopenfilename(filetypes=[("PEM bestanden", "*.pem")])
        self.pem_path.config(text=path)

    def login(self):
        key = self.api_key.get()
        secret = self.api_secret.get()

        login_url = "https://emea.api.hvca.globalsign.com:8443/v2/login"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        payload = {
            "api_key": key,
            "api_secret": secret
        }

        try:
            response = requests.post(login_url, json=payload, headers=headers)
            if response.status_code == 200:
                token = response.json()["access_token"]
                messagebox.showinfo("Succes", "Ingelogd!")
                self.open_csr_window(token)
            else:
                messagebox.showerror("Fout", f"Inloggen mislukt:\n{response.text}")
        except Exception as e:
            messagebox.showerror("Fout", str(e))

    def open_csr_window(self, token):
        self.root.destroy()
        new_root = tk.Tk()
        CSRWindow(new_root, token)
        new_root.mainloop()


class CSRWindow:
    def __init__(self, root, token):
        self.root = root
        self.token = token
        root.title("CSR Selectie")

        tk.Button(root, text="Selecteer CSR Bestand", command=self.select_csr).pack(pady=10)
        self.csr_label = tk.Label(root, text="Geen bestand gekozen")
        self.csr_label.pack()

        tk.Button(root, text="Verzend aanvraag", command=self.submit_csr).pack(pady=10)

    def select_csr(self):
        self.csr_path = filedialog.askopenfilename(filetypes=[("CSR bestanden", "*.csr")])
        self.csr_label.config(text=self.csr_path)

    def submit_csr(self):
        try:
            with open(self.csr_path, 'r') as f:
                csr_content = f.read()

            url = "https://emea.api.hvca.globalsign.com:8443/v2/certificates"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json;charset=utf-8"
            }

            payload = {
                "validity": {"not_before": 0},
                "subject_dn": {
                    "common_name": "Vlaamse overheid Prisma CA4",
                    "organization": "Vlaamse overheid",
                    "locality": "Brussel",
                    "state": "Brussel",
                    "country": "BE"
                },
                "signature": {"hash_algorithm": "SHA-256"},
                "public_key": csr_content,
                "extended_key_usages": ["1.3.6.1.5.5.7.3.1"]
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                cert_id = result.get("certificate_id", "Onbekend")
                messagebox.showinfo("Succes", f"Certificaat aangevraagd! ID: {cert_id}")
            else:
                messagebox.showerror("Fout", f"API fout:\n{response.text}")

        except Exception as e:
            messagebox.showerror("Fout", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = CertApp(root)
    root.mainloop()
