import time
from pynput.keyboard import Controller, Key

def perform_keyboard_actions():
    keyboard = Controller()
    
    # Simuleer 4x backspace (verwijderen van tekst)
    for _ in range(5):
        keyboard.tap(Key.backspace)
    
    # Typ de gewenste tekst
    keyboard.tap(Key.enter)
    keyboard.type("Bovenstaande toepassing is goedgekeurd!")
    
    # Wacht 1,5 seconden
    time.sleep(1.5)

    # Druk op Enter, 2x Tab en Spatie
    keyboard.tap(Key.enter)
    for _ in range(2):
        keyboard.tap(Key.tab)
    keyboard.tap(Key.space)

if __name__ == "__main__":
    perform_keyboard_actions()
