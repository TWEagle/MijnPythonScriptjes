# Telegram Setup voor CyNiT Scanner

## 1️⃣ Maak een Telegram-bot
1. Open Telegram en zoek **@BotFather**
2. Typ `/newbot`
3. Geef een naam → bijvoorbeeld `CyNiTNotifier`
4. Kopieer het API-token dat je krijgt (formaat: `1234567890:ABCdefGhIjKlmnOPqrSTUvwxYZ`)

## 2️⃣ Configureer op je server
Sla de token op:
```bash
echo "1234567890:ABCdefGhIjKlmnOPqrSTUvwxYZ" > ~/.telegram_token
chmod 600 ~/.telegram_token
```

Stuur daarna een bericht naar je bot ("hallo") en open:
```
https://api.telegram.org/bot<jouw_token>/getUpdates
```

Kopieer het `chat_id`-nummer uit het resultaat:
```bash
echo "123456789" > ~/.telegram_chat_id
chmod 600 ~/.telegram_chat_id
```

## 3️⃣ Test je setup
```bash
python3
>>> from notify import send_telegram_message
>>> send_telegram_message("🔔 Testbericht van CyNiT Scanner")
```

## 4️⃣ Automatisch gebruik
De scanner stuurt automatisch meldingen bij:
- Nieuwe of gewijzigde SSL-certificaten
- Verlopen domeinen
- Nieuwe merkdetecties
