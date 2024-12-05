import random
import string
import pyperclip
import tkinter as tk
from tkinter import messagebox

def generate_password(length=24):
    # Definieer de sets van karakters om te gebruiken in het wachtwoord
    letters_lower = string.ascii_lowercase
    letters_upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%&*()-_=+[]{}|;:,.<>?/"

    # Combineer alle mogelijke karakters
    all_characters = letters_lower + letters_upper + digits + symbols

    # Zorg ervoor dat ten minste één karakter van elk type wordt opgenomen
    password = [
        random.choice(letters_lower),
        random.choice(letters_upper),
        random.choice(digits),
        random.choice(symbols)
    ]

    # Vul de rest van het wachtwoord aan met willekeurige karakters
    password += random.choices(all_characters, k=length - 4)

    # Schud de karakters om, zodat de volgorde willekeurig is
    random.shuffle(password)

    # Converteer de lijst van karakters naar een string
    password_str = ''.join(password)

    # Kopieer het wachtwoord naar het klembord
    pyperclip.copy(password_str)
    
    return password_str

# Genereer een wachtwoord en kopieer naar het klembord
generated_password = generate_password()

# Maak een Tkinter venster
root = tk.Tk()
root.withdraw()  # Verberg het hoofdvenster

# Toon het gegenereerde wachtwoord in een pop-up venster
messagebox.showinfo("Wachtwoord gegenereerd", f"Gegenereerd wachtwoord (gekopieerd naar klembord): {generated_password}")

