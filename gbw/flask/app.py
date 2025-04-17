from flask import Flask, render_template, request, redirect, url_for, send_file, session
import os, json, bcrypt
from dotenv import load_dotenv
from qr_generator import genereer_qr

# ✅ Laad omgeving
load_dotenv()

app = Flask(__name__)
app.secret_key = 'supergeheimkey123'
app.config['SESSION_COOKIE_SECURE'] = False  # Alleen voor lokaal gebruik

ADMIN_WACHTWOORD = os.getenv("ADMIN_PASSWORD")
WACHTWOORDEN_PATH = 'afdeling_wachtwoorden.json'


# ✅ Helpers
def get_afdelingen():
    static_path = 'static'
    if not os.path.exists(static_path):
        os.makedirs(static_path)
    return sorted([d for d in os.listdir(static_path) if os.path.isdir(os.path.join(static_path, d))])


def load_wachtwoorden():
    if not os.path.exists(WACHTWOORDEN_PATH):
        return {}
    with open(WACHTWOORDEN_PATH, 'r') as f:
        return json.load(f)


def save_wachtwoorden(data):
    with open(WACHTWOORDEN_PATH, 'w') as f:
        json.dump(data, f, indent=4)


def afdeling_is_toegestaan(afdeling):
    toegang = session.get('afdeling_toegang', {}).get(afdeling)
    print(f"[DEBUG] Toegang voor '{afdeling}':", toegang)
    return toegang is True


def geef_toegang(afdeling):
    print(f"[DEBUG] ✅ Toegang verlenen voor '{afdeling}'")
    if 'afdeling_toegang' not in session:
        session['afdeling_toegang'] = {}
    session['afdeling_toegang'][afdeling] = True
    session.modified = True  # 🔧 BELANGRIJK!
    print(f"[DEBUG] 🔐 Sessietoegang na toewijzing:", session)


# ✅ ROUTES
@app.route('/')
def home():
    afdelingen = get_afdelingen()
    return render_template('index.html', afdelingen=afdelingen)


@app.route('/afdeling/<afdeling>/logout')
def afdeling_logout(afdeling):
    if 'afdeling_toegang' in session:
        session['afdeling_toegang'].pop(afdeling, None)
        session.modified = True
    print(f"[DEBUG] 👋 Uitgelogd uit '{afdeling}'. Sessie nu:", session)
    return redirect(url_for('home'))


@app.route('/afdeling/<afdeling>', methods=['GET', 'POST'])
def afdeling(afdeling):
    afdelingspad = os.path.join('static', afdeling)
    os.makedirs(afdelingspad, exist_ok=True)

    print(f"[DEBUG] 📥 Nieuwe aanvraag voor afdeling '{afdeling}'")
    print(f"[DEBUG] 🧠 Sessiestatus bij binnenkomst:", session)

    wachtwoorden = load_wachtwoorden()
    heeft_wachtwoord = afdeling in wachtwoorden

    if not afdeling_is_toegestaan(afdeling):
        if request.method == 'POST':
            ingevoerd = request.form['wachtwoord'].strip().encode('utf-8')

            if not heeft_wachtwoord:
                # Eerste keer instellen
                hashwachtwoord = bcrypt.hashpw(ingevoerd, bcrypt.gensalt()).decode('utf-8')
                wachtwoorden[afdeling] = hashwachtwoord
                save_wachtwoorden(wachtwoorden)
                geef_toegang(afdeling)
                print(f"[INFO] 🔐 Wachtwoord ingesteld voor afdeling '{afdeling}'")
                return redirect(url_for('afdeling', afdeling=afdeling))
            else:
                opgeslagen_hash = wachtwoorden[afdeling].encode('utf-8')
                print(f"[DEBUG] ✅ Ingevoerde wachtwoord (bytes):", ingevoerd)
                print(f"[DEBUG] ✅ Opgeslagen hash (bytes):", opgeslagen_hash)

                if bcrypt.checkpw(ingevoerd, opgeslagen_hash):
                    geef_toegang(afdeling)
                    print(f"[INFO] ✅ Wachtwoord correct - toegang verleend aan '{afdeling}'")
                    return redirect(url_for('afdeling', afdeling=afdeling))
                else:
                    print(f"[WARNING] ❌ Verkeerd wachtwoord voor '{afdeling}'")
                    return render_template('afdeling_login.html', afdeling=afdeling, fout="Verkeerd wachtwoord.")
        return render_template('afdeling_login.html', afdeling=afdeling, nieuw=not heeft_wachtwoord)

    bestanden = os.listdir(afdelingspad)
    bestanden.sort(reverse=True)
    fout = None

    if request.method == 'POST':
        url = request.form['url'].strip()
        naam = request.form['naam'].strip()
        subtekst = request.form['subtekst'].strip()

        if not url or not naam:
            fout = "URL en bestandsnaam zijn verplicht."
        else:
            bestand_path = genereer_qr(url, naam, subtekst, 'static', afdeling)
            bestanden = os.listdir(afdelingspad)
            bestanden.sort(reverse=True)
            return send_file(bestand_path, as_attachment=True)

    return render_template('afdeling.html', afdeling=afdeling, bestanden=bestanden, fout=fout)


@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        wachtwoord = request.form.get('wachtwoord')
        if wachtwoord == ADMIN_WACHTWOORD:
            session['ingelogd'] = True
            print("[INFO] ✅ Admin ingelogd")
            return redirect(url_for('admin_add'))
        else:
            print("[WARNING] ❌ Verkeerd admin wachtwoord")
            return render_template('admin_login.html', fout="Verkeerd wachtwoord.")
    return render_template('admin_login.html')


@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
    if not session.get('ingelogd'):
        return redirect(url_for('admin_login'))

    melding = None
    if request.method == 'POST':
        nieuwe_afdeling = request.form.get('nieuwe_afdeling').strip()
        if nieuwe_afdeling:
            path = os.path.join('static', nieuwe_afdeling)
            if not os.path.exists(path):
                os.makedirs(path)
                melding = f"Afdeling '{nieuwe_afdeling}' is aangemaakt."
                print(f"[INFO] ➕ Nieuwe afdeling aangemaakt: {nieuwe_afdeling}")
            else:
                melding = f"Afdeling '{nieuwe_afdeling}' bestaat al."

    afdelingen = get_afdelingen()
    return render_template('admin_add.html', afdelingen=afdelingen, melding=melding)


@app.route('/admin/reset/<afdeling>')
def reset_wachtwoord(afdeling):
    if not session.get('ingelogd'):
        return redirect(url_for('admin_login'))
    wachtwoorden = load_wachtwoorden()
    if afdeling in wachtwoorden:
        del wachtwoorden[afdeling]
        save_wachtwoorden(wachtwoorden)
        print(f"[INFO] 🔄 Wachtwoord van '{afdeling}' is gereset")
    return redirect(url_for('admin_add'))


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    print("[INFO] 🚪 Admin uitgelogd, sessie geleegd")
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
