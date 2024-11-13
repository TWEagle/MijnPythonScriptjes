import PySimpleGUI as sg
import time
import threading
from playsound import playsound
from PIL import ImageFont

# Definieer eigen thema
def create_custom_theme():
    Gezinsbond = {
        'BACKGROUND': 'black',
        'TEXT': green_hex,
        'INPUT': green_hex,
        'TEXT_INPUT': green_hex,
        'SCROLL': green_hex,
        'BUTTON': ('white', green_hex),
        'PROGRESS': ('#01826B', '#D0D0D0'),
        'BORDER': 1, 'SLIDER_DEPTH': 0, 'PROGRESS_DEPTH': 0,
    }
    sg.theme_add_new('MyCustomTheme', Gezinsbond)

# RGB naar hexadecimaal
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

green_hex = rgb_to_hex((0, 152, 68))
create_custom_theme()
sg.theme('Gezinsbond')

# Timer tekst font
timer_font = ('Helvetica', 50, 'bold')

def show_timer_window():
    layout = [
        [sg.Text("00:00:00", key="-TIMER-", font=timer_font, justification='center', background_color='black', text_color=green_hex)]
    ]

    # Gebruik de 'location' parameter om het venster rechtsonder weer te geven
    window = sg.Window("Timer", layout, no_titlebar=True, keep_on_top=True, element_justification='center', finalize=True, background_color='black', location=(1200, 700))
    return window

def start_timer(hrs, mins, secs, timer_window):
    elapsed_seconds = 0
    target_seconds = hrs * 3600 + mins * 60 + secs

    while elapsed_seconds <= target_seconds:
        hrs, mins = divmod(elapsed_seconds, 3600)
        mins, secs = divmod(mins, 60)

        # Update de timer in het venster
        timer_window["-TIMER-"].update(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        
        time.sleep(1)
        elapsed_seconds += 1

    playsound('sounds/horn.wav')
    timer_window.close()

# Timer configuratievenster
sg.theme('Black')

hours = [f"{i:02d}" for i in range(24)]
minutes = [f"{i:02d}" for i in range(60)]
seconds = [f"{i:02d}" for i in range(60)]

layout = [
    [sg.Text("Uren"), sg.Combo(hours, size=(10, 1), key="-HRS-")],
    [sg.Text("Minuten"), sg.Combo(minutes, size=(10, 1), key="-MINS-")],
    [sg.Text("Seconden"), sg.Combo(seconds, size=(10, 1), key="-SECS-")],
    [sg.Button("Starten"), sg.Button("Sluiten")]
]

main_window = sg.Window("Start Timer", layout)

while True:
    event, values = main_window.read()
    if event == sg.WINDOW_CLOSED or event == "Sluiten":
        break
    if event == "Starten":
        try:
            hrs = int(values["-HRS-"])
            mins = int(values["-MINS-"])
            secs = int(values["-SECS-"])

            # Open timer venster en start teller
            timer_window = show_timer_window()
            threading.Thread(target=start_timer, args=(hrs, mins, secs, timer_window), daemon=True).start()
        except ValueError:
            sg.popup("Voer geldige getallen in voor uren, minuten en seconden.")

main_window.close()
