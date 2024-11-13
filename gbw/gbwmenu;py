import PySimpleGUI as sg
import subprocess

# Functies voor het starten van je tools
def start_qr_generator():
    subprocess.run(["python", "qrgbw.py"])
    pass

def start_countdown_timer():
    # Code of commando om de aftelklok te starten
    # Voorbeeld: subprocess.run(["python", "countdown_timer.py"])
    pass

# RGB naar hexadecimaal
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

green_hex = rgb_to_hex((0, 152, 68))

# Definieer het thema en de layout
sg.theme('Black')
button_layout = [
    [sg.Button('Start QR Code Generator', key='START_QR', button_color=('white', green_hex)), sg.Button('Start Countdown Timer', key='START_TIMER', button_color=('white', green_hex))],
]


layout = [
    [sg.Text('Welkom bij de Gezinsbond Wijchmaal Tool Selecteerder', justification='center', font=('Helvetica', 16, 'bold'), text_color=green_hex, pad=(0,10))],  # Verhoog de verticale padding
    [sg.Button('Start QR Code Generator', key='START_QR', button_color=('white', green_hex)), sg.Stretch(), sg.Button('Start Countdown Timer', key='START_TIMER', button_color=('white', green_hex))],
    [sg.Stretch(), sg.Button('Sluiten', key='CLOSE', button_color=('white', green_hex)), sg.Stretch()]
]

# Maak het Window
window = sg.Window('Gezinsbod Wijchmaal Selecteerder', layout, size=(600, 200))

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