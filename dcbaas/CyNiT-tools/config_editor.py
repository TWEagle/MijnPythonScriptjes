#!/usr/bin/env python3
"""
Eenvoudige Config & Theme Editor voor CyNiT Tools.

Bewerkt:
- settings.json
- config/voica1.json
- config/voica1_messages.md
"""

from pathlib import Path
import json

from flask import request, render_template_string
import cynit_layout

BASE_DIR = Path(__file__).parent

EDITABLE_FILES = {
    "settings.json": BASE_DIR / "settings.json",
    "VOICA1 config (config/voica1.json)": BASE_DIR / "config" / "voica1.json",
    "VOICA1 messages (config/voica1_messages.md)": BASE_DIR / "config" / "voica1_messages.md",
}


def _detect_lang(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".json":
        return "JSON"
    if ext in (".md", ".markdown"):
        return "Markdown"
    return "Tekst"


def register_web_routes(app, settings, tools=None):
    base_css = cynit_layout.common_css(settings)
    common_js = cynit_layout.common_js()

    colors_cfg = settings.get("colors", {})
    accent_bg = colors_cfg.get("button_bg", "#facc15")
    accent_fg = colors_cfg.get("button_fg", "#000000")

    extra_css = f"""
.card {{
  max-width: 1000px;
  margin: 0 auto 20px auto;
  background: #1e1e1e;
  padding: 20px;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.6);
}}
label {{ display:block; margin-top:12px; font-weight:600; }}
select, textarea {{
  width:100%; padding:8px 10px;
  border-radius:8px; border:1px solid #444;
  background:#111; color:#eee;
}}
textarea {{ min-height:420px; font-family:Consolas,monospace; }}
.btn {{
  display:inline-block;
  margin-top:16px;
  padding:8px 16px;
  border-radius:999px;
  border:none;
  background: {accent_bg};
  color: {accent_fg};
  font-weight:700;
  cursor:pointer;
}}
.btn:hover {{
  filter: brightness(1.05);
}}
.badge {{
  display:inline-block;
  padding:2px 10px;
  border-radius:999px;
  background:#222;
  border:1px solid {accent_bg};
  color:{accent_bg};
  font-size:0.8em;
  margin-left:8px;
}}
.muted {{ color:#aaa; font-size:0.9em; }}
.flash-ok {{ background:#064e3b; color:#bbf7d0;
            padding:8px 12px; border-radius:8px; margin-bottom:8px; }}
.flash-err {{ background:#7f1d1d; color:#fecaca;
             padding:8px 12px; border-radius:8px; margin-bottom:8px; }}
"""

    header = cynit_layout.header_html(
        settings,
        tools=tools,
        title="CyNiT Config & Theme Editor",
        right_html="",
    )
    footer = cynit_layout.footer_html()

    page_template = (
        "<!doctype html>\n"
        "<html lang='nl'>\n"
        "<head>\n"
        "  <meta charset='utf-8'>\n"
        "  <title>CyNiT Config Editor</title>\n"
        "  <style>\n"
        f"{base_css}\n{extra_css}\n"
        "  </style>\n"
        "  <script>\n"
        f"{common_js}\n"
        "  </script>\n"
        "</head>\n"
        "<body>\n"
        f"{header}\n"
        "<div class='page'>\n"
        "<div class='card'>\n"
        "  <h1>Config & Theme Editor</h1>\n"
        "  <p class='muted'>Pas centraal je settings, VOICA1-config en templates aan.</p>\n"
        "  {% if msg_ok %}<div class='flash-ok'>{{ msg_ok }}</div>{% endif %}\n"
        "  {% if msg_err %}<div class='flash-err'>{{ msg_err }}</div>{% endif %}\n"
        "  <form method='get' action='{{ url_for(\"config_editor\") }}'>\n"
        "    <label>Kies bestand</label>\n"
        "    <select name='file_key' onchange='this.form.submit()'>\n"
        "      {% for key in file_keys %}\n"
        "      <option value='{{ key }}' {% if key == current_key %}selected{% endif %}>{{ key }}</option>\n"
        "      {% endfor %}\n"
        "    </select>\n"
        "  </form>\n"
        "  <form method='post' action='{{ url_for(\"config_editor\") }}'>\n"
        "    <input type='hidden' name='file_key' value='{{ current_key }}'>\n"
        "    <label>Inhoud van {{ current_key }} "
        "<span class='badge'>{{ lang_label }}</span></label>\n"
        "    <textarea name='content'>{{ content }}</textarea>\n"
        "    <p class='muted'>"
        "JSON-bestanden worden gevalideerd en mooi ingesprongen. "
        "Markdown/tekst wordt rechtstreeks bewaard.</p>\n"
        "    <button type='submit' class='btn'>Opslaan</button>\n"
        "  </form>\n"
        "</div>\n"
        "</div>\n"
        f"{footer}\n"
        "</body>\n"
        "</html>\n"
    )

    def _render(**ctx):
        return render_template_string(page_template, tools=tools, **ctx)

    @app.route("/config-editor", methods=["GET", "POST"])
    def config_editor():
        msg_ok = ""
        msg_err = ""
        file_keys = list(EDITABLE_FILES.keys())

        if request.method == "POST":
            file_key = request.form.get("file_key") or file_keys[0]
            path = EDITABLE_FILES.get(file_key)
            content = request.form.get("content") or ""
            if not path:
                msg_err = "Onbekend bestand."
                current_key = file_key
            else:
                try:
                    if path.suffix.lower() == ".json":
                        # json validatie
                        json.loads(content)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                    msg_ok = f"{file_key} opgeslagen."
                except Exception as e:
                    msg_err = f"Fout bij opslaan: {e}"
                current_key = file_key
        else:
            current_key = request.args.get("file_key") or file_keys[0]

        path = EDITABLE_FILES.get(current_key)
        if path and path.exists():
            raw = path.read_text(encoding="utf-8")
            lang_label = _detect_lang(path)
            # JSON netjes indenten
            if path.suffix.lower() == ".json":
                try:
                    raw_json = json.loads(raw)
                    raw = json.dumps(raw_json, indent=2, ensure_ascii=False)
                except Exception:
                    pass
            content = raw
        else:
            content = ""
            lang_label = "Onbekend"

        return _render(
            file_keys=file_keys,
            current_key=current_key,
            content=content,
            msg_ok=msg_ok,
            msg_err=msg_err,
            lang_label=lang_label,
        )
