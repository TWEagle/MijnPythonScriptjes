import PySimpleGUI as sg
import subprocess
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

# Creëer en gebruik aangepast thema
create_custom_theme()
sg.theme('Gezinsbond')

# Functies voor het starten van je tools
def start_qr_generator():
    subprocess.run(["python", "qrgbw.pyw"])
    pass

def start_countdown_timer():
    subprocess.run(["python", "aftelklok.pyw"])
    # Voorbeeld: subprocess.run(["python", "countdown_timer.py"])
    pass

# RGB naar hexadecimaal
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb
green_hex = rgb_to_hex((0, 152, 68))

# Lettertype en grootte
font_path = 'fonts/SourceSansPro-Bold.ttf'
font_size = 16
fontBig_size = 20

# Controleer of het lettertype bestaat
try:
    font = ImageFont.truetype(font_path, font_size)
except IOError:
    sg.popup_error('Lettertypebestand niet gevonden!', font=(font_path, font_size))
    raise SystemExit('Lettertypebestand niet gevonden!')

# Definieer het thema en de layout
sg.theme('Gezinsbond')

# Aangepaste fontinstellingen voor knoppen
button_font = (font_path, font_size, 'bold')  # Verwijder de tekstkleur
button_text_color = green_hex  # Voeg de tekstkleur toe
font = (font_path, fontBig_size, 'bold')  # Verwijder de tekstkleur

button_layout = [
    [sg.Button('Start QR Code Generator', key='START_QR', button_color=('white', button_text_color), font=button_font),
     sg.Button('Start Countdown Timer', key='START_TIMER', button_color=('white', button_text_color), font=button_font)],
]

layout = [
    [sg.Text('Welkom bij de Gezinsbond Wijchmaal Tool Selecteerder', justification='center', font=font, text_color=button_text_color, pad=(0,10))],
    [sg.Button('Start QR Code Generator', key='START_QR', button_color=('white', button_text_color), font=button_font),
     sg.Stretch(),
     sg.Button('Start Countdown Timer', key='START_TIMER', button_color=('white', button_text_color), font=button_font)],
    [sg.Stretch(), sg.Button('Sluiten', key='CLOSE', button_color=('white', button_text_color), font=button_font), sg.Stretch()]
]

gewenste_breedte = 780
gewenste_hoogte = 200

# Maak het Window
window = sg.Window('Gezinsbond Wijchmaal Selecteerder', layout, size=(gewenste_breedte, gewenste_hoogte), grab_anywhere=True, finalize=True)

# Event Loop
while True:
    event, values = window.read()
    
    if event == sg.WIN_CLOSED or event == 'CLOSE':
        break
    elif event == 'START_QR':
        start_qr_generator()
    elif event == 'START_TIMER':
        start_countdown_timer()

window.close()
