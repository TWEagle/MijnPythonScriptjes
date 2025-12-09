# 🕒 Weekly DNS Scanner Setup (Pi & AWS)

Automatiseer je **DNS Scanner** volledig met een gescheiden planning:
- 🧩 **Raspberry Pi** draait op **zaterdag 02:00** → genereert de nieuwste domeinlijst.
- ☁️ **AWS-instance** draait op **zondag 02:00** → voert de volledige DNS- en WHOIS-scan uit en uploadt naar GitHub.

Zo is de dataset van de Pi altijd up-to-date vóór de AWS-scan.

---

## ⚙️ 1️⃣ Raspberry Pi — zaterdag 02:00

### ➤ Crontab (aanbevolen)

Open de crontab op je Pi:
```bash
crontab -e
```

Voeg deze regel onderaan toe:
```bash
0 2 * * 6 cd /home/ubuntu/dns-scanner-webapp && /home/ubuntu/dns-scanner-webapp/venv/bin/python3 scanner_job.py >> /home/ubuntu/dns-scanner-webapp/scan.log 2>&1
```

💡 **Uitleg:**
- `0 2 * * 6` → Elke zaterdag om 02:00
- Voert `scanner_job.py` uit binnen de virtuele omgeving
- Logt uitvoer in `scan.log`

📘 **Resultaat:** De Raspberry Pi maakt automatisch een nieuwe domeinlijst, voert eventuele voorbereidende scans uit en pusht de resultaten naar GitHub.

### ➤ Systemd Timer (optioneel op Pi)

Bestand `/etc/systemd/system/dns-scanner-weekly.timer`:
```ini
[Timer]
OnCalendar=Sat 02:00
Persistent=true
```

Herlaad en activeer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dns-scanner-weekly.timer
sudo systemctl start dns-scanner-weekly.timer
```

Controleer status:
```bash
sudo systemctl list-timers --all
```

---

## ☁️ 2️⃣ AWS-instance — zondag 02:00

### ➤ Crontab (aanbevolen)

Open de crontab op AWS:
```bash
crontab -e
```

Voeg toe:
```bash
0 2 * * 0 cd /home/ubuntu/dns-scanner-webapp && /home/ubuntu/dns-scanner-webapp/venv/bin/python3 scanner_job.py >> /home/ubuntu/dns-scanner-webapp/scan.log 2>&1
```

💡 **Uitleg:**
- `0 2 * * 0` → Elke zondag om 02:00
- Gebruikt de meest recente GitHub-data (gepusht door de Pi)
- Voert volledige DNS-, WHOIS-, RDAP- en IP-scans uit
- Uploadt nieuwe resultaten + logboek naar GitHub
- Verwijdert Excel-bestanden lokaal na succesvolle upload

### ➤ Systemd Timer (optioneel)

Bestand `/etc/systemd/system/dns-scanner-weekly.timer`:
```ini
[Timer]
OnCalendar=Sun 02:00
Persistent=true
```

Herlaad en activeer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dns-scanner-weekly.timer
sudo systemctl start dns-scanner-weekly.timer
```

Controleer status:
```bash
sudo systemctl list-timers --all
```

---

## 🧾 3️⃣ Logboek en GitHub-upload

Elke run logt:
- **Datum & tijd** van start
- **Duur van de scan** (in minuten)
- **Aantal gescande domeinen**
- **Of er wijzigingen waren**
- **Naam van het resultaatbestand**

📍 Bestand: `results/scan_log.csv`  
📍 Wordt automatisch geüpload naar GitHub  
📍 Excel-resultaten worden lokaal verwijderd na succesvolle upload

---

## ✅ 4️⃣ Samenvatting

| Platform | Dag | Tijd | Actie |
|-----------|-----|------|--------|
| 🧩 Raspberry Pi | Zaterdag | 02:00 | Domeinlijst en voorbereidende scan uitvoeren |
| ☁️ AWS Instance | Zondag | 02:00 | Volledige DNS/WHOIS/RDAP-scan en GitHub-upload |

---

🎯 **Resultaat:** Je infrastructuur werkt nu volledig autonoom — 
- De Raspberry Pi bereidt de data voor op zaterdag,  
- De AWS-instance draait de hoofdsessie op zondag,  
- Alles wordt gelogd, gesynchroniseerd en geüpload naar GitHub.