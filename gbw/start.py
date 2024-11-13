import PySimpleGUI as start
import subprocess
from PIL import ImageFont

# Definieer eigen thema
def create_custom_theme():
    Gezinsbond = {
        'BACKGROUND': '#000000',
        'TEXT': green_hex,
        'INPUT': green_hex,
        'TEXT_INPUT': green_hex,
        'SCROLL': green_hex,
        'BUTTON': ('white', green_hex),
        'PROGRESS': ('#01826B', '#D0D0D0'),
        'BORDER': 1, 'SLIDER_DEPTH': 0, 'PROGRESS_DEPTH': 0,
    }
    start.theme_add_new('MyCustomTheme', Gezinsbond)

# RGB naar hexadecimaal
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb
green_hex = rgb_to_hex((0, 152, 68))

# Creëer en gebruik aangepast thema
create_custom_theme()
start.theme('Gezinsbond')

# Voeg hier het pad naar uw lettertypebestand toe
font_path = 'fonts/SourceSansPro-Bold.ttf'
font_name = 'Source Sans Pro'
font_size = 16
kleur= green_hex
fontie = (font_name, font_size, 'bold') 
fbig = (font_name, 20, 'bold')
button_font = (font_path, font_size, 'bold')  # Verwijder de tekstkleur
button_text_color = green_hex  

# Controleer of het lettertype bestaat
try:
    font = ImageFont.truetype(font_path, font_size)
except IOError:
    start.popup_error('Lettertypebestand niet gevonden!', font=(font_path, font_size))
    raise SystemExit('Lettertypebestand niet gevonden!')

# Gebruik de font tuple in uw layout
layout = [
    [start.Text('Welkom bij de Gezinsbondtool', font=fbig, text_color=kleur)],
    [start.Text("Deze tool is gemaakt voor de Gezinsbond.", font=fontie, text_color=kleur)],
    [start.Text("Ben jij een bestuurslid/medewerker van Gezinsbond Wijchmaal?", font=fontie, text_color=kleur)],
    [start.Radio('Ja', 'SR1', key='JA', font=fontie, text_color=kleur),start.Stretch(), start.Radio('Nee', 'SR1', default=True, key='NEE', font=fontie, text_color=kleur)],
    [start.Button('Ok', button_color=('white', button_text_color), font=button_font), start.Stretch(), start.Button('Sluiten', button_color=('white', button_text_color), font=button_font)]
]

window = start.Window('Gezinsbondtool', layout, grab_anywhere=True)

while True:
    try:
        event, values = window.read()
        if event == start.WIN_CLOSED or event == 'Sluiten':
            break

        if values['JA']:
            password = start.popup_get_text("Voer het wachtwoord in:", password_char='*', font=fontie, text_color=kleur)
            if password == "GbW2023":
                start.popup("Geslaagd!", font=fontie, text_color=kleur)
                try:
                    subprocess.run(["python", "gbwmenu.py"])
                except Exception as e:
                    start.popup(f"Er is een fout opgetreden bij het starten van gbwmenu.py: {e}", font=fontie, text_color=kleur)
            else:
                start.popup("Verkeerd wachtwoord.", font=fontie, text_color=kleur)
                try:
                    subprocess.run(["python", "qrgb.py"])
                except Exception as e:
                    start.popup(f"Er is een fout opgetreden bij het starten van qrgb.py: {e}", font=fontie, text_color=kleur)

        if values['NEE']:
            try:
                subprocess.run(["python", "qrgb.py"])
            except Exception as e:
                start.popup(f"Er is een fout opgetreden bij het starten van qrgb.py: {e}", font=fontie, text_color=kleur)

    except Exception as e:
        start.popup(f"Een onverwachte fout is opgetreden: {e}", font=fontie, text_color=kleur)

window.close()
