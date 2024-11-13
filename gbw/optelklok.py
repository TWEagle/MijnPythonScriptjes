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

# Timer tekst font (groot en klein formaat)
timer_font_large = ('Helvetica', 300, 'bold')
timer_font_small = ('Helvetica', 20, 'bold')

def show_timer_window():
    screen_width, screen_height = sg.Window.get_screen_size()
    window_width, window_height = 1800, 1200
    location = (screen_width // 2 - window_width // 2, screen_height // 2 - window_height // 2)

    # Layout met optelklok in het midden en aftelklok rechts onderaan
    layout = [
        [sg.Text("00:00:00", key="-TIMER-", font=timer_font_large, justification='center', background_color='black', text_color=green_hex, size=(10, 1))],
        [sg.Text("", size=(30, 1)), sg.Text("00:00:00", key="-COUNTDOWN-", font=timer_font_small, justification='right', background_color='black', text_color=green_hex)]
    ]

    window = sg.Window("Timer", layout, no_titlebar=True, keep_on_top=True, element_justification='center', finalize=True, background_color='black', location=location, size=(window_width, window_height))
    return window

def start_timer(hrs, mins, secs, timer_window):
    elapsed_seconds = 0
    target_seconds = hrs * 3600 + mins * 60 + secs

    while elapsed_seconds <= target_seconds:
        hrs_elapsed, mins_elapsed = divmod(elapsed_seconds, 3600)
        mins_elapsed, secs_elapsed = divmod(mins_elapsed, 60)
        timer_window["-TIMER-"].update(f"{hrs_elapsed:02d}:{mins_elapsed:02d}:{secs_elapsed:02d}")
        
        time.sleep(1)
        elapsed_seconds += 1

    playsound('sounds/horn.wav')
    timer_window.close()

def start_countdown(hrs, mins, secs, timer_window):
    total_seconds = hrs * 3600 + mins * 60 + secs

    while total_seconds >= 0:
        hrs_remaining, mins_remaining = divmod(total_seconds, 3600)
        mins_remaining, secs_remaining = divmod(mins_remaining, 60)
        timer_window["-COUNTDOWN-"].update(f"{hrs_remaining:02d}:{mins_remaining:02d}:{secs_remaining:02d}")
        
        time.sleep(1)
        total_seconds -= 1

    timer_window["-COUNTDOWN-"].update("00:00:00")

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

            # Open timer venster en start de optel- en aftelklokken
            timer_window = show_timer_window()
            threading.Thread(target=start_timer, args=(hrs, mins, secs, timer_window), daemon=True).start()
            threading.Thread(target=start_countdown, args=(hrs, mins, secs, timer_window), daemon=True).start()

        except ValueError:
            sg.popup("Voer geldige getallen in voor uren, minuten en seconden.")

main_window.close()
