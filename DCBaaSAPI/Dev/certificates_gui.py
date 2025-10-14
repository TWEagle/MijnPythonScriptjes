import argparse
import json
import base64
import requests
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox


APP_TITLE = "DCBaaS Certificate Manager"

TEMPLATES = [
    "SSL Server",
    "SSL Client",
    "SSL Signing",
    "SSL Client + Signing",
    "Machine Authenticatie",
    "ECC Client + Signing",
    "Andere"
]


class CertificateGUI(ttk.Window):
    def __init__(self, base_url="", token=""):
        super().__init__(themename="darkly")
        self.title(APP_TITLE)
        self.geometry("900x740")
        self.minsize(820, 600)

        # State
        self._base_url = base_url
        self.token_var = tk.StringVar(value=token)

        self.app_name_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.org_code_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="12")
        self.template_var = tk.StringVar(value=TEMPLATES[0])
        self.template_custom_var = tk.StringVar()
        self.csr_b64 = tk.StringVar(value="")

        self.status_var = tk.StringVar(value="")

        self._token_entry = None
        self._token_hidden = True

        self.create_widgets()

    # ---------- UI ----------
    def create_widgets(self):
        pad = {"padx": 8, "pady": 6}

        # Config
        cfg = ttk.LabelFrame(self, text="Configuratie")
        cfg.pack(fill="x", **pad)

        row = 0
        ttk.Label(cfg, text="Access token:").grid(row=row, column=0, sticky="w")
        self._token_entry = ttk.Entry(cfg, textvariable=self.token_var, width=60, show="•")
        self._token_entry.grid(row=row, column=1, sticky="w")
        ttk.Button(cfg, text="Toon/Verberg", command=self.toggle_token_visibility).grid(row=row, column=2, sticky="w")
        row += 1

        # Cert fields
        ops = ttk.LabelFrame(self, text="Certificate toevoegen")
        ops.pack(fill="x", **pad)

        ttk.Label(ops, text="Application name:").grid(row=0, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.app_name_var, width=50).grid(row=0, column=1, sticky="w")

        ttk.Label(ops, text="Description:").grid(row=1, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.description_var, width=50).grid(row=1, column=1, sticky="w")

        ttk.Label(ops, text="Organization code:").grid(row=2, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.org_code_var, width=30).grid(row=2, column=1, sticky="w")

        ttk.Label(ops, text="Duration (maanden):").grid(row=3, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.duration_var, width=10).grid(row=3, column=1, sticky="w")

        ttk.Label(ops, text="Certificate template:").grid(row=4, column=0, sticky="w")
        cb = ttk.Combobox(ops, values=TEMPLATES, textvariable=self.template_var, width=30, state="readonly")
        cb.grid(row=4, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", self._on_template_change)

        self.template_custom_entry = ttk.Entry(ops, textvariable=self.template_custom_var, width=40)
        # wordt enkel zichtbaar bij "Andere"

        ttk.Label(ops, text="CSR bestand:").grid(row=5, column=0, sticky="w")
        ttk.Button(ops, text="Kies bestand", command=self.load_csr_file).grid(row=5, column=1, sticky="w")

        ttk.Entry(ops, textvariable=self.csr_b64, width=80, state="readonly").grid(row=6, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(ops, text="Kopieer CSR Base64", command=self.copy_csr).grid(row=6, column=2, sticky="w")

        # Separator
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=6)

        # Knoppen
        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(6, 0))

        self.btn_add = ttk.Button(btns, text="Add Certificate", command=self.do_add)
        self.btn_add.pack(side="left", padx=4)

        ttk.Button(btns, text="Sluiten", command=self.destroy, bootstyle="danger").pack(side="right", padx=4)

        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.pack(side="bottom", fill="x", pady=2)

        # Output
        out = ttk.LabelFrame(self, text="Resultaat / Debug")
        out.pack(fill="both", expand=True, **pad)
        self.output = tk.Text(out, height=22)
        self.output.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- Helpers ----------
    def toggle_token_visibility(self):
        self._token_hidden = not self._token_hidden
        self._token_entry.config(show="•" if self._token_hidden else "")

    def log(self, *parts):
        s = " ".join(str(p) for p in parts)
        self.output.insert("end", s + "\n")
        self.output.see("end")

    def _headers(self):
        return {
            "Origin": "localhost",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": self.token_var.get().strip()  # RAW token
        }

    def _clear_output(self):
        self.output.delete("1.0", "end")

    def flash_button(self, button, success=True):
        button.config(bootstyle="success" if success else "danger")
        self.after(1500, lambda: button.config(bootstyle="secondary"))

    def _on_template_change(self, event=None):
        if self.template_var.get() == "Andere":
            self.template_custom_entry.grid(row=4, column=2, sticky="w")
        else:
            self.template_custom_entry.grid_forget()

    def load_csr_file(self):
        path = filedialog.askopenfilename(title="Kies CSR bestand", filetypes=[("CSR files", "*.csr"), ("Alle bestanden", "*.*")])
        if not path:
            return
        try:
            with open(path, "rb") as f:
                csr_bytes = f.read()
            csr_b64 = base64.b64encode(csr_bytes).decode("utf-8")
            self.csr_b64.set(csr_b64)
            self.log("CSR bestand geladen en omgezet naar Base64")
        except Exception as e:
            messagebox.showerror("Fout", f"Kon CSR niet lezen: {e}")

    def copy_csr(self):
        val = self.csr_b64.get().strip()
        if not val:
            messagebox.showinfo("Leeg", "Geen CSR om te kopiëren.")
            return
        self.clipboard_clear()
        self.clipboard_append(val)
        messagebox.showinfo("Gekopieerd", "CSR Base64 gekopieerd naar klembord.")

    # ---------- Actions ----------
    def do_add(self):
        app = self.app_name_var.get().strip()
        desc = self.description_var.get().strip()
        org = self.org_code_var.get().strip()
        dur = self.duration_var.get().strip()
        csr = self.csr_b64.get().strip()

        if not app or not csr:
            messagebox.showerror("Fout", "Application name en CSR zijn verplicht.")
            self.flash_button(self.btn_add, success=False)
            return
        try:
            dur = int(dur)
        except ValueError:
            messagebox.showerror("Fout", "Duration moet een geheel getal zijn.")
            self.flash_button(self.btn_add, success=False)
            return

        tpl = self.template_var.get()
        if tpl == "Andere":
            tpl = self.template_custom_var.get().strip()

        payload = {
            "application_name": app,
            "description": desc or f"Certificaat {app}",
            "organization_code": org,
            "duration": dur,
            "certificate_template": tpl,
            "csr": csr,
        }

        self._post("application/certificate/add", payload, self.btn_add)

    # ---------- Networking ----------
    def _post(self, path: str, payload: dict, button=None):
        def task():
            self.status_var.set("⏳ Bezig met POST...")
            url = f"{self._base_url}/dev/{path.lstrip('/')}"

            headers = self._headers()
            self._clear_output()
            self.log(f"POST {url}")
            self.log("Body:", json.dumps(payload, ensure_ascii=False))

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                self._log_response(resp)
                if button:
                    self.flash_button(button, success=(resp.status_code == 200))
            except requests.RequestException as e:
                self.log("Request error:", e)
                messagebox.showerror("Request error", str(e))
                if button:
                    self.flash_button(button, success=False)
            finally:
                self.status_var.set("")

        threading.Thread(target=task, daemon=True).start()

    def _log_response(self, resp: requests.Response):
        self.log(f"Status: {resp.status_code}")
        try:
            self.log("Response:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
        except Exception:
            self.log("Response (raw):", resp.text)
        try:
            self.log("Headers(resp):", json.dumps(dict(resp.headers), indent=2, ensure_ascii=False))
        except Exception:
            pass


# ---------- main ----------
def parse_args():
    p = argparse.ArgumentParser(description=APP_TITLE)
    p.add_argument("--token", dest="token", default="", help="Access token")
    p.add_argument("--base-url", dest="base_url", default="", help="Base URL")
    return p.parse_args()


def main():
    args = parse_args()
    gui = CertificateGUI(
        base_url=args.base_url,
        token=args.token,
    )
    gui.mainloop()


if __name__ == "__main__":
    main()
