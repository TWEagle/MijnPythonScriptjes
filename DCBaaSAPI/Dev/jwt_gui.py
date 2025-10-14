import time
import json
import os
import subprocess
import sys
import requests
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

import jwt
from jwt import PyJWTError

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from jwcrypto import jwk

APP_TITLE = "JWT Generator (RS256) — JWK/PEM/PFX"
DEFAULT_EXP_OFFSET = 300  # 5 minuten
CONFIG_PATH = Path.home() / ".jwt_gui_config.json"

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showwarning("Kon instellingen niet opslaan", str(e))

class JWTApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")  # andere opties: "cyborg", "superhero", "solar"
        self.title(APP_TITLE)
        self.geometry("980x920")
        self.minsize(860, 800)

        # ==== State ====
        self.key_path = tk.StringVar()
        self.key_password = tk.StringVar()

        # iss == sub (één veld), aud is JWT-claim
        self.iss_sub = tk.StringVar()
        self.aud = tk.StringVar()

        # centrale base URL (Postman {{url}})
        self.base_url = tk.StringVar()

        # token audience voor /op/v1/token (niet de JWT aud-claim!)
        self.token_audience = tk.StringVar()

        self.iat = tk.IntVar(value=int(time.time()))
        self.exp = tk.IntVar(value=int(time.time()) + DEFAULT_EXP_OFFSET)
        self.exp_offset = tk.IntVar(value=DEFAULT_EXP_OFFSET)
        self.link_exp = tk.BooleanVar(value=True)

        self.alg = tk.StringVar(value="RS256")
        self.kid = tk.StringVar()  # optioneel header veld

        self.last_access_token = None  # onthoud het laatst opgehaalde access token

        # Config laden en defaults zetten
        self.cfg = load_config()
        self._apply_config_defaults()

        self._build_ui()
        self._bind_events()

    def _apply_config_defaults(self):
        self.iss_sub.set(self.cfg.get("iss_sub", "612bf17a-ebb0-45c3-9225-d04f1067a0b0"))
        self.aud.set(self.cfg.get("aud", "https://authenticatie-ti.vlaanderen.be/op"))
        self.kid.set(self.cfg.get("kid", ""))

        # {{url}} en token_audience
        self.base_url.set(self.cfg.get("base_url", "https://extapi.dcb-dev.vlaanderen.be"))
        self.token_audience.set(self.cfg.get("token_audience", ""))  # leeg = fallback naar iss_sub

        now = int(time.time())
        self.iat.set(now)
        self.exp_offset.set(int(self.cfg.get("exp_offset", DEFAULT_EXP_OFFSET)))
        self.link_exp.set(bool(self.cfg.get("link_exp", True)))
        if self.link_exp.get():
            self.exp.set(now + int(self.exp_offset.get()))
        else:
            self.exp.set(int(self.cfg.get("exp", now + DEFAULT_EXP_OFFSET)))

        self.alg.set(self.cfg.get("alg", "RS256"))

        kp = self.cfg.get("key_path", "")
        if kp and Path(kp).exists():
            self.key_path.set(kp)

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        # Centrale instellingen incl. {{url}} en token audience
        frm_url = ttk.LabelFrame(self, text="Centrale instellingen (Postman {{url}})")
        frm_url.pack(fill="x", **pad)
        ttk.Label(frm_url, text="Base URL ({{url}}):").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm_url, textvariable=self.base_url, width=70).grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(frm_url, text="Token audience (/op/v1/token):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm_url, textvariable=self.token_audience, width=70).grid(row=1, column=1, sticky="ew", **pad)
        frm_url.columnconfigure(1, weight=1)

        # JWT Claims
        frm_top = ttk.LabelFrame(self, text="JWT Claims")
        frm_top.pack(fill="x", **pad)

        ttk.Label(frm_top, text="iss & sub (identiek):").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm_top, textvariable=self.iss_sub, width=60).grid(row=0, column=1, columnspan=3, sticky="ew", **pad)

        ttk.Label(frm_top, text="aud (Audience claim in JWT):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm_top, textvariable=self.aud, width=60).grid(row=1, column=1, columnspan=3, sticky="ew", **pad)

        ttk.Label(frm_top, text="iat (Issued At, epoch):").grid(row=2, column=0, sticky="w", **pad)
        self.iat_entry = ttk.Entry(frm_top, textvariable=self.iat, width=20)
        self.iat_entry.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(frm_top, text="exp (Expiration, epoch):").grid(row=3, column=0, sticky="w", **pad)
        self.exp_entry = ttk.Entry(frm_top, textvariable=self.exp, width=20)
        self.exp_entry.grid(row=3, column=1, sticky="w", **pad)

        link_cb = ttk.Checkbutton(frm_top, text="Houd exp = iat + offset (sec)", variable=self.link_exp, command=self.sync_exp)
        link_cb.grid(row=2, column=2, sticky="w", **pad)
        ttk.Spinbox(frm_top, from_=5, to=86400, textvariable=self.exp_offset, width=10, command=self.sync_exp).grid(row=2, column=3, sticky="w", **pad)

        frm_top.columnconfigure(1, weight=1)

        # Header / Alg
        frm_hdr = ttk.LabelFrame(self, text="Header / Algoritme")
        frm_hdr.pack(fill="x", **pad)

        ttk.Label(frm_hdr, text="alg:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Combobox(frm_hdr, values=["RS256"], textvariable=self.alg, width=10, state="readonly").grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(frm_hdr, text="kid (optioneel):").grid(row=0, column=2, sticky="e", **pad)
        ttk.Entry(frm_hdr, textvariable=self.kid, width=30).grid(row=0, column=3, sticky="w", **pad)

        # Private Key
        frm_key = ttk.LabelFrame(self, text="Private Key")
        frm_key.pack(fill="x", **pad)

        ttk.Label(frm_key, text="Bestand (.jwk/.json/.pem/.key/.pfx/.p12):").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm_key, textvariable=self.key_path, width=60).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(frm_key, text="Kies…", command=self.choose_key).grid(row=0, column=2, **pad)

        ttk.Label(frm_key, text="Wachtwoord (optioneel, voor versleutelde PEM/PFX):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm_key, textvariable=self.key_password, show="•", width=30).grid(row=1, column=1, sticky="w", **pad)

        frm_key.columnconfigure(1, weight=1)
        
        # Separator boven knoppenbalk
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=4)

        # Acties
        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", **pad)

        # Links
        left_frame = ttk.Frame(frm_actions)
        left_frame.pack(side="left", padx=8)
        ttk.Button(left_frame, text="Tijden verversen", command=self.refresh_times).pack(side="left", padx=4)
        ttk.Button(left_frame, text="Instellingen opslaan", command=self.save_current_config).pack(side="left", padx=4)

        # Midden
        mid_frame = ttk.Frame(frm_actions)
        mid_frame.pack(side="left", padx=8)
        ttk.Button(mid_frame, text="Genereer JWT", command=self.generate_jwt).pack(side="left", padx=4)
        ttk.Button(mid_frame, text="Access Token", command=self.ask_access_token).pack(side="left", padx=4)

        # Rechts
        right_frame = ttk.Frame(frm_actions)
        right_frame.pack(side="right", padx=8)
        ttk.Button(right_frame, text="Toepassingen", command=self.open_application_gui).pack(side="left", padx=4)
        ttk.Button(frm_actions, text="Certificates GUI", command=self.open_certificates_gui, bootstyle="secondary").pack(side="right", padx=4)
        ttk.Button(right_frame, text="Sluiten", command=self.close_and_cleanup, bootstyle="danger").pack(side="left", padx=4)




        # Output
        frm_out = ttk.LabelFrame(self, text="JWT / Access token (gecodeerd)")
        frm_out.pack(fill="both", expand=True, **pad)

        self.jwt_text = ScrolledText(frm_out, wrap="word", height=16)
        self.jwt_text.pack(fill="both", expand=True, padx=6, pady=6)

        frm_out_btns = ttk.Frame(frm_out)
        frm_out_btns.pack(fill="x", padx=6, pady=6)
        ttk.Button(frm_out_btns, text="Kopieer naar klembord", command=self.copy_to_clipboard).pack(side="left", padx=4)
        ttk.Button(frm_out_btns, text="Opslaan als…", command=self.save_token).pack(side="left", padx=4)

    def _bind_events(self):
        self.iat_entry.bind("<KeyRelease>", lambda e: self.sync_exp())
        self.exp_entry.bind("<FocusOut>", lambda e: self.validate_exp())

    # -------------- Helpers --------------
    def choose_key(self):
        initialdir = None
        if self.key_path.get():
            try:
                initialdir = str(Path(self.key_path.get()).parent)
            except Exception:
                initialdir = None

        path = filedialog.askopenfilename(
            title="Kies private key",
            initialdir=initialdir,
            filetypes=[
                ("Key bestanden", "*.jwk *.json *.pem *.key *.pfx *.p12"),
                ("Alle bestanden", "*.*"),
            ]
        )
        if path:
            self.key_path.set(path)
            self.cfg["key_path"] = path
            save_config(self.cfg)

    def refresh_times(self):
        now = int(time.time())
        self.iat.set(now)
        if self.link_exp.get():
            self.exp.set(now + int(self.exp_offset.get()))

    def sync_exp(self):
        try:
            iat_val = int(self.iat.get())
        except Exception:
            return
        if self.link_exp.get():
            try:
                off = int(self.exp_offset.get())
            except Exception:
                off = DEFAULT_EXP_OFFSET
            self.exp.set(iat_val + off)

    def validate_exp(self):
        try:
            iat = int(self.iat.get())
            exp = int(self.exp.get())
            if exp <= iat:
                messagebox.showwarning("Ongeldige exp", "exp moet groter zijn dan iat.")
        except Exception:
            pass

    def save_current_config(self):
        self.cfg.update({
            "iss_sub": self.iss_sub.get().strip(),
            "aud": self.aud.get().strip(),
            "kid": self.kid.get().strip(),
            "exp_offset": int(self.exp_offset.get()),
            "link_exp": bool(self.link_exp.get()),
            "alg": self.alg.get(),
            "key_path": self.key_path.get().strip(),
            "base_url": self.base_url.get().strip(),
            "token_audience": self.token_audience.get().strip(),
            "exp": int(self.exp.get()) if not self.link_exp.get() else None,
        })
        self.cfg = {k: v for k, v in self.cfg.items() if v is not None and v != ""}
        save_config(self.cfg)
        messagebox.showinfo("Opgeslagen", f"Instellingen opgeslagen naar:\n{CONFIG_PATH}")

    # ---- Key loading (JWK / PEM / PFX) ----
    def load_private_key(self):
        path = self.key_path.get().strip()
        if not path:
            raise ValueError("Geen private key geselecteerd.")

        p = Path(path)
        ext = p.suffix.lower()

        if ext in [".jwk", ".json"]:
            try:
                data_text = p.read_text(encoding="utf-8")
                _ = json.loads(data_text)
                key = jwk.JWK.from_json(data_text)
                if not self.kid.get().strip():
                    try:
                        kid_val = json.loads(key.export(as_dict=True))["kid"]
                        if kid_val:
                            self.kid.set(kid_val)
                    except Exception:
                        pass
                pem_key_bytes = key.export_to_pem(private_key=True, password=None)
                return load_pem_private_key(pem_key_bytes, password=None)
            except Exception as e:
                raise ValueError(f"Kon JWK niet laden: {e}")

        if ext in [".pem", ".key"]:
            try:
                pwd = self.key_password.get().encode("utf-8") if self.key_password.get() else None
                return load_pem_private_key(p.read_bytes(), password=pwd)
            except Exception as e:
                raise ValueError(f"Kon PEM/KEY niet laden: {e}")

        if ext in [".pfx", ".p12"]:
            try:
                pwd = self.key_password.get().encode("utf-8") if self.key_password.get() else None
                key, cert, addl = load_key_and_certificates(p.read_bytes(), pwd)
                if key is None:
                    raise ValueError("Geen private key gevonden in PKCS#12.")
                return key
            except Exception as e:
                raise ValueError(f"Kon PKCS#12 (.pfx/.p12) niet laden: {e}")

        raise ValueError("Onbekend sleuteltype. Gebruik .jwk/.json, .pem/.key of .pfx/.p12")

    def build_claims(self):
        try:
            iat = int(self.iat.get())
            exp = int(self.exp.get())
        except Exception:
            raise ValueError("iat/exp moeten integers (epoch seconden) zijn.")

        if exp <= iat:
            raise ValueError("exp moet groter zijn dan iat.")

        iss_sub_val = self.iss_sub.get().strip()
        aud_val = self.aud.get().strip()

        if not iss_sub_val or not aud_val:
            raise ValueError("Vul het veld 'iss & sub' en 'aud' in.")

        claims = {
            "iss": iss_sub_val,
            "sub": iss_sub_val,
            "aud": aud_val,
            "iat": iat,
            "exp": exp,
        }
        return claims

    # -------------- Generate / Output --------------
    def generate_jwt(self):
        try:
            key = self.load_private_key()
            claims = self.build_claims()

            headers = {"typ": "JWT", "alg": self.alg.get()}
            if self.kid.get().strip():
                headers["kid"] = self.kid.get().strip()

            token = jwt.encode(
                payload=claims,
                key=key,
                algorithm=self.alg.get(),
                headers=headers
            )

            self.jwt_text.delete("1.0", "end")
            self.jwt_text.insert("1.0", token)
            self.last_access_token = None  # reset: we tonen nu de JWT

            self.save_current_config()

        except (ValueError, PyJWTError) as e:
            messagebox.showerror("Fout bij genereren", str(e))
        except Exception as e:
            messagebox.showerror("Onbekende fout", repr(e))

    # -------------- Token endpoint call --------------
    
    def ask_access_token(self):
        audience = (self.token_audience.get().strip() or self.iss_sub.get().strip())
        client_assertion = self.jwt_text.get("1.0", "end").strip()

        if not client_assertion or client_assertion.count(".") != 2:
            messagebox.showwarning("Geen JWT", "Genereer eerst de JWT (client_assertion).")
            return
        if not audience:
            messagebox.showwarning("Ontbrekende audience", "Vul 'Token audience' of 'iss & sub' in.")
            return

        url = "https://authenticatie-ti.vlaanderen.be/op/v1/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_assertion,
            "audience": audience,
        }

        try:
            print("[DEBUG] Requesting access_token at:", url)
            resp = requests.post(url, headers=headers, data=data, timeout=30)
            print("[DEBUG] Response status:", resp.status_code)
            print("[DEBUG] Response body:", resp.text)

            resp.raise_for_status()
            token_data = resp.json()
            access_token = token_data.get("access_token", "")

            if not access_token:
                raise RuntimeError("Geen access_token ontvangen van token endpoint.")

            self.last_access_token = access_token
            self.clipboard_clear()
            self.clipboard_append(access_token)

            # Toon access token in GUI
            self.jwt_text.delete("1.0", "end")
            self.jwt_text.insert("1.0", access_token)

            messagebox.showinfo("Access token", "Access token opgehaald en gekopieerd naar klembord.")

            # ==== DEBUG: schrijf context weg ====
            from pathlib import Path
            import json
            debug_file = Path(__file__).with_name(".debug_context.json")
            ctx = {
                "access_token": self.last_access_token,
                "base_url": self.base_url.get().strip()
            }
            debug_file.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
            print("[DEBUG] Context written to", debug_file)
            # =====================================

        except Exception as e:
            messagebox.showerror("Fout bij token aanvraag", str(e))


    # -------------- Open secondary GUI --------------
    def open_application_gui(self):
        base_url = self.base_url.get().strip()
        if not base_url:
            messagebox.showwarning("Ontbrekende {{url}}", "Vul eerst de centrale Base URL ({{url}}) in.")
            return

        if not self.last_access_token:
            messagebox.showwarning("Geen access token", "Vraag eerst een access_token op.")
            return

        app_gui_path = Path(__file__).with_name("application_gui.py")
        if not app_gui_path.exists():
            messagebox.showerror("Bestand ontbreekt", f"application_gui.py niet gevonden in:\n{app_gui_path.parent}")
            return

        try:
            # Geef base-url en token door als CLI-parameters
            cmd = [
                sys.executable,
                str(app_gui_path),
                "--token", self.last_access_token,   # juiste vlag
            ]
            print("[DEBUG] Opening application_gui.py with token (first 50 chars):",
                (self.last_access_token or "")[:50], "...")
            subprocess.Popen(cmd)

        except Exception as e:
            messagebox.showerror("Kon Application GUI niet openen", repr(e))

    def copy_to_clipboard(self):
        content = self.jwt_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Leeg", "Er is geen inhoud om te kopiëren.")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("Gekopieerd", "Inhoud gekopieerd naar het klembord.")

    def close_and_cleanup(self):
        try:
            from pathlib import Path
            debug_file = Path(__file__).with_name(".debug_context.json")
            if debug_file.exists():
                debug_file.unlink()
                print("[DEBUG] Context file removed:", debug_file)
        except Exception as e:
            print("[DEBUG] Could not remove context file:", e)
        self.destroy()        

    def save_token(self):
        content = self.jwt_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Leeg", "Er is geen inhoud om op te slaan.")
            return
        initialdir = None
        if self.key_path.get():
            try:
                initialdir = str(Path(self.key_path.get()).parent)
            except Exception:
                initialdir = None

        path = filedialog.asksaveasfilename(
            title="Sla output op",
            initialdir=initialdir,
            defaultextension=".txt",
            filetypes=[("Text", "*.txt *.jwt *.token"), ("Alle bestanden", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(content, encoding="utf-8")
        messagebox.showinfo("Opgeslagen", f"Output opgeslagen naar:\n{path}")
    
    def open_certificates_gui(self):
        base_url = self.base_url.get().strip()
        if not base_url:
            messagebox.showwarning("Ontbrekende {{url}}", "Vul eerst de centrale Base URL ({{url}}) in.")
            return

        if not self.last_access_token:
            messagebox.showwarning("Geen access token", "Vraag eerst een access_token op.")
            return

        cert_gui_path = Path(__file__).with_name("certificates_gui.py")
        if not cert_gui_path.exists():
            messagebox.showerror("Bestand ontbreekt", f"certificates_gui.py niet gevonden in:\n{cert_gui_path.parent}")
            return

        try:
            cmd = [
                sys.executable,
                str(cert_gui_path),
                "--token", self.last_access_token,
                "--base-url", base_url,
            ]
            print("[DEBUG] Opening certificates_gui.py with token (first 50 chars):",
                (self.last_access_token or "")[:50], "...")
            subprocess.Popen(cmd)

        except Exception as e:
            messagebox.showerror("Kon Certificates GUI niet openen", repr(e))



if __name__ == "__main__":
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = JWTApp()
    app.mainloop()
