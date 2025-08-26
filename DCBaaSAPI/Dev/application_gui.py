import argparse
import json
import requests
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox


APP_TITLE = "DCBaaS Application Manager"

AUTH_SCHEMES = [
    "Bearer <token>",     # Authorization: Bearer <token>
    "Raw token only",     # Authorization: <token>  (of in custom header)
    "DCB <token>",        # Authorization: DCB <token>
]

def build_auth_value(token: str, scheme: str, header_name: str) -> str:
    """Maak de header-waarde. Voor 'Raw token only' strippen we NIET,
    zodat je exact kan plakken wat Postman stuurt (incl. eventueel 'Bearer ' of 'DCB ')."""
    t = (token or "").strip()
    if scheme == "Raw token only":
        return t
    # Voor de schema-opties strippen we eerst een eventuele bestaande prefix
    low = t.lower()
    if low.startswith("bearer "):
        t = t[7:].strip()
    if low.startswith("dcb "):
        t = t[4:].strip()
    if scheme == "DCB <token>":
        return f"DCB {t}"
    return f"Bearer {t}"

class AppGUI(ttk.Window):
    def __init__(self, base_url="", token="", auth_scheme="Bearer <token>", origin="localhost"):
        super().__init__(themename="darkly")  # andere optie: "cyborg", "superhero", "solar"
        self.title(APP_TITLE)
        self.geometry("900x740")
        self.minsize(820, 600)

        # State
        self.token_var = tk.StringVar(value=token)
        from pathlib import Path
        import json

        debug_file = Path(__file__).with_name(".debug_context.json")
        self._base_url = ""  # default
        if debug_file.exists():
            try:
                ctx = json.loads(debug_file.read_text(encoding="utf-8"))
                expected_token = ctx.get("access_token", "")
                self._base_url = ctx.get("base_url", "")
                print("[DEBUG] application_gui.py loaded context:")
                print("       expected_token(first 50):", expected_token[:50], "...")
                print("       token_received(first 50):", token[:50], "...")
                print("       base_url:", self._base_url)

                if expected_token == token:
                    print("[DEBUG] ✅ Token matches exactly with jwt_gui.py")
                else:
                    print("[DEBUG] ❌ Token mismatch!")
            except Exception as e:
                print("[DEBUG] Could not read context file:", e)


        # Common fields
        self.app_name_var = tk.StringVar()
        self.reason_var = tk.StringVar()
        self.org_code_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="1")  # for delegate
        # statusbalk (onderaan)
        self.status_var = tk.StringVar(value="")


        # interne referentie voor token entry (voor show/hide)
        self._token_entry = None
        self._token_hidden = True

        self.create_widgets()

    def flash_button(self, button, success=True):
        """
        Verander tijdelijk de kleur van een knop.
        - success=True  -> groen
        - success=False -> rood
        """
        if success:
            button.config(bootstyle="success")
        else:
            button.config(bootstyle="danger")

        # Na 1,5 sec terug naar standaard
        self.after(1500, lambda: button.config(bootstyle="secondary"))
        

    def create_widgets(self):
        pad = {"padx": 8, "pady": 6}

        # Config frame
        cfg = ttk.LabelFrame(self, text="Configuratie (moet overeenkomen met Postman)")
        cfg.pack(fill="x", **pad)

        row = 0

        ttk.Label(cfg, text="Access token:").grid(row=row, column=0, sticky="w")
        self._token_entry = ttk.Entry(cfg, textvariable=self.token_var, width=60, show="•")
        self._token_entry.grid(row=row, column=1, sticky="w")
        ttk.Button(cfg, text="Toon/Verberg", command=self.toggle_token_visibility).grid(row=row, column=2, sticky="w")
        row += 1

        # Operations frame
        ops = ttk.LabelFrame(self, text="Application acties")
        ops.pack(fill="x", **pad)

        row = 0
        ttk.Label(ops, text="Application name:").grid(row=row, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.app_name_var, width=50).grid(row=row, column=1, sticky="w")
        ttk.Label(ops, text="bv. dcbaas-ext-api.nu/test1").grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(ops, text="Reason / Description:").grid(row=row, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.reason_var, width=50).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(ops, text="Organization code (delegate):").grid(row=row, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.org_code_var, width=30).grid(row=row, column=1, sticky="w")
        ttk.Label(ops, text="bv. dcbaasbeheer").grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(ops, text="Duration (delegate, maanden):").grid(row=row, column=0, sticky="w")
        ttk.Entry(ops, textvariable=self.duration_var, width=10).grid(row=row, column=1, sticky="w")
        row += 1

        # Separator boven knoppen
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=6)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(6, 0))

        # Links subframe (Add/Update/Delegate/Delete)
        left_frame = ttk.Frame(btns)
        left_frame.pack(side="left", padx=4)

        self.btn_add = ttk.Button(left_frame, text="Add", command=self.do_add)
        self.btn_add.pack(side="left", padx=4)

        self.btn_update = ttk.Button(left_frame, text="Update", command=self.do_update)
        self.btn_update.pack(side="left", padx=4)

        self.btn_delegate = ttk.Button(left_frame, text="Delegate", command=self.do_delegate)
        self.btn_delegate.pack(side="left", padx=4)

        self.btn_delete = ttk.Button(left_frame, text="Delete", command=self.do_delete)
        self.btn_delete.pack(side="left", padx=4)


        # Midden subframe (Health)
        mid_frame = ttk.Frame(btns)
        mid_frame.pack(side="left", padx=12)
        ttk.Button(mid_frame, text="Health", command=self.do_health, bootstyle="success").pack(side="left", padx=4)


        # Rechts subframe (Sluiten)
        right_frame = ttk.Frame(btns)
        right_frame.pack(side="right", padx=4)
        ttk.Button(right_frame, text="Sluiten", command=self.destroy, bootstyle="danger").pack(side="right", padx=4)


        
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.pack(side="bottom", fill="x", pady=2)


        # Output frame
        out = ttk.LabelFrame(self, text="Resultaat / Debug")
        out.pack(fill="both", expand=True, **pad)
        self.output = tk.Text(out, height=22)
        self.output.pack(fill="both", expand=True, padx=6, pady=6)

    def toggle_token_visibility(self):
        self._token_hidden = not self._token_hidden
        self._token_entry.config(show="•" if self._token_hidden else "")

    def log(self, *parts):
        s = " ".join(str(p) for p in parts)
        self.output.insert("end", s + "\n")
        self.output.see("end")

    def _headers(self, is_json=True):
        token = self.token_var.get().strip()

        headers = {
            "Origin": "localhost",
            "Accept": "application/json",
            "Authorization": token  # <-- RAW token, GEEN "Bearer "
        }
        if is_json:
            headers["Content-Type"] = "application/json"

        return headers
    
    def master_base_url(self):
        from pathlib import Path
        import json
        cfg_path = Path.home() / ".jwt_gui_config.json"
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("base_url", "").rstrip("/")
            except Exception:
                return ""
        return ""

    def _post(self, path: str, payload: dict, button=None):
        def task():
            self.status_var.set("⏳ Bezig met POST...")
            base = self.master_base_url()
            url = f"{self._base_url}/dev/{path.lstrip('/')}"

            if not base:
                messagebox.showerror("Fout", "Base URL is leeg.")
                self.status_var.set("")
                if button:
                    self.flash_button(button, success=False)
                return None

            headers = self._headers(is_json=True)
            self._clear_output()
            self.log(f"POST {url}")
            self.log("Body:", json.dumps(payload, ensure_ascii=False))

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                self._log_response(resp)

                if button:
                    if resp.status_code == 200:
                        self.flash_button(button, success=True)
                    else:
                        self.flash_button(button, success=False)

            except requests.RequestException as e:
                self.log("Request error:", e)
                messagebox.showerror("Request error", str(e))
                if button:
                    self.flash_button(button, success=False)

            finally:
                self.status_var.set("")

        threading.Thread(target=task, daemon=True).start()

    def _get(self, path: str):
        def task():
            self.status_var.set("⏳ Bezig met GET...")
            base = self.master_base_url()
            url = f"{self._base_url}/dev/{path.lstrip('/')}"
            if not base:
                messagebox.showerror("Fout", "Base URL is leeg.")
                self.status_var.set("")
                return None

            headers = self._headers(is_json=False)

            self._clear_output()
            self.log(f"GET {url}")

            try:
                resp = requests.get(url, headers=headers, timeout=20)
                self._log_response(resp)
            except requests.RequestException as e:
                self.log("Request error:", e)
                messagebox.showerror("Request error", str(e))
            finally:
                self.status_var.set("")

        threading.Thread(target=task, daemon=True).start()


    def _log_response(self, resp: requests.Response):
        self.log(f"Status: {resp.status_code}")
        try:
            self.log("Response:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
        except Exception:
            self.log("Response (raw):", resp.text)

        # Headers incl. WWW-Authenticate tonen
        try:
            self.log("Headers(resp):", json.dumps(dict(resp.headers), indent=2, ensure_ascii=False))
        except Exception:
            pass
        wa = resp.headers.get("WWW-Authenticate")
        if wa:
            self.log("WWW-Authenticate:", wa)

        if resp.status_code == 401:
            self.log("⚠️ 401 Authorisation failed -> probeer een ander Authorization schema "
                     "en/of kies een andere auth header name (Authorization/authorizationtoken/Both). "
                     "Controleer ook of je token met de juiste audience is opgehaald.")

    def _clear_output(self):
        self.output.delete("1.0", "end")

    # ---- Actions ----
    def do_add(self):
        name = self.app_name_var.get().strip()
        reason = self.reason_var.get().strip() or "API Test"
        if not name:
            messagebox.showerror("Fout", "Vul 'Application name' in.")
            self.flash_button(self.btn_add, success=False)
            return
        payload = {"name": name, "reason": reason}
        self._post("application/add", payload, button=self.btn_add)

    def do_update(self):
        name = self.app_name_var.get().strip()
        reason = self.reason_var.get().strip() or "API aanpassing in informatie"
        if not name:
            messagebox.showerror("Fout", "Vul 'Application name' in.")
            self.flash_button(self.btn_update, success=False)
            return
        payload = {"name": name, "reason": reason}
        self._post("application/update", payload, button=self.btn_update)

    def do_delegate(self):
        name = self.app_name_var.get().strip()
        org_code = self.org_code_var.get().strip()
        duration = self.duration_var.get().strip()
        if not name or not org_code:
            messagebox.showerror("Fout", "Vul 'Application name' en 'Organization code' in.")
            self.flash_button(self.btn_delegate, success=False)
            return
        try:
            duration_i = int(duration)
        except ValueError:
            messagebox.showerror("Fout", "Duration moet een geheel getal zijn (maanden).")
            self.flash_button(self.btn_delegate, success=False)
            return
        payload = {"name": name, "organization_code_delegated": org_code, "duration": duration_i}
        self._post("application/delegate", payload, button=self.btn_delegate)

    def do_delete(self):
        name = self.app_name_var.get().strip()
        if not name:
            messagebox.showerror("Fout", "Vul 'Application name' in.")
            self.flash_button(self.btn_delete, success=False)
            return
        payload = {"name": name}
        self._post("application/delete", payload, button=self.btn_delete)


    def do_health(self):
        # GET {{url}}/dev/health — in Postman zonder headers; vaak publiek. :contentReference[oaicite:5]{index=5}
        self._get("health")

def parse_args():
    p = argparse.ArgumentParser(description=APP_TITLE)
    p.add_argument("--token", dest="token", default="", help="Access token")
    p.add_argument("--access-token", dest="token", help="Alias voor --token")  # accepteer ook --access-token
    return p.parse_args()

def main():
    args = parse_args()
    gui = AppGUI(
        token=args.token,
    )
    gui.mainloop()

if __name__ == "__main__":
    main()
