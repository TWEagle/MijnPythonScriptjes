import PySimpleGUI as sg
import time
import threading
from playsound import playsound
from PIL import Image, ImageFont

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

# Creëer en gebruik aangepast thema
create_custom_theme()
sg.theme('Gezinsbond')

# Lettertype en grootte
font_path = 'fonts/sspb.ttf'
font_size = 16

# Controleer of het lettertype bestaat
try:
    font = ImageFont.truetype(font_path, font_size)
except IOError:
    sg.popup_error('Lettertypebestand niet gevonden!', font=(font_path, font_size))
    raise SystemExit('Lettertypebestand niet gevonden!')

# Aanpassingen voor timer tekst font
timer_font = (font_path, 300, 'bold')

# RGB naar hexadecimaal
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

green_hex = rgb_to_hex((0, 152, 68))

def show_countdown_window(hrs, mins, secs):
    # Afmetingen van de afbeelding bepalen
    img = Image.open('pics/GB_Transparant.png')
    img_width, img_height = img.size

    # Maak een graph element met dezelfde afmetingen als de afbeelding
    graph_layout = sg.Graph(
        canvas_size=(img_width, img_height),
        graph_bottom_left=(0, 0),
        graph_top_right=(img_width, img_height),
        key='-GRAPH-',
        background_color='black'
    )

    layout = [
        [graph_layout]
    ]

    window = sg.Window('Timer', layout, no_titlebar=True, keep_on_top=True, resizable=True, element_justification='center', background_color='black').Finalize()
    window.Maximize()

    # Voeg de afbeelding en tekst toe aan het graph element
    graph = window['-GRAPH-']
    graph.draw_image('pics/GB_Transparant.png', location=(0, img_height))
    text_location = (img_width // 2, img_height // 2)
    font = timer_font
    text_id = graph.draw_text(f'{hrs:02d}:{mins:02d}:{secs:02d}', text_location, font=font, color='#FFFFFF', text_location='center')

    return window, text_id

def countdown_timer(hrs, mins, secs, window, graph, text_id):
    total_seconds = hrs * 3600 + mins * 60 + secs
    img_width, img_height = graph.CanvasSize
    font = timer_font

    while total_seconds > 0:
        time.sleep(1)
        total_seconds -= 1
        hrs, mins = divmod(total_seconds, 3600)
        mins, secs = divmod(mins, 60)

        # Update de timer tekst
        graph.delete_figure(text_id)
        text_location = (img_width // 2, img_height // 2)
        text_id = graph.draw_text(f'{hrs:02d}:{mins:02d}:{secs:02d}', text_location, font=font, color='#FFFFFF', text_location='center')

    playsound('sounds/horn2.wav')
    window.close()


sg.theme('Black')

hours = [f'{i:02d}' for i in range(24)]
minutes = [f'{i:02d}' for i in range(60)]
seconds = [f'{i:02d}' for i in range(60)]

# Bepaal de breedte van de kolommen
kolom_breedte = 330

uur_kolom = [
    [sg.Text('Uren', font=(font_path, font_size), justification='center')],
    [sg.Combo(hours, size=(15, 1), key='-HRS-', font=(font_path, font_size))]
]

minuut_kolom = [
    [sg.Text('Minuten', font=(font_path, font_size), justification='center')],
    [sg.Combo(minutes, size=(15, 1), key='-MINS-', font=(font_path, font_size))]
]

seconde_kolom = [
    [sg.Text('Seconden', font=(font_path, font_size), justification='center')],
    [sg.Combo(seconds, size=(15, 1), key='-SECS-', font=(font_path, font_size))]
]

# Lay-out voor knoppen in een aparte tabel
knoppen_rij = [
    [sg.Button('Starten', font=(font_path, font_size), button_color=('white', green_hex)),
     sg.Push(),
     sg.Button('Sluiten', font=(font_path, font_size), button_color=('white', green_hex))]
]

# Volledige lay-out
layout = [
    [sg.Column(uur_kolom), sg.Column(minuut_kolom), sg.Column(seconde_kolom)],
    [sg.Text(' ')],  # Een lege regel voor ruimte
    knoppen_rij
]

gewenste_breedte = 670
gewenste_hoogte = 200
# Creëer het hoofdvenster
window = sg.Window('Aftelklok', layout, size=(gewenste_breedte, gewenste_hoogte))



while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Sluiten':
        break
    if event == 'Starten':
        try:
            hrs = int(values['-HRS-'])
            mins = int(values['-MINS-'])
            secs = int(values['-SECS-'])
            # Toewijzen van returnwaarden van show_countdown_window
            countdown_window, text_id = show_countdown_window(hrs, mins, secs)
            graph = countdown_window['-GRAPH-'] # Haal het graph-element op
            threading.Thread(target=countdown_timer, args=(hrs, mins, secs, countdown_window, graph, text_id), daemon=True).start()
        except ValueError:
            sg.popup('Voer geldige getallen in voor uren, minuten en seconden.')



window.close()
