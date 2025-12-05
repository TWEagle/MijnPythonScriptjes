#!/usr/bin/env python3
import sys
import os
import json
import subprocess
from pathlib import Path
from io import BytesIO

from flask import Flask, request, render_template_string, send_file

import cynit_theme
import cert_viewer
import voica1

# -------------------------------------------------------------------
#  Basis setup
# -------------------------------------------------------------------

IS_FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = cynit_theme.BASE_DIR

# Basis config + tools + helpfiles
settings = cynit_theme.load_settings()
tools_cfg = cynit_theme.load_tools()
help_cfg = cynit_theme.load_helpfiles()

# lijstjes
TOOLS = tools_cfg.get("tools", [])
HELPFILES = help_cfg.get("helpfiles", [])

# Zorg dat certviewer altijd een web_path heeft (voor oudere tools.json)
for tool in TOOLS:
    if tool.get("id") == "certviewer" and not tool.get("web_path"):
        tool["web_path"] = "/cert"

COLORS = settings["colors"]
UI = settings["ui"]

BG = COLORS["background"]
FG = COLORS["general_fg"]
TITLE = COLORS["title"]
BTN_BG = COLORS["button_bg"]
BTN_FG = COLORS["button_fg"]

app = Flask(__name__)

# -------------------------------------------------------------------
#  Helpers
# -------------------------------------------------------------------

def restart_program():
    """Herstart de volledige hub (nieuw proces, oude sluit af)."""
    python = sys.executable
    args = sys.argv
    try:
        subprocess.Popen([python] + args, cwd=BASE_DIR)
    except Exception as e:
        print(f"[ERROR] Kon herstart niet uitvoeren: {e}")
    os._exit(0)


def start_external_py(script_name: str, extra_args=None):
    """
    Start een externe tool uit tools.json als apart proces.
    Werkt in .py modus; EXE-modus kan later uitgebreid worden.
    """
    if extra_args is None:
        extra_args = []
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        return False, f"Script {script_name} niet gevonden in {BASE_DIR}"

    if IS_FROZEN:
        return False, "Externe tools starten uit ctools.exe is nog niet geïmplementeerd."

    try:
        subprocess.Popen([sys.executable, str(script_path)] + extra_args, cwd=BASE_DIR)
        return True, f"{script_name} werd opgestart."
    except Exception as e:
        return False, f"Kon {script_name} niet starten: {e}"


def set_active_profile(profile_name: str):
    """
    Past active_profile in settings.json aan (als profiel bestaat).
    """
    path = cynit_theme.SETTINGS_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, "Kon settings.json niet lezen."

    profiles = raw.get("profiles", {})
    if profile_name not in profiles:
        return False, f"Profiel '{profile_name}' bestaat niet in settings.json."

    raw["active_profile"] = profile_name
    try:
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    except Exception as e:
        return False, f"Kon settings.json niet schrijven: {e}"
    return True, f"Actief profiel gewijzigd naar '{profile_name}'."

# -------------------------------------------------------------------
#  HTML template voor de hub (home)
# -------------------------------------------------------------------

HOME_TEMPLATE = f"""
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>CyNiT Tools</title>
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
  <style>
    body {{
      background: {BG};
      color: {FG};
      font-family: Arial, sans-serif;
      margin: 0;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      background: #111;
      border-bottom: 1px solid #333;
    }}
    .topbar-left {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .topbar-right {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .logo {{
      max-height: {UI.get("logo_max_height", 80)}px;
    }}
    .page {{
      padding: 20px;
      min-height: calc(100vh - 120px);  /* zodat de footer mooi onderaan komt */
    }}
    h1, h2, h3 {{
      color: {TITLE};
    }}
    .footer {{
      padding: 8px 16px;
      background: #111111;
      border-top: 1px solid #333333;
      color: {FG};
      font-size: 0.85em;
      text-align: right;
    }}
    .card {{
      border: 1px solid #333;
      background: #111;
      padding: 12px 16px;
      margin-bottom: 12px;
      border-radius: 6px;
    }}
    .card-title {{
      font-size: 1.15em;
      margin-bottom: 4px;
    }}
    button {{
      background: {BTN_BG};
      color: {BTN_FG};
      border: 1px solid {FG};
      padding: 5px 10px;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.6);
      border-radius: 4px;
      margin-right: 5px;
    }}
    button:hover {{
      background: #222;
    }}
    a {{
      color: {FG};
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .msg {{
      margin-bottom: 10px;
      font-size: 0.9em;
    }}

    /* Wafelmenu */
    .waffle-wrapper {{
      position: relative;
      display: inline-block;
    }}
    .waffle-icon {{
      width: 26px;
      height: 26px;
      border-radius: 4px;
      border: 1px solid {FG};
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 16px;
      margin-right: 8px;
    }}
    .waffle-dropdown {{
      display: none;
      position: absolute;
      top: 30px;
      left: 0;
      background: #111;
      border: 1px solid #333;
      min-width: 220px;
      z-index: 999;
      border-radius: 4px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.7);
    }}
    .waffle-dropdown a {{
      display: block;
      padding: 6px 10px;
      font-size: 0.9em;
      white-space: nowrap;
    }}
    .waffle-dropdown a:hover {{
      background: #222;
    }}

    /* Help-hamburger rechts */
    .hamburger-wrapper {{
      position: relative;
      display: inline-block;
    }}
    .hamburger-icon {{
      width: 26px;
      height: 26px;
      border-radius: 4px;
      border: 1px solid {FG};
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 16px;
    }}
    .hamburger-dropdown {{
      display: none;
      position: absolute;
      top: 30px;
      right: 0;
      background: #111;
      border: 1px solid #333;
      min-width: 220px;
      z-index: 999;
      border-radius: 4px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.7);
    }}
    .hamburger-dropdown a {{
      display: block;
      padding: 6px 10px;
      font-size: 0.9em;
      white-space: nowrap;
    }}
    .hamburger-dropdown a:hover {{
      background: #222;
    }}

    select {{
      background: #000;
      color: {FG};
      border: 1px solid #555;
      border-radius: 4px;
      padding: 2px 4px;
    }}
  </style>
  <script>
    function toggleWaffle() {{
      var el = document.getElementById('waffle-menu');
      if (!el) return;
      el.style.display = (el.style.display === 'block') ? 'none' : 'block';
    }}

    function toggleHelpMenu() {{
      var el = document.getElementById('help-menu');
      if (!el) return;
      el.style.display = (el.style.display === 'block') ? 'none' : 'block';
    }}

    async function restartApp() {{
      try {{
        await fetch('/restart');
      }} catch (e) {{
        // tijdens restart kan de fetch mislukken, is oké
      }}
      setTimeout(function() {{
        window.location.href = '/';
      }}, 1000);
    }}

    async function setProfile(event) {{
      event.preventDefault();
      var form = event.target;
      var formData = new FormData(form);
      try {{
        await fetch('/set_profile', {{
          method: 'POST',
          body: formData
        }});
      }} catch (e) {{
        // negeren; we herstarten toch
      }}
      restartApp();
    }}
  </script>
</head>
<body>
  <div class="topbar">
    <div class="topbar-left">
      <div class="waffle-wrapper">
        <div class="waffle-icon" onclick="toggleWaffle()">▦</div>
        <div id="waffle-menu" class="waffle-dropdown">
          {{% for t in tools if t.get('web_path') %}}
            <a href="{{{{ t.web_path }}}}">{{{{ t.name }}}}</a>
          {{% endfor %}}
          <a href="/">🏠 Hub home</a>
          <a href="#" onclick="restartApp(); return false;">🔄 Reload app</a>
        </div>
      </div>
      <img src="/logo.png" class="logo" alt="CyNiT Logo">
      <span>CyNiT Tools</span>
    </div>
    <div class="topbar-right">
      <form onsubmit="setProfile(event)" style="display:flex; align-items:center; gap:4px;">
        <label style="font-size:0.9em;">Profiel:</label>
        <select name="profile">
          {{% for name in profiles %}}
            <option value="{{{{ name }}}}" {{% if name == active_profile %}}selected{{% endif %}}>{{{{ name }}}}</option>
          {{% endfor %}}
        </select>
        <button type="submit" style="padding:2px 6px; font-size:0.9em;">Set</button>
      </form>

      <div class="hamburger-wrapper">
        <div class="hamburger-icon" onclick="toggleHelpMenu()">☰</div>
        <div id="help-menu" class="hamburger-dropdown">
          {{% for h in helpfiles %}}
            <a href="/help/{{{{ h.id }}}}" target="_blank">{{{{ h.name }}}}</a>
          {{% endfor %}}
        </div>
      </div>
    </div>
  </div>

  <div class="page">
    {{% if msg %}}<div class="msg">{{{{ msg }}}}</div>{{% endif %}}

    <h1>Welkom in CyNiT Tools</h1>
    <p>Deze pagina leest automatisch je tools uit <code>config/tools.json</code>.</p>

    <h2>Tools</h2>
    {{% for tool in tools %}}
      <div class="card">
        <div class="card-title">{{{{ tool.name }}}}</div>
        <p style="font-size:0.9em;">{{{{ tool.description }}}}</p>

        {{% if tool.type == 'web+gui' %}}
          {{% if tool.web_path %}}
            <a href="{{{{ tool.web_path }}}}" style="margin-right:8px;">🌐 Open Web</a>
          {{% endif %}}
          <form method="post" action="/start/{{{{ tool.id }}}}" style="display:inline;">
            <button type="submit">🖥 Start GUI</button>
          </form>
        {{% elif tool.type == 'web' %}}
          {{% if tool.web_path %}}
            <a href="{{{{ tool.web_path }}}}">🌐 Open Web</a>
          {{% endif %}}
        {{% elif tool.type == 'gui' %}}
          <form method="post" action="/start/{{{{ tool.id }}}}">
            <button type="submit">🖥 Start GUI</button>
          </form>
        {{% endif %}}
      </div>
    {{% endfor %}}
  </div>

  <div class="footer">
    © CyNiT 2024 - 2026
  </div>
</body>
</html>
"""

# -------------------------------------------------------------------
#  Routes
# -------------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    profiles = list(settings.get("profiles", {}).keys())
    active_profile = settings.get("active_profile")
    return render_template_string(
        HOME_TEMPLATE,
        tools=TOOLS,
        msg=None,
        profiles=profiles,
        active_profile=active_profile,
        helpfiles=HELPFILES,
    )


@app.route("/start/<tool_id>", methods=["POST"])
def start_tool(tool_id):
    tool = next((t for t in TOOLS if t.get("id") == tool_id), None)
    if not tool:
        msg = f"Tool '{tool_id}' niet gevonden in tools.json."
    else:
        t_type = tool.get("type", "gui")
        script = tool.get("script")
        if tool_id == "certviewer":
            ok, msg = start_external_py(script, extra_args=["--gui"])
        else:
            if t_type in ("gui", "web+gui"):
                ok, msg = start_external_py(script)
            else:
                ok, msg = False, "Tooltype niet ondersteund voor start vanuit hub."

    profiles = list(settings.get("profiles", {}).keys())
    active_profile = settings.get("active_profile")

    return render_template_string(
        HOME_TEMPLATE,
        tools=TOOLS,
        msg=msg,
        profiles=profiles,
        active_profile=active_profile,
        helpfiles=HELPFILES,
    )


@app.route("/set_profile", methods=["POST"])
def set_profile_route():
    profile = request.form.get("profile")
    ok, msg = set_active_profile(profile)
    status = 200 if ok else 400
    return {"ok": ok, "message": msg}, status


@app.route("/restart")
def restart_route():
    restart_program()
    return ""  # praktisch nooit bereikt


@app.route("/about")
def about_route():
    """
    Oude /about route blijft nog werken.
    (Zelfde inhoud als 'about' in helpfiles.)
    """
    try:
        md = cynit_theme.ABOUT_MD.read_text(encoding="utf-8")
    except Exception:
        md = "ABOUT.md kon niet gelezen worden."
    html_body = cynit_theme.markdown_to_html_simple(md)
    return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>About CyNiT Tools</title>
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
  <style>
    body {{
      background: {BG};
      color: {FG};
      font-family: Arial, sans-serif;
      margin: 20px;
    }}
    h1, h2, h3 {{ color: {TITLE}; }}
    a {{ color: {FG}; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""


@app.route("/help/<help_id>")
def help_route(help_id):
    """
    Toont een helpfile uit config/helpfiles.json in je CyNiT-kleuren.
    """
    entry = next((h for h in HELPFILES if h.get("id") == help_id), None)
    if not entry:
        return f"Helpfile '{help_id}' niet gevonden in helpfiles.json.", 404

    md_rel = entry.get("md")
    if not md_rel:
        return f"Helpfile '{help_id}' heeft geen 'md' pad.", 500

    md_path = BASE_DIR / md_rel
    if not md_path.exists():
        return f"Markdown bestand '{md_path}' niet gevonden.", 404

    try:
        md = md_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Markdown bestand kon niet gelezen worden: {e}", 500

    html_body = cynit_theme.markdown_to_html_simple(md)
    title = entry.get("name", f"Help: {help_id}")
    return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
  <style>
    body {{
      background: {BG};
      color: {FG};
      font-family: Arial, sans-serif;
      margin: 20px;
    }}
    h1, h2, h3 {{ color: {TITLE}; }}
    a {{ color: {FG}; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""


@app.route("/favicon.ico")
def favicon_route():
    ico_bytes = cynit_theme.generate_ico_bytes()
    if ico_bytes is None:
        return "", 404
    return send_file(BytesIO(ico_bytes), mimetype="image/x-icon")


@app.route("/logo.png")
def logo_route():
    if not cynit_theme.LOGO_PATH.exists():
        return "", 404
    return send_file(str(cynit_theme.LOGO_PATH), mimetype="image/png")


# Cert viewer web-routes
cert_viewer.register_web_routes(app, settings, TOOLS)

# VOICA1 config uit config/voica1.json
voica1_cfg_path = Path(__file__).parent / "config" / "voica1.json"
if voica1_cfg_path.exists():
    with voica1_cfg_path.open(encoding="utf-8") as f:
        voica_cfg = json.load(f)
else:
    voica_cfg = {}

# VOICA1 web-routes
voica1.register_web_routes(app, settings, TOOLS, voica_cfg)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
    # Als je liever alles op 5445 draait:
    # app.run(host="127.0.0.1", port=5445, debug=False)

