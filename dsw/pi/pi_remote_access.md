# 🌐 Raspberry Pi – Externe Toegang via Cloudflare Tunnel (met Access Policies)

Een uitgebreide gids om je Raspberry Pi veilig bereikbaar te maken via **Cloudflare Tunnel**, inclusief optionele **Zero Trust Access Policies** voor extra beveiliging (zoals e-mail, Google, of 2FA-authenticatie).

---

## 🔒 Waarom Cloudflare Tunnel?

Cloudflare Tunnel creëert een versleutelde verbinding tussen je Raspberry Pi en het Cloudflare-netwerk.  
➡️ Geen open poorten nodig.  
➡️ Automatisch HTTPS-certificaat.  
➡️ Optioneel: toegangscontrole via e-mail of OAuth.

---

## ⚙️ 1️⃣ Voorbereiding

**Je hebt nodig:**
- Raspberry Pi met Ubuntu Server 22.04+  
- Cloudflare-account (gratis) – [https://dash.cloudflare.com](https://dash.cloudflare.com)  
- Domein beheerd in Cloudflare (bijv. `cynit.eu`)

---

## 🧱 2️⃣ Domein toevoegen aan Cloudflare

1. Log in op [Cloudflare Dashboard](https://dash.cloudflare.com).  
2. Klik **Add a Site** → voer `cynit.eu` in.  
3. Volg de wizard om je domein toe te voegen.  
4. Cloudflare toont je **twee nameservers** (bijv. `amy.ns.cloudflare.com` en `ivan.ns.cloudflare.com`).

5. **Ga naar Openprovider:**
   - Log in op [https://cp.openprovider.eu](https://cp.openprovider.eu)
   - Ga naar **Domeinen → Mijn Domeinen → cynit.eu**
   - Klik **Wijzig nameservers**
   - Vervang de huidige nameservers door die van Cloudflare:
     ```
     amy.ns.cloudflare.com
     ivan.ns.cloudflare.com
     ```
   - Klik **Opslaan**

6. Wacht enkele uren tot de DNS-propagatie voltooid is.  
   Je kunt dit controleren via [https://dnschecker.org](https://dnschecker.org).

---

## 🚀 3️⃣ Cloudflare Tunnel installeren

```bash
sudo apt update && sudo apt install curl -y
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-main.gpg
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/ buster main' | sudo tee /etc/apt/sources.list.d/cloudflare.list
sudo apt update && sudo apt install cloudflared -y
```

Login met je Cloudflare-account:
```bash
cloudflared tunnel login
```
Volg de URL, log in, en koppel de Pi aan je domein.

Maak een tunnel:
```bash
cloudflared tunnel create pi-tunnel
```

Configuratiebestand aanmaken:
```bash
sudo nano /etc/cloudflared/config.yml
```
Plak dit:
```yaml
tunnel: pi-tunnel
credentials-file: /home/ubuntu/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: pi.cynit.eu
    service: ssh://localhost:22
  - service: http_status:404
```
Vervang `<tunnel-id>` met je echte ID.

Service activeren:
```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

Controleer status:
```bash
sudo systemctl status cloudflared
```

---

## 🧠 4️⃣ SSH via Cloudflare Tunnel

Op je pc:
- Installeer [cloudflared](https://developers.cloudflare.com/cloudflared/install-and-run/install-windows/)
- Voeg in `~/.ssh/config` (Windows: `C:\Users\<Naam>\.ssh\config`):
```bash
Host pi.cynit.eu
  ProxyCommand cloudflared access ssh --hostname %h
  User ubuntu
  IdentityFile C:\d\OneDrive - TWEagle\downloads\dns-keypairs.pem
```

SSH naar je Pi:
```bash
ssh ubuntu@pi.cynit.eu
```

---

## 🔐 5️⃣ Cloudflare Zero Trust Access Policies

Cloudflare Zero Trust laat je bepalen **wie** toegang heeft tot je tunnel (via e-mail, Google, GitHub, enz.).

### 1️⃣ Activeer Zero Trust
1. Ga naar [https://dash.cloudflare.com](https://dash.cloudflare.com)
2. Klik **Zero Trust** (bovenaan in menu)
3. Klik **Access → Applications → Add an Application**
4. Kies **Self-hosted**

### 2️⃣ Stel toegang in
- **Application name:** Raspberry Pi SSH
- **Domain:** `pi.cynit.eu`
- **Session duration:** 24h

Klik **Next → Add Rule:**
- Action: **Allow**
- Include: **Emails → info@tweagle.eu** (of meerdere mails)

Optioneel:
- Voeg **Google Workspace** of **GitHub OAuth** toe voor login met externe accounts.

Klik **Save**

Nu zal Cloudflare **een loginpagina tonen** (zoals `login.cynit.eu`) voordat iemand SSH-toegang krijgt.

### 3️⃣ SSH login met Access Token
Bij eerste SSH-verbinding opent automatisch een browser om in te loggen. Na authenticatie mag je verbinden met de tunnel.

---

## 🌐 6️⃣ Webapps publiceren via Tunnel

Wil je je webapp beschikbaar maken?

Voeg toe aan `/etc/cloudflared/config.yml`:
```yaml
ingress:
  - hostname: app.cynit.eu
    service: http://localhost:8501
  - hostname: pi.cynit.eu
    service: ssh://localhost:22
  - service: http_status:404
```

Herstart Cloudflare:
```bash
sudo systemctl restart cloudflared
```

Daarna kun je via HTTPS je app bereiken:
```
https://app.cynit.eu
```

---

## 📊 7️⃣ Logboek & Beheer

Bekijk logs:
```bash
sudo journalctl -u cloudflared -f
```

Cloudflare Dashboard → **Zero Trust → Access → Tunnels** toont live status en uptime.

---

## ✅ 8️⃣ Samenvatting

| Doel | Oplossing |
|------|------------|
| Externe SSH-toegang | Cloudflare Tunnel + Zero Trust Access Policy |
| Webapp publiceren | Extra hostnaam in config.yml |
| Beveiliging | Geen poorten open, automatisch SSL, optionele 2FA |
| Monitoring | Cloudflare Zero Trust → Tunnels |

---

🎉 **Je Pi is nu wereldwijd bereikbaar, 100% beveiligd via Cloudflare.**  
Zonder open poorten, met loginbescherming en automatische SSL.

