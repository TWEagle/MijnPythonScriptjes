import argparse
import json
import tkinter as tk
from tkinter import ttk, messagebox
import requests

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

class AppGUI(tk.Tk):
    def __init__(self, base_url="", token="", auth_scheme="Bearer <token>", origin="localhost"):
        super().__init__()
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

        # interne referentie voor token entry (voor show/hide)
        self._token_entry = None
        self._token_hidden = True

        self.create_widgets()

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

        btns = ttk.Frame(ops)
        btns.grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Button(btns, text="Add", command=self.do_add).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Update", command=self.do_update).grid(row=0, column=1, padx=4)
        ttk.Button(btns, text="Delegate", command=self.do_delegate).grid(row=0, column=2, padx=4)
        ttk.Button(btns, text="Delete", command=self.do_delete).grid(row=0, column=3, padx=4)
        ttk.Button(btns, text="Health", command=self.do_health).grid(row=0, column=4, padx=12)

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


    def _post(self, path: str, payload: dict):
        base = self.master_base_url()   # nieuwe helper
        url = f"{self._base_url}/dev/{path.lstrip('/')}"
        if not base:
            messagebox.showerror("Fout", "Base URL is leeg.")
            return None

        url = f"{self._base_url}/dev/{path.lstrip('/')}"
        headers = self._headers(is_json=True)

        # logging
        shown_auth = headers.get("Authorization") or headers.get("authorizationtoken") or ""
        if len(shown_auth) > 40:
            shown_auth = shown_auth[:20] + "..." + shown_auth[-6:]
        self._clear_output()
        self.log(f"POST {url}")
        self.log(f"Headers: "
                 f"{'Authorization=' + shown_auth if 'Authorization' in headers else ''} "
                 f"{'authorizationtoken=' + shown_auth if 'authorizationtoken' in headers else ''} "
                 f"| Origin={headers.get('Origin')} | Content-Type={headers.get('Content-Type')}")
        self.log("Body:", json.dumps(payload, ensure_ascii=False))

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.RequestException as e:
            self.log("Request error:", e)
            messagebox.showerror("Request error", str(e))
            return None

        self._log_response(resp)
        return resp

    def _post(self, path: str, payload: dict):
        base = self.master_base_url()   # nieuwe helper
        url = f"{self._base_url}/dev/{path.lstrip('/')}"
        if not base:
            messagebox.showerror("Fout", "Base URL is leeg.")
            return None

        url = f"{self._base_url}/dev/{path.lstrip('/')}"
        headers = self._headers(is_json=False)

        shown_auth = headers.get("Authorization") or headers.get("authorizationtoken") or ""
        if len(shown_auth) > 40:
            shown_auth = shown_auth[:20] + "..." + shown_auth[-6:]
        self._clear_output()
        self.log(f"GET {url}")
        self.log(f"Headers: "
                 f"{'Authorization=' + shown_auth if 'Authorization' in headers else ''} "
                 f"{'authorizationtoken=' + shown_auth if 'authorizationtoken' in headers else ''} "
                 f"| Origin={headers.get('Origin')} | Accept=application/json")

        try:
            resp = requests.get(url, headers=headers, timeout=20)
        except requests.RequestException as e:
            self.log("Request error:", e)
            messagebox.showerror("Request error", str(e))
            return None

        self._log_response(resp)
        return resp

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
            return
        payload = {"name": name, "reason": reason}
        # Postman: {{url}}/dev/application/add met Authorization + Origin. :contentReference[oaicite:4]{index=4}
        self._post("application/add", payload)

    def do_update(self):
        name = self.app_name_var.get().strip()
        reason = self.reason_var.get().strip() or "API aanpassing in informatie"
        if not name:
            messagebox.showerror("Fout", "Vul 'Application name' in.")
            return
        payload = {"name": name, "reason": reason}
        self._post("application/update", payload)

    def do_delegate(self):
        name = self.app_name_var.get().strip()
        org_code = self.org_code_var.get().strip()
        duration = self.duration_var.get().strip()
        if not name or not org_code:
            messagebox.showerror("Fout", "Vul 'Application name' en 'Organization code' in.")
            return
        try:
            duration_i = int(duration)
        except ValueError:
            messagebox.showerror("Fout", "Duration moet een geheel getal zijn (maanden).")
            return
        payload = {"name": name, "organization_code_delegated": org_code, "duration": duration_i}
        self._post("application/delegate", payload)

    def do_delete(self):
        name = self.app_name_var.get().strip()
        if not name:
            messagebox.showerror("Fout", "Vul 'Application name' in.")
            return
        payload = {"name": name}
        self._post("application/delete", payload)

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
