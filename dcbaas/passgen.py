import random
import string

def generate_password(length=24):
    letters_lower = string.ascii_lowercase
    letters_upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%&*()-_=+;[{}]:,.<>?/"

    all_characters = letters_lower + letters_upper + digits + symbols

    password = [
        random.choice(letters_lower),
        random.choice(letters_upper),
        random.choice(digits),
        random.choice(symbols),
    ]

    password += random.choices(all_characters, k=length - 4)
    random.shuffle(password)

    return ''.join(password)

if __name__ == "__main__":
    print(generate_password())
