from pathlib import Path
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

import jwt
from jwt import PyJWTError

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from jwcrypto import jwk

APP_TITLE = "JWT Generator (RS256) — JWK/PEM/PFX"
DEFAULT_EXP_OFFSET = 300  # 5 minuten
CONFIG_PATH = Path.home() / ".jwt_gui_config.json"

# === Logging helpers (daily logs) ===
import sys, traceback
from datetime import datetime
try:
    from tkinter import messagebox
except Exception:
    # In non-GUI contexts, messagebox may not be available
    messagebox = None

def _log_dir() -> Path:
    p = Path(__file__).with_name("logs")
    try:
        p.mkdir(exist_ok=True)
    except Exception:
        pass
    return p

def _day_log_file() -> Path:
    ts = datetime.now().strftime("%Y-%m-%d")
    return _log_dir() / f"{ts}.log"

def _append_log(text: str):
    try:
        lf = _day_log_file()
        with lf.open("a", encoding="utf-8") as f:
            f.write(text if text.endswith("\n") else text + "\n")
    except Exception:
        # as last resort, try last_error.log in script dir
        try:
            Path(__file__).with_name("last_error.log").write_text(text, encoding="utf-8")
        except Exception:
            pass

def log_and_popup(title: str, detail: str):
    msg = f"{title}: {detail}"
    try:
        sys.stderr.write(msg + "\n")
    except Exception:
        pass
    _append_log(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}")
    if messagebox:
        try:
            messagebox.showerror(title, detail)
        except Exception:
            # ignore GUI errors
            pass

def _excepthook(exc_type, exc, tb):
    trace = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        sys.stderr.write(trace)
    except Exception:
        pass
    _append_log(f"[{datetime.now().isoformat(timespec='seconds')}] {trace}")
    if messagebox:
        try:
            messagebox.showerror("Onverwachte fout", str(exc))
        except Exception:
            pass

sys.excepthook = _excepthook
# === end logging helpers ===

# === Omgevingen ===
ENVIRONMENTS = {
    "Dev": {
        "base_url": "https://extapi.dcb-dev.vlaanderen.be",
        "token_audience": "https://authenticatie-ti.vlaanderen.be",
    },
    "T&I": {
        "base_url": "https://extapi.dcb-ti.vlaanderen.be",
        "token_audience": "https://authenticatie-ti.vlaanderen.be",
    },
    "Prod": {
        "base_url": "https://extapi.dcb.vlaanderen.be",
        "token_audience": "https://authenticatie.vlaanderen.be",
    },
}

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
        log_and_popup("Kon instellingen niet opslaan", str(e))

class JWTApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")  # andere opties: "cyborg", "superhero", "solar"
        self.title(APP_TITLE)
        self.geometry("1000x980")
        self.minsize(880, 860)

        # ==== State ====
        self.key_path = tk.StringVar()
        self.key_password = tk.StringVar()

        # Issuer/Subject/Audience (aud is de token-audience host)
        self.issuer = tk.StringVar()  # iss
        self.sub = tk.StringVar()     # sub
        self.aud = tk.StringVar()     # aud (host, bv. https://authenticatie-ti.vlaanderen.be)

        # centrale base URL (Postman {{url}})
        self.base_url = tk.StringVar()

        # token audience voor /op/v1/token (form 'audience' param; host)
        self.token_audience = tk.StringVar()

        self.iat = tk.IntVar(value=int(time.time()))
        self.exp = tk.IntVar(value=int(time.time()) + DEFAULT_EXP_OFFSET)
        self.exp_offset = tk.IntVar(value=DEFAULT_EXP_OFFSET)
        self.link_exp = tk.BooleanVar(value=True)

        self.alg = tk.StringVar(value="RS256")
        self.kid = tk.StringVar()  # optioneel header veld

        self.last_access_token = None  # onthoud het laatst opgehaalde access token

        # Environment selectie
        self.env_selected = tk.StringVar(value="Dev")

        # Config laden en defaults zetten
        self.cfg = load_config()
        self._apply_config_defaults()

        self._build_ui()
        self._bind_events()

    def _apply_config_defaults(self):
        # Omgeving
        env = self.cfg.get("environment", "Dev")
        if env not in ENVIRONMENTS:
            env = "Dev"
        self.env_selected.set(env)
        env_cfg = ENVIRONMENTS.get(env, ENVIRONMENTS["Dev"])

        # Issuer / Subject / Audience (aud = host)
        self.issuer.set(self.cfg.get("issuer", "DCB Tool"))
        self.sub.set(self.cfg.get("sub", self.cfg.get("iss_sub", "612bf17a-ebb0-45c3-9225-d04f1067a0b0")))
        default_aud = self.cfg.get("aud", env_cfg["token_audience"])
        self.aud.set(default_aud)

        # {{url}} en token_audience volgens environment (kan nadien handmatig aangepast worden)
        self.base_url.set(self.cfg.get("base_url", env_cfg["base_url"]))
        self.token_audience.set(self.cfg.get("token_audience", env_cfg["token_audience"]))

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
        self.kid.set(self.cfg.get("kid", ""))

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        # Omgeving + Centrale instellingen
        top = ttk.LabelFrame(self, text="Omgeving & Centrale instellingen")
        top.pack(fill="x", **pad)

        # Environment radios
        env_frame = ttk.Frame(top)
        env_frame.grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(env_frame, text="Omgeving:").pack(side="left", padx=(0,8))
        for name in ["Dev", "T&I", "Prod"]:
            ttk.Radiobutton(env_frame, text=name, value=name, variable=self.env_selected, command=self.on_env_change).pack(side="left", padx=4)

        ttk.Label(top, text="Base URL ({{url}}):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.base_url, width=70).grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(top, text="Token audience (host):").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.token_audience, width=70).grid(row=2, column=1, sticky="ew", **pad)
        top.columnconfigure(1, weight=1)

        # JWT Claims
        frm_top = ttk.LabelFrame(self, text="JWT Claims")
        frm_top.pack(fill="x", **pad)

        ttk.Label(frm_top, text="Issuer (iss) — naam:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm_top, textvariable=self.issuer, width=60).grid(row=0, column=1, columnspan=3, sticky="ew", **pad)

        ttk.Label(frm_top, text="Subject (sub) — client-id:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm_top, textvariable=self.sub, width=60).grid(row=1, column=1, columnspan=3, sticky="ew", **pad)

        ttk.Label(frm_top, text="Audience (aud) — token audience (host):").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(frm_top, textvariable=self.aud, width=60).grid(row=2, column=1, columnspan=3, sticky="ew", **pad)

        ttk.Label(frm_top, text="iat (Issued At, epoch):").grid(row=3, column=0, sticky="w", **pad)
        self.iat_entry = ttk.Entry(frm_top, textvariable=self.iat, width=20)
        self.iat_entry.grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(frm_top, text="exp (Expiration, epoch):").grid(row=4, column=0, sticky="w", **pad)
        self.exp_entry = ttk.Entry(frm_top, textvariable=self.exp, width=20)
        self.exp_entry.grid(row=4, column=1, sticky="w", **pad)

        link_cb = ttk.Checkbutton(frm_top, text="Houd exp = iat + offset (sec)", variable=self.link_exp, command=self.sync_exp)
        link_cb.grid(row=3, column=2, sticky="w", **pad)
        ttk.Spinbox(frm_top, from_=5, to=86400, textvariable=self.exp_offset, width=10, command=self.sync_exp).grid(row=3, column=3, sticky="w", **pad)

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

        # JWK Generator
        gen = ttk.LabelFrame(self, text="JWK sleutelpaar genereren")
        gen.pack(fill="x", **pad)
        ttk.Label(gen, text="Genereert een RSA-2048 sleutelpaar met 'use': 'sig' en 'alg': 'RS256'.").grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Button(gen, text="Genereer JWK keypair…", command=self.generate_jwk_keypair).grid(row=1, column=0, sticky="w", **pad)

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
    def on_env_change(self):
        """Bij wijzigen van omgeving -> vul Base URL, Token Audience en aud (host) automatisch in."""
        env = self.env_selected.get()
        cfg = ENVIRONMENTS.get(env, ENVIRONMENTS["Dev"])
        self.base_url.set(cfg["base_url"])
        self.token_audience.set(cfg["token_audience"])
        # aud claim = host (geen /op)
        self.aud.set(cfg["token_audience"])

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
                log_and_popup("Ongeldige exp", "exp moet groter zijn dan iat.")
        except Exception:
            pass

    def save_current_config(self):
        self.cfg.update({
            "issuer": self.issuer.get().strip(),
            "sub": self.sub.get().strip(),
            "aud": self.aud.get().strip(),
            "kid": self.kid.get().strip(),
            "exp_offset": int(self.exp_offset.get()),
            "link_exp": bool(self.link_exp.get()),
            "alg": self.alg.get(),
            "key_path": self.key_path.get().strip(),
            "base_url": self.base_url.get().strip(),
            "token_audience": self.token_audience.get().strip(),
            "environment": self.env_selected.get(),
            "exp": int(self.exp.get()) if not self.link_exp.get() else None,
        })
        # Verwijder legacy sleutel indien nog aanwezig
        if "iss_sub" in self.cfg:
            self.cfg.pop("iss_sub", None)

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
                key = jwk.JWK.from_json(data_text)

                # kid overnemen of thumbprint gebruiken
                try:
                    exported = key.export(as_dict=True)
                    data = exported if isinstance(exported, dict) else json.loads(exported)
                    if not self.kid.get().strip():
                        kid_val = data.get("kid") or key.thumbprint()
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

        iss_val = self.issuer.get().strip()
        sub_val = self.sub.get().strip()
        aud_val = self.aud.get().strip()

        if not iss_val:
            raise ValueError("Vul 'Issuer (iss)' in.")
        if not sub_val:
            raise ValueError("Vul 'Subject (sub)' in.")
        if not aud_val:
            raise ValueError("Vul 'Audience (aud)' (host) in.")

        claims = {
            "iss": iss_val,
            "sub": sub_val,
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
            log_and_popup("Fout bij genereren", str(e))
        except Exception as e:
            log_and_popup("Onbekende fout", repr(e))

    # -------------- Token endpoint call --------------
    def ask_access_token(self):
        # 'audience' (form param) blijft de kale host, fallback op sub
        audience = (self.token_audience.get().strip() or self.sub.get().strip())
        client_assertion = self.jwt_text.get("1.0", "end").strip()

        if not client_assertion or client_assertion.count(".") != 2:
            messagebox.showwarning("Geen JWT", "Genereer eerst de JWT (client_assertion).")
            return
        if not audience:
            messagebox.showwarning("Ontbrekende audience", "Vul 'Token audience' of 'Subject (sub)' in.")
            return

        # Token endpoint URL per omgeving
        url = "https://authenticatie-ti.vlaanderen.be/op/v1/token" if self.env_selected.get() in ["Dev", "T&I"] else "https://authenticatie.vlaanderen.be/op/v1/token"
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
            debug_file = Path(__file__).with_name(".debug_context.json")
            ctx = {
                "access_token": self.last_access_token,
                "base_url": self.base_url.get().strip()
            }
            debug_file.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
            print("[DEBUG] Context written to", debug_file)
            # =====================================

        except Exception as e:
            log_and_popup("Fout bij token aanvraag", str(e))

    # -------------- JWK Generation --------------
    def generate_jwk_keypair(self):
        """Genereer een RSA-2048 JWK keypair en sla beide JSON-bestanden op.
        - private: bevat d, p, q, etc. + 'use': 'sig', 'alg': 'RS256', 'kid'
        - public:  enkel n, e + dezelfde 'use', 'alg', 'kid'
        """
        # Kies doel-bestandsnaam (we leiden map af, en maken 2 bestanden)
        target = filedialog.asksaveasfilename(
            title="Sla JWK sleutelpaar op als… (kies bestandsnaam zonder extensie)",
            defaultextension=".jwk",
            initialfile="client-key.jwk",
            filetypes=[("JWK JSON", "*.jwk *.json"), ("Alle bestanden", "*.*")],
        )
        if not target:
            return

        try:
            # Generate RSA-2048 key
            key = jwk.JWK.generate(kty='RSA', size=2048)
            kid = key.thumbprint()

            # Zorg dat metadata aanwezig is
            exported = key.export(as_dict=True)
            priv_obj = exported if isinstance(exported, dict) else json.loads(exported)
            priv_obj["use"] = "sig"
            priv_obj["alg"] = "RS256"
            priv_obj["kid"] = priv_obj.get("kid", kid)

            # Public part
            pub = jwk.JWK()
            pub.import_key(**{k: v for k, v in priv_obj.items() if k in ("kty", "n", "e")})
            exported_pub = pub.export(as_dict=True)
            pub_obj = exported_pub if isinstance(exported_pub, dict) else json.loads(exported_pub)
            pub_obj["use"] = "sig"
            pub_obj["alg"] = "RS256"
            pub_obj["kid"] = priv_obj["kid"]

            # Bestandsnamen
            base = Path(target)
            if base.suffix.lower() not in [".jwk", ".json"]:
                base = base.with_suffix(".jwk")
            private_path = base
            public_path = base.with_name(base.stem + ".public" + base.suffix)

            private_path.write_text(json.dumps(priv_obj, indent=2), encoding="utf-8")
            public_path.write_text(json.dumps(pub_obj, indent=2), encoding="utf-8")

            self.key_path.set(str(private_path))
            self.kid.set(priv_obj["kid"])

            messagebox.showinfo(
                "JWK aangemaakt",
                f"Private key:\n{private_path}\n\nPublic key:\n{public_path}\n\nkid: {priv_obj['kid']}"
            )
        except Exception as e:
            log_and_popup("Kon JWK niet genereren", str(e))

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
            log_and_popup("Bestand ontbreekt", f"application_gui.py niet gevonden in:\n{app_gui_path.parent}")
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
            log_and_popup("Kon Application GUI niet openen", repr(e))

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
            log_and_popup("Bestand ontbreekt", f"certificates_gui.py niet gevonden in:\n{cert_gui_path.parent}")
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
            log_and_popup("Kon Certificates GUI niet openen", repr(e))



if __name__ == "__main__":
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = JWTApp()
    app.mainloop()
