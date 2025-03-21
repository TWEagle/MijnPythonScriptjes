import PySimpleGUI as gbw
import qrcode
import PIL
from PIL import Image, ImageDraw, ImageFont
import os.path


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
    gbw.theme_add_new('MyCustomTheme', Gezinsbond)


# RGB naar hexadecimaal
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


green_hex = rgb_to_hex((0, 152, 68))

# Creëer en gebruik aangepast thema
create_custom_theme()
gbw.theme('Gezinsbond')

# Lettertype en grootte
font_path = 'fonts/SourceSansPro-Bold.ttf'
font_size = 16

# Gebruik de font tuple in uw layout
layout = [
    [gbw.Text('Selecteer de map waar het moet opgeslagen worden', font=(font_path, font_size))],
    [gbw.In(key='Mapje'), gbw.FolderBrowse()],
    [gbw.Text('Vul hier de URL in', font=(font_path, font_size))],
    [gbw.InputText(key='URL')],
    [gbw.Text('Vul hier de naam van het bestand in (in 1 woord)', font=(font_path, font_size))],
    [gbw.InputText(key='Bestand')],
    [gbw.Text('Welke tekst wil je onder Gezinsbond hebben staan onder de QR-Code?', font=(font_path, font_size))],
    [gbw.InputText(key='Subtekst')],
    [gbw.Checkbox(key='geenpopup', text='Geen popup na aanmaken van het bestand', default=False, font=(font_path, font_size))],
    [gbw.Button('Ok', font=(font_path, font_size)), gbw.Button('Sluiten', font=(font_path, font_size))]
]

# Creëer het hoofdvenster
window = gbw.Window('QR code generator', layout, grab_anywhere=True)
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == gbw.WIN_CLOSED or event == 'Sluiten':  # if user closes window or clicks cancel
        break
    print(values['URL'])
    print(values['Bestand'])
    print(values['Mapje'])

    def add_corners(frame, rad):
        circle = Image.new('L', (rad * 2, rad * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
        alpha = Image.new('L', frame.size, 255)
        w, h = frame.size
        alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
        alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
        alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
        alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
        frame.putalpha(alpha)
        return frame
 
    # creating a image object (new image object) with
    # RGB mode and size 200x200
    frame = PIL.Image.new(mode="RGB", size=(700, 900),
                    color=(0, 152, 68))

    draw = ImageDraw.Draw(frame)
    drawcalx = ImageDraw.Draw(frame)

    frame = add_corners(frame, 45)
    Subtext = values['Subtekst']

    fontie = ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', 120)
    fonts = fontie
    
    # Bereken de verhouding tussen de breedte van de tekst en de breedte van de image
    ratiox = drawcalx.textlength(Subtext, font=fonts) / frame.size[0]
    # Stel een maximale verhouding in, bijvoorbeeld 0.8
    max_ratiox = 0.8
    # Als de verhouding groter is dan de maximale verhouding, verklein dan de font size
    if ratiox > max_ratiox:
        # Bereken de nieuwe font size door de oude te vermenigvuldigen met de omgekeerde verhouding
        new_font_sizex = int(fonts.size * max_ratiox / ratiox)
        # Maak een nieuw font object met de nieuwe font size
        fonts = ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', new_font_sizex)

    draw.text((32, 609), "Gezinsbond", font=fontie, fill=(255, 255, 255))
    text_ws = drawcalx.textlength(Subtext, font=fonts)
    # Gebruik de textsize attribuut van het font object om de hoogte van de tekst te krijgen
    text_hs = fonts.size * len(Subtext.split("\n"))
    text_xs = (frame.size[0] - text_ws) // 2  # horizontaal centreren
    text_ys = frame.size[1] - text_hs - 30  # verticaal onderaan plaatsen
    drawcalx.text ((text_xs, text_ys), Subtext, font=fonts, fill=(255, 255, 255))

    frametje = frame

    afdeling = 'Grote-Brogel'
    print(afdeling)
    
    gbz = Image.open('pics/GB.png').crop(None)
    drawtje = ImageDraw.Draw(gbz)
    fontie = ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', 120)
    fontje = fontie
    
    # Bereken de verhouding tussen de breedte van de tekst en de breedte van de image
    ratioj = drawtje.textlength(afdeling, font=fontje) / gbz.size[0]
    # Stel een maximale verhouding in, bijvoorbeeld 0.8
    max_ratioj = 0.8
    # Als de verhouding groter is dan de maximale verhouding, verklein dan de font size
    if ratioj > max_ratioj:
        # Bereken de nieuwe font size door de oude te vermenigvuldigen met de omgekeerde verhouding
        new_font_sizej = int(fontje.size * max_ratioj / ratioj)
        # Maak een nieuw font object met de nieuwe font size
        fontje = ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', new_font_sizej)
    # Gebruik de textlength methode om de breedte van de tekst te krijgen
    text_w = drawtje.textlength(afdeling, font=fontje)
    # Gebruik de textsize attribuut van het font object om de hoogte van de tekst te krijgen
    text_h = fontje.size * len(afdeling.split("\n"))
    text_x = (gbz.size[0] - text_w) // 2  # horizontaal centreren
    text_y = gbz.size[1] - text_h - 10  # verticaal onderaan plaatsen
    drawtje.text ((text_x, text_y), afdeling, font=fontje, fill=(0, 152, 68))
    gb = gbz

    url = (values['URL'])

    print(url)

    word = values['Bestand']
    mapje = values['Mapje']
    filename = f"{word}.png"
    bestand = os.path.join(mapje, filename)
    print(bestand)

    qrtje = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        version=10,
        border=1,
    )
    qrtje.add_data(url)
    qrtje.make()
    qrtje = qrtje.make_image(fill_color="#009844", back_color="#ffffff").convert('RGB')

    posqr = ((qrtje.size[0] - gb.size[0]) // 2, (qrtje.size[1] - gb.size[1]) // 2)
    posimg = (54, 22)
    saveje = (bestand)
    print(saveje)

    qrtje.paste(gb, posqr)
    frametje.paste(qrtje, posimg)
    frametje.save(bestand)
    # Vervang tkinter messagebox door PySimpleGUI popup voor consistentie
    if values['geenpopup'] == False:
        message = f"Het bestand {bestand} is aangemaakt.\nEn opgeslagen in de map c:/pi/gezinsbond\n\nWil je ook nog de QR code zien?"
        antwoord = gbw.popup_yes_no(message, title="Gelukt", font=(font_path, font_size))
        if antwoord == 'Yes':
            frametje.show()
#            gb.show()
        else:
            break
    else:
        break
window.close()
