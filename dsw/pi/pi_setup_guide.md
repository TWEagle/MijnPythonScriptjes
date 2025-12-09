# 🧠 Raspberry Pi – CT Domeinscanner Setup

Een complete gids om je Raspberry Pi in te richten als **Certificate Transparency domeinverzamelaar**.

---

## 🚀 1️⃣ Benodigdheden

- Raspberry Pi 3 of 4 (aanbevolen 4 GB RAM + SD kaart van 32 GB of meer)
- Stabiele internetverbinding (Ethernet of Wi‑Fi)
- Laptop/desktop om via SSH te verbinden
- GitHub account met een privé repo (TWEagle/dns‑scanner‑webapp)

---

## 🧱 2️⃣ Installatie van Ubuntu Server

1. Download **Ubuntu Server 22.04 LTS (64‑bit)** voor Raspberry Pi:  
   👉 https://ubuntu.com/download/raspberry‑pi

2. Flash het image naar je micro‑SD met **Raspberry Pi Imager** of **balenaEtcher**.

3. In Raspberry Pi Imager → klik ⚙️ (geavanceerde opties):
   - Hostname: `pi‑scanner`
   - Gebruiker: `ubuntu` met wachtwoord (eigen keuze)
   - SSH inschakelen: ✅
   - Wi‑Fi (als nodig): SSID + wachtwoord invullen

4. Plaats de SD‑kaart in de Pi en start op.

5. Verbind via SSH vanaf je pc (zoek IP in router of via `ping pi‑scanner.local`):

```bash
ssh ubuntu@<IP‑adres‑van‑pi>
```

6. Na de eerste login word je gevraagd het wachtwoord te wijzigen.

---

## ⚙️ 3️⃣ Systeem update en basispakketten

```bash
sudo apt update && sudo apt upgrade ‑y
sudo apt install ‑y python3‑venv python3‑pip git curl jq unzip
```

---

## 🐍 4️⃣ Virtuele omgeving voor Python

```bash
cd ~
mkdir ct‑scanner && cd ct‑scanner
python3 ‑m venv venv
source venv/bin/activate
pip install ‑‑upgrade pip pandas requests openpyxl ```

---

## 🔑 5️⃣ GitHub token instellen

1️⃣ Maak een **Personal Access Token** (PAT):  
  👉 https://github.com/settings/tokens

2️⃣ Kies:
| Instelling | Waarde |
|-------------|---------|
| Naam | `pi‑ct‑uploader` |
| Toegang | Repo: `TWEagle/dns‑scanner‑webapp` |
| Permissies | Contents ✅ Read & Write |

3️⃣ Kopieer de token en sla hem op op de Pi:

```bash
echo 'ghp_AbCdEf1234567890...' > ~/.github_token
chmod 600 ~/.github_token
```

---

## 📦 6️⃣ Script get_ct_domains.py

Maak het bestand aan:

```bash
nano get_ct_domains.py
```

Plak dit erin:

```python
import requests, pandas as pd, datetime, time, os, subprocess

REPO = "TWEagle/dns-scanner-webapp"
TOKEN_FILE = os.path.expanduser("~/.github_token")
RESULT_DIR = "results/domains"


def get_domains_from_ct(tlds):
   all_domains = set()
   for tld in tlds:
      print(f"Haal domeinen op voor .{tld}...")
      url = f"https://crt.sh/?q=%25.{tld}&output=json"
      try:
         resp = requests.get(url, timeout=60)
         if resp.status_code == 200:
            for e in resp.json():
              domain = e.get("name_value", "").lower()
              if domain and not domain.startswith("*"):
                all_domains.add(domain)
      except Exception as ex:
         print(f"Fout bij .{tld}: {ex}")
      time.sleep(5)
   return sorted(all_domains)


def save_and_upload(domains):
   today = datetime.date.today().strftime("%Y-%m-%d")
   fname = f"domeinen_auto_{today}.xlsx"
   pd.DataFrame(domains, columns=["domein"]).to_excel(fname, index=False)
   print(f"{len(domains)} domeinen → {fname}")

   token = open(TOKEN_FILE).read().strip()
   os.system(f"git config user.name 'pi‑bot'")
   os.system(f"git config user.email 'info@tweagle.eu'")
   os.system(f"git clone https://{token}@github.com/{REPO}.git repo")
   os.chdir("repo")
   os.makedirs(RESULT_DIR, exist_ok=True)
   os.replace(f"../{fname}", f"{RESULT_DIR}/{fname}")
   os.system("git add .")
   os.system(f"git commit ‑m 'CT update {today}' || true")
   os.system("git push origin main")
   print("✅ Upload voltooid naar GitHub.")


if __name__ == "__main__":
   tlds = ["be", "eu", "gent", "vlaanderen", "brussels"]
   domains = get_domains_from_ct(tlds)
   save_and_upload(domains)
```

Opslaan (CTRL + O, Enter, CTRL + X).

---

## 🔁 7️⃣ Cronjob instellen (1× per week)

Open de crontab:

```bash
crontab ‑e
```

Voeg toe:

```bash
0 3 * * 1 cd /home/ubuntu/ct‑scanner && /home/ubuntu/ct‑scanner/venv/bin/python3 get_ct_domains.py >> /home/ubuntu/ct‑scanner/ct.log 2>&1
```

💡 Dat draait elke maandag om 03:00 en uploadt het resultaat naar GitHub.

---

## 🧪 8️⃣ Manueel testen

```bash
source venv/bin/activate
python3 get_ct_domains.py
```

Na enkele minuten zie je:
```
50000 domeinen → domeinen_auto_2025‑11‑05.xlsx
✅ Upload voltooid naar GitHub.
```

Controleer in GitHub → `results/domains/` of het bestand daar staat.

---

## 🔒 9️⃣ Beveiligingstips

- Gebruik altijd een **privé GitHub‑repo**
- Deel je token nooit in code of logs
- Gebruik `chmod 600 ~/.github_token`
- Zet een firewall op de Pi (`sudo ufw enable` + `sudo ufw allow 22/tcp`)

---

## 🏁 10️⃣ Volgende stap

Nu worden de CT‑domeinen automatisch op GitHub gezet. Je AWS‑instance kan deze wekelijks ophalen en scannen met `scanner_job.py`.

💡 In AWS:
```
0 4 * * 1 cd ~/dns-scanner-webapp && git pull && source venv/bin/activate && python3 scanner_job.py
```

Zo heb je een volledig geautomatiseerde CT → DNS analyse keten tussen je Pi en AWS ☁️💪

