import json
import os
import time
import traceback
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog
import webbrowser
from urllib.parse import urlparse, parse_qs
from email.utils import parsedate_to_datetime  # voor Date-header -> datetime

import jwt
import requests
from jwt.algorithms import RSAAlgorithm  # voor JWK -> key object

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROFILES_FILE = "jwt_builder_profiles.json"

DEFAULT_PROFILE_TEMPLATE = {
    "postman_api_key": "",
    "share_url": "",
    "environment_uid": "",
    "default_jwk_path": "",
    "last_env": "TI",          # "TI" of "PROD"
    "tls_ignore_verify": True, # standaard: TLS verificatie negeren (verify=False)
    "tls_ca_path": ""          # pad naar CA-certificaat als verificatie aan staat
}

AUDIENCE_MAP = {
    "TI": "https://authenticatie-ti.vlaanderen.be/op",
    "PROD": "https://authenticatie.vlaanderen.be/op",
}

# Thema
BG = "black"
FG_LABEL = "yellow"
FG_ENTRY = "white"
BTN_BG = "#333333"
BTN_ACTIVE_BG = "#555555"
FONT = ("Segoe UI", 14)


def load_profiles():
    """Laadt alle profielen uit één JSON-bestand."""
    if not os.path.exists(PROFILES_FILE):
        data = {"last_profile": None, "profiles": {}}
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("[ERROR] Fout bij lezen van profiles-bestand, nieuw bestand wordt aangemaakt.")
        traceback.print_exc()
        data = {"last_profile": None, "profiles": {}}
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    if "profiles" not in data or not isinstance(data["profiles"], dict):
        data["profiles"] = {}
    if "last_profile" not in data:
        data["last_profile"] = None

    # Merge met default template per profiel
    fixed_profiles = {}
    for name, prof in data["profiles"].items():
        p = DEFAULT_PROFILE_TEMPLATE.copy()
        for k, v in prof.items():
            if k in p:
                p[k] = v
        fixed_profiles[name] = p

    data["profiles"] = fixed_profiles
    return data


def save_profiles(data):
    """Schrijft alle profielen terug naar disk."""
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        print("[ERROR] Fout bij schrijven van profiles-bestand.")
        traceback.print_exc()


def extract_env_uid_from_share_url(url: str) -> str:
    """Haalt de Postman environment UID uit de share-URL (active-environment=...)."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    env_from_query = qs.get("active-environment", [None])[0]
    if env_from_query:
        return env_from_query
    raise ValueError("Kon geen 'active-environment' parameter vinden in de URL.")


class JWTBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JWT Builder - Client Assertion (profielen, issuer = kid)")
        self.root.configure(bg=BG)
        self.root.option_add("*Font", FONT)

        # Profielen laden
        self.profiles_data = load_profiles()
        self.current_profile_name = self.profiles_data.get("last_profile")

        # Als er nog geen profielen zijn: vraag naam
        if not self.profiles_data["profiles"]:
            name = simpledialog.askstring(
                "Nieuw profiel",
                "Geef een naam voor je eerste profiel (bijv. 'DCBaaS'):",
                parent=self.root,
            )
            if not name:
                name = "default"
            self.profiles_data["profiles"][name] = DEFAULT_PROFILE_TEMPLATE.copy()
            self.profiles_data["last_profile"] = name
            save_profiles(self.profiles_data)
            self.current_profile_name = name

        # Fallback als last_profile ontbreekt
        if not self.current_profile_name:
            if self.profiles_data["profiles"]:
                self.current_profile_name = list(self.profiles_data["profiles"].keys())[0]
                self.profiles_data["last_profile"] = self.current_profile_name
                save_profiles(self.profiles_data)
            else:
                self.current_profile_name = "default"
                self.profiles_data["profiles"][self.current_profile_name] = DEFAULT_PROFILE_TEMPLATE.copy()
                self.profiles_data["last_profile"] = self.current_profile_name
                save_profiles(self.profiles_data)

        # State
        self.jwk_path = None
        self.current_issuer = None  # = kid
        self.profile_var = tk.StringVar(value=self.current_profile_name)
        self.selected_env = tk.StringVar(value=self.get_current_profile().get("last_env", "TI"))
        self.tls_ignore_var = tk.BooleanVar(value=self.get_current_profile().get("tls_ignore_verify", True))

        # --- UI opbouw ---
        row = 0
        info = (
            "Deze tool maakt een JWT (client_assertion) met je JWK private key.\n"
            "Issuer en Subject worden automatisch gezet op de 'kid' uit de JWK.\n"
            "Audience: T&I of PROD (zelfde Postman environment)."
        )
        tk.Label(self.root, text=info, justify="left", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, columnspan=4, sticky="w", padx=5, pady=5
        )
        row += 1

        # Profiel selectie
        tk.Label(self.root, text="Profiel:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )

        self.profile_menu = tk.OptionMenu(
            self.root,
            self.profile_var,
            *self.profiles_data["profiles"].keys(),
            command=self.on_profile_change
        )
        self.profile_menu.configure(bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG,
                                    activeforeground=FG_LABEL, highlightthickness=0)
        self.profile_menu["menu"].config(bg=BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG)
        self.profile_menu.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="Nieuw profiel", command=self.new_profile,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=2, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="Profiel opslaan", command=self.save_current_profile_and_file,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=3, sticky="w", padx=5, pady=5)
        row += 1

        # JWK
        tk.Label(self.root, text="JWK private key bestand:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        tk.Button(
            self.root, text="Kies JWK bestand...", command=self.choose_jwk,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)

        self.jwk_label = tk.Label(self.root, text="Geen bestand gekozen", bg=BG, fg=FG_LABEL)
        self.jwk_label.grid(row=row, column=2, columnspan=2, sticky="w", padx=5, pady=5)
        row += 1

        # Issuer / Subject (readonly)
        tk.Label(self.root, text="Issuer / Subject (kid uit JWK):", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.iss_entry = tk.Entry(self.root, width=60, state="readonly",
                                  bg=BG, fg=FG_ENTRY, insertbackground=FG_ENTRY)
        self.iss_entry.grid(row=row, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        row += 1

        # Audience / Environment keuze
        tk.Label(self.root, text="Audience / Environment:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        tk.Radiobutton(
            self.root,
            text="T&I (https://authenticatie-ti.vlaanderen.be/op)",
            variable=self.selected_env,
            value="TI",
            command=self.on_env_change,
            bg=BG,
            fg=FG_LABEL,
            selectcolor=BG,
            activebackground=BG,
            activeforeground=FG_LABEL,
        ).grid(row=row, column=1, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1

        tk.Radiobutton(
            self.root,
            text="PROD (https://authenticatie.vlaanderen.be/op)",
            variable=self.selected_env,
            value="PROD",
            command=self.on_env_change,
            bg=BG,
            fg=FG_LABEL,
            selectcolor=BG,
            activebackground=BG,
            activeforeground=FG_LABEL,
        ).grid(row=row, column=1, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1

        # TLS checkbox + CA-pad
        tk.Label(self.root, text="TLS verificatie:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.tls_check = tk.Checkbutton(
            self.root,
            text="TLS verificatie negeren (verify=False)",
            variable=self.tls_ignore_var,
            onvalue=True,
            offvalue=False,
            command=self.on_tls_ignore_change,
            bg=BG,
            fg=FG_LABEL,
            selectcolor=BG,
            activebackground=BG,
            activeforeground=FG_LABEL,
        )
        self.tls_check.grid(row=row, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        row += 1

        tk.Label(self.root, text="CA-certificaat (PEM) voor TLS:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.ca_entry = tk.Entry(self.root, width=60,
                                 bg=BG, fg=FG_ENTRY, insertbackground=FG_ENTRY)
        self.ca_entry.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="Kies CA bestand...", command=self.choose_ca_file,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=2, sticky="w", padx=5, pady=5)
        row += 1

        # API key
        tk.Label(self.root, text="Postman API key:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.api_key_entry = tk.Entry(self.root, width=60, show="*",
                                      bg=BG, fg=FG_ENTRY, insertbackground=FG_ENTRY)
        self.api_key_entry.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="API key pagina openen", command=self.open_postman_api_keys,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=2, sticky="w", padx=5, pady=5)
        row += 1

        # Share URL + UID
        tk.Label(self.root, text="Postman share URL (environment):", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.share_url_entry = tk.Entry(self.root, width=60,
                                        bg=BG, fg=FG_ENTRY, insertbackground=FG_ENTRY)
        self.share_url_entry.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="Uit URL UID halen", command=self.extract_and_fill_env_uid,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=2, sticky="w", padx=5, pady=5)
        row += 1

        tk.Label(self.root, text="Environment UID:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.env_uid_entry = tk.Entry(self.root, width=60,
                                      bg=BG, fg=FG_ENTRY, insertbackground=FG_ENTRY)
        self.env_uid_entry.grid(row=row, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        row += 1

        # Klok + tijd-offset
        tk.Label(self.root, text="Systeemklok:", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.time_label = tk.Label(self.root, text="", bg=BG, fg=FG_LABEL)
        self.time_label.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="Check server tijd (Postman)", command=self.check_internet_time,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=2, sticky="w", padx=5, pady=5)

        tk.Button(
            self.root, text="Windows tijd resync (w32tm)", command=self.resync_windows_time,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=3, sticky="w", padx=5, pady=5)

        row += 1
        self.time_drift_label = tk.Label(self.root, text="", bg=BG, fg=FG_LABEL)
        self.time_drift_label.grid(row=row, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        row += 1

        # Buttons
        tk.Button(
            self.root, text="Create JWT & Update Postman", command=self.create_jwt,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=0, sticky="w", padx=5, pady=10)

        tk.Button(
            self.root, text="Copy JWT naar klembord", command=self.copy_jwt,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=1, sticky="w", padx=5, pady=10)

        tk.Button(
            self.root, text="Profiel opslaan", command=self.save_current_profile_and_file,
            bg=BTN_BG, fg=FG_LABEL, activebackground=BTN_ACTIVE_BG, activeforeground=FG_LABEL
        ).grid(row=row, column=2, sticky="w", padx=5, pady=10)
        row += 1

        # Output
        tk.Label(self.root, text="Gegenereerde JWT (Client_assertion):", bg=BG, fg=FG_LABEL).grid(
            row=row, column=0, sticky="nw", padx=5, pady=5
        )
        row += 1

        self.output_text = scrolledtext.ScrolledText(
            self.root, width=100, height=10,
            bg=BG, fg=FG_ENTRY, insertbackground=FG_ENTRY
        )
        self.output_text.grid(row=row, column=0, columnspan=4, padx=5, pady=5)
        row += 1

        # Status
        self.status_label = tk.Label(self.root, text="", bg=BG, fg=FG_LABEL)
        self.status_label.grid(row=row, column=0, columnspan=4, sticky="w", padx=5, pady=5)

        # Velden vullen vanuit huidig profiel
        self.load_profile_into_fields()

        # Klok starten
        self.update_clock()

    # ---------- Profiel helpers ----------

    def get_current_profile(self):
        return self.profiles_data["profiles"].get(self.current_profile_name, DEFAULT_PROFILE_TEMPLATE.copy())

    def on_profile_change(self, selected_name):
        self.current_profile_name = selected_name
        self.profiles_data["last_profile"] = selected_name
        save_profiles(self.profiles_data)
        print(f"[DEBUG] Profiel gewijzigd naar: {selected_name}")
        self.load_profile_into_fields()

    def new_profile(self):
        name = simpledialog.askstring(
            "Nieuw profiel",
            "Geef een naam voor het nieuwe profiel:",
            parent=self.root
        )
        if not name:
            return
        if name in self.profiles_data["profiles"]:
            messagebox.showerror("Fout", f"Profiel '{name}' bestaat al.")
            return

        self.profiles_data["profiles"][name] = DEFAULT_PROFILE_TEMPLATE.copy()
        self.profiles_data["last_profile"] = name
        self.current_profile_name = name
        save_profiles(self.profiles_data)

        # Dropdown updaten
        menu = self.profile_menu["menu"]
        menu.delete(0, "end")
        for prof_name in self.profiles_data["profiles"].keys():
            menu.add_command(label=prof_name, command=lambda v=prof_name: self.profile_var.set(v))
        self.profile_var.set(name)

        self.load_profile_into_fields()
        print(f"[DEBUG] Nieuw profiel aangemaakt: {name}")

    def load_profile_into_fields(self):
        prof = self.get_current_profile()

        # JWK pad
        default_jwk = prof.get("default_jwk_path")
        if default_jwk and os.path.exists(default_jwk):
            self.jwk_path = default_jwk
            self.jwk_label.config(text=default_jwk, fg=FG_LABEL)
            self.update_issuer_from_jwk()
        elif default_jwk:
            self.jwk_label.config(text=f"Bestand niet gevonden: {default_jwk}", fg="red")
            self.jwk_path = None
            self.set_issuer_field(None)
        else:
            self.jwk_label.config(text="Geen bestand gekozen", fg=FG_LABEL)
            self.jwk_path = None
            self.set_issuer_field(None)

        # Env keuze
        self.selected_env.set(prof.get("last_env", "TI"))

        # TLS instellingen
        self.tls_ignore_var.set(prof.get("tls_ignore_verify", True))
        self.ca_entry.delete(0, tk.END)
        self.ca_entry.insert(0, prof.get("tls_ca_path", ""))

        # API key, URL, UID
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, prof.get("postman_api_key", ""))

        self.share_url_entry.delete(0, tk.END)
        self.share_url_entry.insert(0, prof.get("share_url", ""))

        self.env_uid_entry.delete(0, tk.END)
        self.env_uid_entry.insert(0, prof.get("environment_uid", ""))

        self.status_label.config(text=f"Profiel geladen: {self.current_profile_name}", fg=FG_LABEL)

    def save_current_profile_and_file(self):
        prof = self.get_current_profile()

        prof["default_jwk_path"] = self.jwk_path or ""
        prof["last_env"] = self.selected_env.get()
        prof["postman_api_key"] = self.api_key_entry.get().strip()
        prof["share_url"] = self.share_url_entry.get().strip()
        prof["environment_uid"] = self.env_uid_entry.get().strip()
        prof["tls_ignore_verify"] = self.tls_ignore_var.get()
        prof["tls_ca_path"] = self.ca_entry.get().strip()

        self.profiles_data["profiles"][self.current_profile_name] = prof
        self.profiles_data["last_profile"] = self.current_profile_name
        save_profiles(self.profiles_data)
        self.status_label.config(text="Profiel opgeslagen.", fg=FG_LABEL)
        print(f"[DEBUG] Profiel opgeslagen: {self.current_profile_name} -> {prof}")

    # ---------- Issuer helpers ----------

    def set_issuer_field(self, value: str | None):
        self.iss_entry.config(state="normal")
        self.iss_entry.delete(0, tk.END)
        if value:
            self.iss_entry.insert(0, value)
        self.iss_entry.config(state="readonly")

    def update_issuer_from_jwk(self):
        if not self.jwk_path:
            self.current_issuer = None
            self.set_issuer_field(None)
            return

        try:
            with open(self.jwk_path, "r", encoding="utf-8") as f:
                jwk_dict = json.load(f)
            kid = jwk_dict.get("kid")
            if not kid:
                raise ValueError("Geen 'kid' gevonden in de JWK.")
            self.current_issuer = kid
            self.set_issuer_field(kid)
            print(f"[DEBUG] Issuer (kid) uit JWK: {kid}")
        except Exception as e:
            print("[ERROR] Kon 'kid' niet uit JWK halen.")
            traceback.print_exc()
            self.current_issuer = None
            self.set_issuer_field(None)
            messagebox.showerror("Fout bij uitlezen JWK", f"Kon 'kid' niet uit de JWK halen:\n{e}")

    # ---------- TLS helpers ----------

    def on_tls_ignore_change(self):
        """Als de checkbox verandert: bij uitzetten meteen CA vragen als er nog geen pad is."""
        ignore = self.tls_ignore_var.get()
        print(f"[DEBUG] TLS ignore verify: {ignore}")
        if not ignore:
            # TLS verificatie AAN -> CA-pad vereist
            current_ca = self.ca_entry.get().strip()
            if not current_ca:
                messagebox.showinfo(
                    "CA-certificaat vereist",
                    "Je hebt TLS verificatie aangezet.\n"
                    "Kies nu een CA-certificaatbestand (PEM/CRT) dat jouw proxy/CA bevat."
                )
                self.choose_ca_file()
                if not self.ca_entry.get().strip():
                    # Gebruik heeft geannuleerd -> terug naar ignore=True
                    messagebox.showwarning(
                        "Geen CA gekozen",
                        "Er is geen CA-bestand gekozen. TLS verificatie negeren blijft aan."
                    )
                    self.tls_ignore_var.set(True)

    def choose_ca_file(self):
        path = filedialog.askopenfilename(
            title="Kies CA certificaatbestand (PEM/CRT)",
            filetypes=[("Certificaten", "*.pem *.crt *.cer"), ("Alle bestanden", "*.*")]
        )
        if path:
            self.ca_entry.delete(0, tk.END)
            self.ca_entry.insert(0, path)
            prof = self.get_current_profile()
            prof["tls_ca_path"] = path
            self.profiles_data["profiles"][self.current_profile_name] = prof
            save_profiles(self.profiles_data)
            print(f"[DEBUG] CA pad gekozen: {path}")

    # ---------- Klok / tijd helpers ----------

    def update_clock(self):
        """Update de systeemklok-label elke seconde."""
        local_time = time.localtime()
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        self.time_label.config(text=time_str)
        self.root.after(1000, self.update_clock)

    def check_internet_time(self):
        """
        Vergelijk lokale tijd met server tijd via de Postman API.
        We lezen de 'Date' header van https://api.getpostman.com/environments/<env_uid>.
        """
        try:
            prof = self.get_current_profile()
            api_key = prof.get("postman_api_key", "").strip()
            env_uid = prof.get("environment_uid", "").strip()
            if not api_key or not env_uid:
                raise RuntimeError(
                    "Geen Postman API key of environment UID ingesteld.\n"
                    "Vul die eerst in en sla het profiel op."
                )

            # Zelfde TLS-instellingen als de rest
            tls_ignore = prof.get("tls_ignore_verify", True)
            ca_path = prof.get("tls_ca_path", "").strip()
            if tls_ignore:
                verify_arg = False
            else:
                verify_arg = ca_path if ca_path else True

            url = f"https://api.getpostman.com/environments/{env_uid}"
            headers = {"X-API-Key": api_key}
            print(f"[DEBUG] Server tijd check via {url} (verify={verify_arg})")

            resp = requests.get(url, headers=headers, timeout=10, verify=verify_arg)
            # Ook bij 401/403 heeft de server meestal een Date-header, dus we eisen geen 200.
            date_header = resp.headers.get("Date")
            if not date_header:
                raise RuntimeError(
                    f"Geen 'Date'-header ontvangen (HTTP status {resp.status_code}). "
                    f"Response headers: {resp.headers}"
                )

            # Date-header naar timestamp
            dt = parsedate_to_datetime(date_header)  # timezone-aware
            internet_ts = dt.timestamp()
            local_ts = time.time()
            diff = local_ts - internet_ts  # positief = lokale klok loopt VOOR

            diff_rounded = round(diff, 1)
            if diff_rounded > 0:
                msg = f"Systeemklok loopt {diff_rounded} seconden VOOR op Postman-server tijd."
            elif diff_rounded < 0:
                msg = f"Systeemklok loopt {abs(diff_rounded)} seconden ACHTER op Postman-server tijd."
            else:
                msg = "Systeemklok lijkt exact gelijk met Postman-server tijd."

            self.time_drift_label.config(text=msg)
            print("[DEBUG] Time drift:", msg)
            messagebox.showinfo("Server tijd check", msg)

        except Exception as e:
            print("[ERROR] Fout bij server tijd check.")
            traceback.print_exc()
            messagebox.showerror(
                "Fout bij server tijd",
                f"Kon server tijd niet bepalen:\n{e}"
            )

    def resync_windows_time(self):
        """Probeert Windows tijd te resyncen via w32tm /resync."""
        try:
            completed = subprocess.run(
                ["w32tm", "/resync"],
                capture_output=True,
                text=True,
                shell=False
            )
            if completed.returncode == 0:
                msg = "Windows tijd resync opdracht succesvol uitgevoerd."
                print("[DEBUG] w32tm /resync OK:", completed.stdout)
                messagebox.showinfo("Tijd resync", msg)
            else:
                msg = (
                    f"w32tm /resync faalde (code {completed.returncode}).\n\n"
                    f"Output:\n{completed.stdout}\n\nError:\n{completed.stderr}"
                )
                print("[ERROR] w32tm /resync failed:", msg)
                messagebox.showerror("Tijd resync fout", msg)
        except FileNotFoundError:
            messagebox.showerror(
                "Tijd resync fout",
                "w32tm commando niet gevonden. Dit werkt enkel op Windows met de tijdservice actief."
            )
        except Exception as e:
            print("[ERROR] Onbekende fout bij w32tm /resync.")
            traceback.print_exc()
            messagebox.showerror(
                "Tijd resync fout",
                f"Onbekende fout bij uitvoeren van w32tm /resync:\n{e}"
            )

    # ---------- GUI acties ----------

    def choose_jwk(self):
        path = filedialog.askopenfilename(
            title="Kies JWK private key bestand",
            filetypes=[("JSON files", "*.json;*.jwk"), ("Alle bestanden", "*.*")]
        )
        if path:
            self.jwk_path = path
            self.jwk_label.config(text=path, fg=FG_LABEL)
            prof = self.get_current_profile()
            prof["default_jwk_path"] = path
            self.profiles_data["profiles"][self.current_profile_name] = prof
            save_profiles(self.profiles_data)
            self.update_issuer_from_jwk()

    def on_env_change(self):
        print(f"[DEBUG] Environment selectie: {self.selected_env.get()}")

    def open_postman_api_keys(self):
        url = "https://web.postman.co/settings/me/api-keys"
        webbrowser.open(url)

    def extract_and_fill_env_uid(self):
        url = self.share_url_entry.get().strip()
        if not url:
            messagebox.showerror("Fout", "Vul eerst een Postman share URL in.")
            return

        try:
            env_uid = extract_env_uid_from_share_url(url)
            print(f"[DEBUG] Environment UID uit URL: {env_uid}")
        except Exception as e:
            print("[ERROR] Kon environment UID niet uit URL halen.")
            traceback.print_exc()
            messagebox.showerror("Fout", f"Kon geen environment UID uit de URL halen:\n{e}")
            return

        self.env_uid_entry.delete(0, tk.END)
        self.env_uid_entry.insert(0, env_uid)

        prof = self.get_current_profile()
        prof["environment_uid"] = env_uid
        self.profiles_data["profiles"][self.current_profile_name] = prof
        save_profiles(self.profiles_data)

        self.status_label.config(text="Environment UID uit URL gehaald en opgeslagen.", fg=FG_LABEL)

    def copy_jwt(self):
        """Kopieert de huidige JWT uit het tekstvak naar het klembord."""
        jwt_text = self.output_text.get("1.0", tk.END).strip()
        if not jwt_text:
            messagebox.showwarning(
                "Geen JWT",
                "Er staat nog geen JWT in het veld om te kopiëren."
            )
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(jwt_text)
        self.root.update()
        self.status_label.config(text="JWT gekopieerd naar klembord.", fg=FG_LABEL)
        print("[DEBUG] JWT gekopieerd naar klembord.")

    def create_jwt(self):
        self.status_label.config(text="", fg=FG_LABEL)

        # Profiel bewaren
        self.save_current_profile_and_file()
        prof = self.get_current_profile()

        api_key = prof.get("postman_api_key", "").strip()
        if not api_key:
            messagebox.showerror("Config fout", "Geen Postman API key ingevuld in dit profiel.")
            return

        env_uid = prof.get("environment_uid", "").strip()
        if not env_uid:
            messagebox.showerror(
                "Config fout",
                "Geen environment UID ingevuld. Vul de share URL in en klik op 'Uit URL UID halen'."
            )
            return

        if not self.jwk_path:
            messagebox.showerror("Fout", "Kies eerst een JWK private key bestand.")
            return

        if not self.current_issuer:
            self.update_issuer_from_jwk()
            if not self.current_issuer:
                messagebox.showerror("Fout", "Kon geen issuer (kid) uit de JWK halen.")
                return

        iss = self.current_issuer
        env_key = self.selected_env.get()
        aud = AUDIENCE_MAP.get(env_key)
        if not aud:
            messagebox.showerror("Fout", "Onbekende environment selectie.")
            return

        # kleine negatieve skew om 'iat in the future' te vermijden
        now = int(time.time()) - 10
        exp = now + 10 * 60  # 10 minuten geldig

        payload = {
            "iss": iss,
            "sub": iss,
            "iat": now,
            "exp": exp,
            "aud": aud,
        }

        print("[DEBUG] JWT payload:", payload)

        try:
            with open(self.jwk_path, "r", encoding="utf-8") as f:
                jwk_dict = json.load(f)

            jwk_json = json.dumps(jwk_dict)
            key = RSAAlgorithm.from_jwk(jwk_json)

            headers = {"typ": "JWT", "alg": "RS256"}
            kid = jwk_dict.get("kid")
            if kid:
                headers["kid"] = kid
            print("[DEBUG] JWT headers:", headers)

            token = jwt.encode(payload, key, algorithm="RS256", headers=headers)
            print("[DEBUG] JWT succesvol gegenereerd.")

        except Exception as e:
            print("[ERROR] Fout bij JWT genereren.")
            traceback.print_exc()
            messagebox.showerror("Fout bij JWT genereren", f"Er ging iets mis bij het maken van de JWT:\n{e}")
            return

        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, token)

        # TLS verify-param bepalen
        tls_ignore = prof.get("tls_ignore_verify", True)
        ca_path = prof.get("tls_ca_path", "").strip()
        if tls_ignore:
            verify_arg = False
            print("[DEBUG] TLS verificatie UIT (verify=False)")
        else:
            verify_arg = ca_path if ca_path else True
            print(f"[DEBUG] TLS verificatie AAN, verify={verify_arg}")

        try:
            self.update_postman_environment_cloud(api_key, env_uid, token, verify_arg)
            self.status_label.config(
                text=f"JWT succesvol naar Postman environment gestuurd (audience: {env_key}).",
                fg=FG_LABEL
            )
            messagebox.showinfo(
                "Succes",
                f"JWT (Client_assertion) is aangemaakt en in de Postman Cloud environment geschreven.\n"
                f"Audience: {aud}\nIssuer/Sub (kid): {iss}"
            )
        except Exception as e:
            print("[ERROR] Fout bij updaten van Postman environment.")
            traceback.print_exc()
            self.status_label.config(
                text="Fout bij updaten van Postman environment.",
                fg="red"
            )
            messagebox.showerror(
                "Fout bij Postman update",
                f"De JWT is wel gegenereerd, maar het updaten van de Postman environment mislukte:\n{e}"
            )

    def update_postman_environment_cloud(self, api_key, env_uid, token, verify_arg):
        base_url = "https://api.getpostman.com/environments/" + env_uid
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        print(f"[DEBUG] GET {base_url} (verify={verify_arg})")
        resp = requests.get(base_url, headers=headers, timeout=15, verify=verify_arg)
        print("[DEBUG] GET status:", resp.status_code)
        if resp.status_code != 200:
            print("[ERROR] GET environment failed:", resp.status_code, resp.text)
            raise RuntimeError(f"GET environment failed: {resp.status_code} - {resp.text}")

        data = resp.json()
        env = data.get("environment")
        if not env:
            raise RuntimeError("Ongeldig environment object in Postman response.")

        values = env.get("values", [])
        found = False
        for item in values:
            if item.get("key") == "Client_assertion":
                item["value"] = token
                item["enabled"] = True
                found = True
                break

        if not found:
            values.append(
                {
                    "key": "Client_assertion",
                    "value": token,
                    "enabled": True,
                    "type": "default"
                }
            )
        env["values"] = values

        payload = {"environment": env}
        print(f"[DEBUG] PUT {base_url} (verify={verify_arg})")
        resp_put = requests.put(base_url, headers=headers, json=payload, timeout=15, verify=verify_arg)
        print("[DEBUG] PUT status:", resp_put.status_code)
        if resp_put.status_code not in (200, 201):
            print("[ERROR] PUT environment failed:", resp_put.status_code, resp_put.text)
            raise RuntimeError(f"PUT environment failed: {resp_put.status_code} - {resp_put.text}")


if __name__ == "__main__":
    root = tk.Tk()
    app = JWTBuilderApp(root)
    root.mainloop()
