import PySimpleGUI as gbw
import qrcode
import PIL
import os
from PIL import Image, ImageDraw, ImageFont
from tkinter import messagebox
import os.path

gbw.theme('Black')   # Add a touch of color
# All the stuff inside your window.
layout = [  [gbw.Text('Selecteer de map waar het moet opgeslagen worden')],
            [gbw.In(key='Mapjegbw'), gbw.FolderBrowse()],
            [gbw.Text('Vul hier de URL in')],
            [gbw.InputText(key='URLgbw')],
            [gbw.Text('Vul hier de naam van het bestand in (in 1 woord)')],
            [gbw.InputText(key='Bestandgbw')],
            [gbw.Text('Wat is de naam van de afdeling?')],
            [gbw.InputText(key='Afdelinggbw', default_text='Wijchmaal')],
            [gbw.Text('Welke tekst wil je onder Gezinsbond hebben staan onder de QR-Code?')],
            [gbw.InputText(key='Subtekstgbw')],
            [gbw.Checkbox(key='geenpopupgbw', text='Geen popup na aanmaken van het bestand', default=False)],
            [gbw.Button('Ok'), gbw.Button('Sluiten')] ]

# Create the Window
window = gbw.Window('QR code generator', layout, no_titlebar=True, grab_anywhere=True)
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == gbw.WIN_CLOSED or event == 'Sluiten': # if user closes window or clicks cancel
        break
    print(values['URLgbw'])
    print(values['Bestandgbw'])
    print(values['Mapjegbw'])

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
    framegbw = PIL.Image.new(mode="RGB", size=(700, 900),
                    color=(0,152,68))

    drawgbw=ImageDraw.Draw(framegbw)
    drawcalxgbw=ImageDraw.Draw(framegbw)

    framegbw= add_corners(framegbw,45)
    Subtextgbw= values['Subtekstgbw']

    fontiegbw= ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', 120)
    fontsgbw= fontiegbw
    
    # Bereken de verhouding tussen de breedte van de tekst en de breedte van de image
    ratioxgbw = drawcalxgbw.textlength(Subtextgbw, font=fontsgbw) / framegbw.size[0]
    # Stel een maximale verhouding in, bijvoorbeeld 0.8
    max_ratioxgbw = 0.8
    # Als de verhouding groter is dan de maximale verhouding, verklein dan de font size
    if ratioxgbw > max_ratioxgbw:
        # Bereken de nieuwe font size door de oude te vermenigvuldigen met de omgekeerde verhouding
        new_font_sizexgbw = int(fontsgbw.size * max_ratioxgbw / ratioxgbw)
        # Maak een nieuw font object met de nieuwe font size
        fontsgbw = ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', new_font_sizexgbw)
    

    drawgbw.text((32,609), "Gezinsbond",font=fontiegbw, fill=(255,255,255))
    text_wsgbw = drawcalxgbw.textlength(Subtextgbw, font=fontsgbw)
    # Gebruik de textsize attribuut van het font object om de hoogte van de tekst te krijgen
    text_hsgbw = fontsgbw.size * len(Subtextgbw.split("\n"))
    text_xsgbw = (framegbw.size[0] - text_wsgbw) // 2 # horizontaal centreren
    text_ysgbw = framegbw.size[1] - text_hsgbw - 30 # verticaal onderaan plaatsen
    drawcalxgbw.text ( (text_xsgbw, text_ysgbw), Subtextgbw, font=fontsgbw, fill=(255,255,255))

    frametjegbw = framegbw

    afdelinggbw = values['Afdelinggbw']
    print(afdelinggbw)
    
    gbzgbw = Image.open('pics/GB.png').crop(None)
    drawtjegbw=ImageDraw.Draw(gbzgbw)
    fontiegbw= ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', 120)
    fontjegbw= fontiegbw
    
    # Bereken de verhouding tussen de breedte van de tekst en de breedte van de image
    ratiojgbw = drawtjegbw.textlength(afdelinggbw, font=fontjegbw) / gbzgbw.size[0]
    # Stel een maximale verhouding in, bijvoorbeeld 0.8
    max_ratiojgbw = 0.8
    # Als de verhouding groter is dan de maximale verhouding, verklein dan de font size
    if ratiojgbw > max_ratiojgbw:
        # Bereken de nieuwe font size door de oude te vermenigvuldigen met de omgekeerde verhouding
        new_font_sizejgbw = int(fontjegbw.size * max_ratiojgbw / ratiojgbw)
        # Maak een nieuw font object met de nieuwe font size
        fontjegbw = ImageFont.truetype('fonts/SourceSansPro-Bold.ttf', new_font_sizejgbw)
    # Gebruik de textlength methode om de breedte van de tekst te krijgen
    text_wgbw = drawtjegbw.textlength(afdelinggbw, font=fontjegbw)
    # Gebruik de textsize attribuut van het font object om de hoogte van de tekst te krijgen
    text_hgbw = fontjegbw.size * len(afdelinggbw.split("\n"))
    text_xgbw = (gbzgbw.size[0] - text_wgbw) // 2 # horizontaal centreren
    text_ygbw = gbzgbw.size[1] - text_hgbw - 10 # verticaal onderaan plaatsen
    drawtjegbw.text ( (text_xgbw, text_ygbw), afdelinggbw, font=fontjegbw, fill=(0,152,68))
    gbgbw = gbzgbw

    urlgbw = (values['URLgbw'])

    print(urlgbw)

    wordgbw = values['Bestandgbw']
    mapjegbw = values['Mapjegbw']
    filenamegbw = f"{wordgbw}.png"
    bestandgbw = os.path.join(mapjegbw, filenamegbw)
    print(bestandgbw)

    qrtjegbw = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        version=10,
        border=1,
    )
    qrtjegbw.add_data(urlgbw)
    qrtjegbw.make()
    qrtjegbw = qrtjegbw.make_image(fill_color="#009844", back_color="#ffffff").convert('RGB')


    posqrgbw = ((qrtjegbw.size[0] - gbgbw.size[0]) // 2, (qrtjegbw.size[1] - gbgbw.size[1]) // 2)
    posimggbw = (54,22)
    savejegbw = (bestandgbw)
    print(savejegbw)

    qrtjegbw.paste(gbgbw, posqrgbw)
    frametjegbw.paste(qrtjegbw, posimggbw)
    frametjegbw.save(bestandgbw)
    if values['geenpopupgbw'] == False:
        toppiegbw = "Het bestand ", bestandgbw, " is aangemaakt.\nEn opgeslagen in de map c:/pi/gezinsbond\n\nWil je ook nog de QR code zien?"
        antwoordgbw = messagebox.askyesno(message= toppiegbw, title= "Gelukt")
        if antwoordgbw == True:
            frametjegbw.show()
#            gbgbw.show()
            messagebox.CANCEL
        else:
            messagebox.CANCEL
    else:
        messagebox.CANCEL

window.close()