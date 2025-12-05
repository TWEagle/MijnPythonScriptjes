#!/usr/bin/env python3
"""
ctools.py

CyNiT Tools webhub:
- Leest tools-config uit config/tools.json (via cynit_theme.load_tools()).
- Homepagina met grid van tools (cards met 3D hover).
- Aantal kolommen instelbaar via settings.json -> home_columns.
- Icons per tool instelbaar via tools.json -> icon_web / icon_gui.
- Web-only tools: volledige card is klikbaar.
- Web+GUI / GUI-tools: aparte knoppen.
- Registreert web-routes van:
  * cert_viewer
  * voica1
  * config_editor
- /start/ route om GUI-tools te starten (type 'gui' of 'web+gui').
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from flask import Flask, render_template_string, request, redirect, url_for

import cynit_theme
import cynit_layout
import cert_viewer
import voica1
import config_editor


BASE_DIR = Path(__file__).parent

# ===== SETTINGS & TOOLS LADEN =====

SETTINGS: Dict[str, Any] = cynit_theme.load_settings()
TOOLS_CFG: Dict[str, Any] = cynit_theme.load_tools()
TOOLS: List[Dict[str, Any]] = TOOLS_CFG.get("tools", [])


# ===== FLASK-APP =====

app = Flask(__name__)


# ===== HOME-TEMPLATE =====

HOME_TEMPLATE = """
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>CyNiT Tools</title>
  <style>
  {{ base_css|safe }}

  /* verstop eventueel kapotte header-afbeelding uit cynit_layout */
  img[alt="CyNiT Logo"] {
    display: none;
  }

  /* === CyNiT Tools homepage grid === */
  .tools-section {
    margin-top: 32px;
  }

  .tools-grid {
    display: grid;
    grid-template-columns: repeat({{ home_columns }}, minmax(280px, 1fr));
    gap: 20px;
  }

  .tool-card {
    background: #111111;
    border-radius: 16px;
    padding: 16px 20px;
    box-shadow: 0 18px 35px rgba(0, 0, 0, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.03);
    transform: translateY(0) scale(1);
    transition:
      transform 0.18s ease-out,
      box-shadow 0.18s ease-out,
      border-color 0.18s ease-out,
      background 0.18s ease-out;
  }

  .tool-card:hover {
    transform: translateY(-6px) scale(1.01);
    box-shadow: 0 24px 45px rgba(0, 0, 0, 1);
    border-color: rgba(0, 247, 0, 0.35);
    background: #151515;
  }

  /* web-only: volledige card is link */
  .tool-card-link {
    display: block;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
  }

  .tool-card h3 {
    margin: 0 0 8px 0;
    font-size: 1.1rem;
    color: {{ colors.title }};
  }

  .tool-card p {
    margin: 0 0 12px 0;
    color: {{ colors.general_fg }};
    font-size: 0.95rem;
  }

  .tool-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
  }

  .tool-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 999px;
    border: none;
    background: {{ colors.button_bg }};
    color: {{ colors.button_fg }};
    font-family: {{ ui.font_buttons }};
    font-size: 0.85rem;
    cursor: pointer;
    text-decoration: none;
  }

  .tool-btn:hover {
    filter: brightness(1.15);
  }

  .tool-btn span.icon {
    font-size: 0.95rem;
    line-height: 1;
  }

  .muted {
    color: #999;
    font-size: 0.95rem;
  }

  .page-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 8px;
  }

  .page-header img {
    border-radius: 16px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.8);
  }

  @media (max-width: 768px) {
    .tools-grid {
      grid-template-columns: 1fr;
    }
  }

  </style>
  <script>
  {{ common_js|safe }}
  </script>
</head>
<body>
  {{ header|safe }}
  <div class="page">
    <div class="page-header">
      {% if logo_url %}
        <img src="{{ logo_url }}" alt="CyNiT Logo Local"
             style="max-height: {{ ui.logo_max_height }}px;">
      {% endif %}
      <div>
        <h1>Welkom in CyNiT Tools</h1>
        <p class="muted">
          Deze pagina leest automatisch je tools uit <code>config/tools.json</code>.
        </p>
      </div>
    </div>

    <h2>Tools</h2>
    <div class="tools-section">
      <div class="tools-grid">
        {% for tool in tools %}
          {# --- Web-only: volledige card is één <a> --- #}
          {% if tool.type == 'web' and tool.web_path %}
            <a href="{{ tool.web_path }}" class="tool-card tool-card-link">
              <h3>{{ tool.name }}</h3>
              <p>{{ tool.description }}</p>
              <div class="tool-actions">
                <span class="tool-btn">
                  <span class="icon">{{ tool.icon_web or "🌐" }}</span>
                  <span>Open Web</span>
                </span>
              </div>
            </a>

          {# --- Web+GUI of alleen GUI: aparte knoppen --- #}
          {% else %}
            <div class="tool-card">
              <h3>{{ tool.name }}</h3>
              <p>{{ tool.description }}</p>

              <div class="tool-actions">
                {% if tool.type == 'web+gui' %}
                  {% if tool.web_path %}
                    <a class="tool-btn" href="{{ tool.web_path }}">
                      <span class="icon">{{ tool.icon_web or "🌐" }}</span>
                      <span>Open Web</span>
                    </a>
                  {% endif %}
                  <form method="post" action="{{ url_for('start_tool') }}" style="margin:0;">
                    <input type="hidden" name="tool_id" value="{{ tool.id }}">
                    <button type="submit" class="tool-btn">
                      <span class="icon">{{ tool.icon_gui or "🖥️" }}</span>
                      <span>Start GUI</span>
                    </button>
                  </form>
                {% elif tool.type == 'gui' %}
                  <form method="post" action="{{ url_for('start_tool') }}" style="margin:0;">
                    <input type="hidden" name="tool_id" value="{{ tool.id }}">
                    <button type="submit" class="tool-btn">
                      <span class="icon">{{ tool.icon_gui or "🖥️" }}</span>
                      <span>Start GUI</span>
                    </button>
                  </form>
                {% elif tool.type == 'web' and tool.web_path %}
                  {# fallback, zou eigenlijk niet nodig moeten zijn #}
                  <a class="tool-btn" href="{{ tool.web_path }}">
                    <span class="icon">{{ tool.icon_web or "🌐" }}</span>
                    <span>Open Web</span>
                  </a>
                {% endif %}
              </div>
            </div>
          {% endif %}
        {% endfor %}
      </div>
    </div>
  </div>
  {{ footer|safe }}
</body>
</html>
"""


# ===== HULPFUNCTIES =====

def _find_tool_by_id(tool_id: str) -> Optional[Dict[str, Any]]:
    for t in TOOLS:
        if t.get("id") == tool_id:
            return t
    return None


def _start_gui_tool(tool: Dict[str, Any]) -> None:
    """Start een GUI-tool via subprocess (python script)."""
    script_name = tool.get("script")
    if not script_name:
        return
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        print(f"[WARN] Script niet gevonden voor tool {tool.get('id')}: {script_path}")
        return

    try:
        subprocess.Popen([sys.executable, str(script_path)], cwd=str(BASE_DIR))
    except Exception as e:
        print(f"[ERROR] Kon GUI-tool niet starten ({tool.get('id')}): {e}")


# ===== ROUTES =====

@app.route("/", methods=["GET"])
def index():
    colors = SETTINGS.get("colors", {})
    ui = SETTINGS.get("ui", {})

    # aantal kolommen uit settings.json (fallback 3)
    home_columns = SETTINGS.get("home_columns", 3)
    try:
        home_columns = int(home_columns)
        if home_columns < 1:
            home_columns = 1
        if home_columns > 5:
            home_columns = 5
    except Exception:
        home_columns = 3

    # logo-url zelf resolven (relatief naar static/)
    paths = SETTINGS.get("paths", {})
    logo_path = paths.get("logo", "")
    if logo_path:
        if logo_path.startswith("/"):
            logo_url = logo_path
        else:
            logo_url = url_for("static", filename=logo_path)
    else:
        logo_url = ""

    base_css = cynit_layout.common_css(SETTINGS)
    common_js = cynit_layout.common_js()
    header_html = cynit_layout.header_html(
        SETTINGS,
        tools=TOOLS,
        title="CyNiT Tools",
        right_html="",
    )
    footer_html = cynit_layout.footer_html()

    return render_template_string(
        HOME_TEMPLATE,
        tools=TOOLS,
        colors=colors,
        ui=ui,
        base_css=base_css,
        common_js=common_js,
        header=header_html,
        footer=footer_html,
        home_columns=home_columns,
        logo_url=logo_url,
    )


from flask import url_for  # onderaan zodat het boven index() beschikbaar is


@app.route("/start/", methods=["POST"])
def start_tool():
    tool_id = request.form.get("tool_id", "").strip()
    tool = _find_tool_by_id(tool_id)
    if tool is None:
        return redirect(url_for("index"))

    if tool.get("type") in ("gui", "web+gui"):
        _start_gui_tool(tool)

    return redirect(url_for("index"))


# ===== EXTERNE TOOL-ROUTES REGISTREREN =====

def register_external_routes(app: Flask) -> None:
    """Registreer routes van cert_viewer, voica1 en config_editor."""
    cert_viewer.register_web_routes(app, SETTINGS, TOOLS)

    voica_cfg_path = BASE_DIR / "config" / "voica1.json"
    if voica_cfg_path.exists():
        try:
            voica_cfg = json.loads(voica_cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARN] Kon voica1-config niet lezen: {exc}")
            voica_cfg = {}
    else:
        voica_cfg = {}

    voica1.register_web_routes(app, SETTINGS, TOOLS, voica_cfg)
    config_editor.register_web_routes(app, SETTINGS, TOOLS)


# ===== MAIN =====

if __name__ == "__main__":
    register_external_routes(app)
    app.run(host="127.0.0.1", port=5000, debug=False)
