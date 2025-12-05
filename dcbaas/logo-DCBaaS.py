import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Definieer de afbeelding grootte en achtergrondkleur
width, height = 500, 500
background_color = "#FEF102"  # Gevraagde HEX-kleur

# Maak een lege afbeelding
img = Image.new("RGB", (width, height), background_color)
draw = ImageDraw.Draw(img)

# Coördinaten voor een schildvorm
shield_points = [
    (width * 0.3, height * 0.2),  # Linkerboven
    (width * 0.7, height * 0.2),  # Rechterboven
    (width * 0.85, height * 0.5),  # Rechtsmidden
    (width * 0.5, height * 0.8),  # Onderpunt
    (width * 0.15, height * 0.5),  # Linksmidden
]

# Teken het schild
draw.polygon(shield_points, fill="black", outline="black")

# Teken een klein documenticoon in het schild
doc_x, doc_y = width * 0.4, height * 0.35
doc_width, doc_height = width * 0.2, height * 0.3
draw.rectangle([doc_x, doc_y, doc_x + doc_width, doc_y + doc_height], fill="white", outline="black")

# Voeg lijnen toe als tekstregels op het document
for i in range(3):
    y_offset = doc_y + (i + 1) * (doc_height / 4)
    draw.line([(doc_x + 5, y_offset), (doc_x + doc_width - 5, y_offset)], fill="black", width=2)

# Teken een slot-icoon
lock_x, lock_y = width * 0.45, height * 0.6
lock_width, lock_height = width * 0.1, height * 0.1
draw.rectangle([lock_x, lock_y, lock_x + lock_width, lock_y + lock_height], fill="black", outline="black")

# Teken de boog van het slot
draw.arc([lock_x - 10, lock_y - 30, lock_x + lock_width + 10, lock_y + lock_height - 10], start=0, end=180, fill="black", width=5)

# Toon de afbeelding
plt.imshow(np.array(img))
plt.axis("off")
plt.show()

# Optioneel: opslaan als bestand
img.save("digital_certificate_logo.png")
