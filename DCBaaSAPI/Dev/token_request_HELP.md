# 📘 Handleiding voor `token_request.py`

Dit script maakt een **JWT (client_assertion)** en vraagt erna een **access token** op bij het Vlaamse authenticatieplatform.  
Je kan het gebruiken om **snel tokens te genereren** vanuit de terminal.

---

## 🔧 Installatievereisten
Voor dit script heb je de volgende Python libraries nodig (staan ook in `requirements.txt`):
```bash
pip install pyjwt requests pyperclip cryptography jwcrypto
```

---

## ▶️ Gebruik
Voer het script uit in de terminal:

```bash
python token_request.py --key <pad-naar-key> --iss <uuid-of-client-id> --aud <jwt-audience> [opties...]
```

---

## ⚙️ Parameters

| Argument | Verplicht | Omschrijving |
|----------|-----------|---------------|
| `--key` | ✅ Ja | Pad naar je private key-bestand (`.jwk`, `.json`, `.pem`, `.key`, `.pfx`, `.p12`) |
| `--iss` | ✅ Ja | De **issuer** en **subject** claim (meestal je `client_id` of UUID) |
| `--aud` | ✅ Ja | De **audience claim** in de JWT (bijv. `https://authenticatie-ti.vlaanderen.be/op`) |
| `--token-audience` | ❌ Nee | Specifieke audience voor het **token endpoint**. Indien leeg → fallback naar `--iss`. |
| `--kid` | ❌ Nee | Optionele **Key ID (kid)** voor de JWT header. |
| `--password` | ❌ Nee | Wachtwoord voor je private key (indien PEM/PFX/P12 beveiligd is). |
| `--save` | ❌ Nee | Slaat de JWT en access token ook op in bestanden (`jwt.txt` en `access_token.txt`) in dezelfde map als de key. |
| `--clip` | ❌ Nee | Kopieert het **access token** automatisch naar het klembord. |

---

## 📜 Voorbeeldcommando's

### 1. JWT en Access Token genereren en tonen
```bash
python token_request.py --key mykey.pfx --password geheim --iss 12345678-abcd --aud https://authenticatie-ti.vlaanderen.be/op
```

### 2. JWT en Access Token opslaan als bestanden
```bash
python token_request.py --key mykey.json --iss 12345678-abcd --aud https://authenticatie-ti.vlaanderen.be/op --save
```
Resultaat:
- `jwt.txt`
- `access_token.txt`

### 3. Access Token direct naar klembord kopiëren
```bash
python token_request.py --key mykey.pem --iss 12345678-abcd --aud https://authenticatie-ti.vlaanderen.be/op --clip
```

---

## 🔑 Werking in stappen
1. **Private key laden** (uit `.jwk`, `.pem`, `.pfx`, etc.).
2. **JWT aanmaken** met claims:  
   - `iss` en `sub` → waarde van `--iss`  
   - `aud` → waarde van `--aud`  
   - `iat` en `exp` → automatisch (huidige tijd + 5 minuten)  
3. **JWT doorgeven aan het token endpoint** (`/op/v1/token`) → access token terugkrijgen.  
4. **Resultaat tonen, opslaan of naar klembord kopiëren** (afhankelijk van opties).  
