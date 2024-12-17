import time
from pynput.keyboard import Controller, Key

def perform_keyboard_actions():
    keyboard = Controller()
    
    # Simuleer 4x backspace (verwijderen van tekst)
    for _ in range(9):
        keyboard.tap(Key.backspace)
    
    # Typ de gewenste tekst
    keyboard.type("Aangemaakt door de DCBaaS-beheerder om toekomstige toepassingsaanvragen met deze structuur automatisch te laten goedkeuren")
    
    # Wacht 1,5 seconden
    time.sleep(1.5)

    # Druk op 1x Tab en Spatie
    for _ in range(1):
        keyboard.tap(Key.tab)
    keyboard.tap(Key.space)

if __name__ == "__main__":
    perform_keyboard_actions()
