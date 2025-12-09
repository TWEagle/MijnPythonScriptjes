# Signal Setup voor CyNiT Scanner

## 1️⃣ Installeer signal-cli
```bash
sudo apt update
sudo apt install -y signal-cli
```

## 2️⃣ Registreer je telefoonnummer
```bash
signal-cli -u +32XXXXXXXXX register
signal-cli -u +32XXXXXXXXX verify <verificatiecode>
```

## 3️⃣ Maak configuratiebestand
Maak een bestand:
```bash
nano ~/.signal_config
```

Voeg toe:
```
+32XXXXXXXXX          # je eigen nummer
+324XXXXXXXXX         # ontvanger 1
+324YYYYYYYYY         # ontvanger 2 (optioneel)
```

Opslaan en beveiligen:
```bash
chmod 600 ~/.signal_config
```

## 4️⃣ Test je setup
```bash
python3
>>> from notify import send_signal_message
>>> send_signal_message("🔔 Testbericht via Signal van CyNiT Scanner")
```

## 5️⃣ Automatisch gebruik
De scanner stuurt bij elke voltooide run meldingen naar Signal én Telegram.
