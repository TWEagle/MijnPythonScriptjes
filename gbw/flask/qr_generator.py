import os
import qrcode
from PIL import Image, ImageDraw, ImageFont


def genereer_qr(url, bestandsnaam, subtekst, rootmap, afdeling):
    green_rgb = (0, 152, 68)
    font_path = 'fonts/SourceSansPro-Bold.ttf'
    logo_path = 'pics/GB.png'

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

    frame = Image.new(mode="RGB", size=(700, 900), color=green_rgb)
    draw = ImageDraw.Draw(frame)
    drawcalx = ImageDraw.Draw(frame)
    frame = add_corners(frame, 45)

    fontie = ImageFont.truetype(font_path, 120)
    fonts = fontie
    ratiox = drawcalx.textlength(subtekst, font=fonts) / frame.size[0]
    if ratiox > 0.8:
        new_font_sizex = int(fonts.size * 0.8 / ratiox)
        fonts = ImageFont.truetype(font_path, new_font_sizex)

    draw.text((32, 609), "Gezinsbond", font=fontie, fill=(255, 255, 255))
    text_ws = drawcalx.textlength(subtekst, font=fonts)
    text_hs = fonts.size * len(subtekst.split("\n"))
    text_xs = (frame.size[0] - text_ws) // 2
    text_ys = frame.size[1] - text_hs - 30
    drawcalx.text((text_xs, text_ys), subtekst, font=fonts, fill=(255, 255, 255))

    gbz = Image.open(logo_path)
    drawtje = ImageDraw.Draw(gbz)
    fontje = ImageFont.truetype(font_path, 120)
    ratioj = drawtje.textlength(afdeling, font=fontje) / gbz.size[0]
    if ratioj > 0.8:
        new_font_sizej = int(fontje.size * 0.8 / ratioj)
        fontje = ImageFont.truetype(font_path, new_font_sizej)

    text_w = drawtje.textlength(afdeling, font=fontje)
    text_h = fontje.size * len(afdeling.split("\n"))
    text_x = (gbz.size[0] - text_w) // 2
    text_y = gbz.size[1] - text_h - 10
    drawtje.text((text_x, text_y), afdeling, font=fontje, fill=green_rgb)

    qrtje = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, version=10, border=1)
    qrtje.add_data(url)
    qrtje.make()
    qrtje = qrtje.make_image(fill_color="#009844", back_color="#ffffff").convert('RGB')
    posqr = ((qrtje.size[0] - gbz.size[0]) // 2, (qrtje.size[1] - gbz.size[1]) // 2)
    posimg = (54, 22)

    qrtje.paste(gbz, posqr)
    frame.paste(qrtje, posimg)

    outputmap = os.path.join(rootmap, afdeling)
    os.makedirs(outputmap, exist_ok=True)
    output_path = os.path.join(outputmap, f"{bestandsnaam}.png")
    frame.save(output_path)
    return output_path
