import cv2
from pyzbar import pyzbar
from PIL import ImageGrab
import pyperclip
import tkinter as tk
from tkinter import messagebox
import numpy as np

# Globale variabelen om de coördinaten van de rechthoek op te slaan
rect_start = None
rect_end = None
drawing = False  # Variabele om bij te houden of we aan het tekenen zijn
qr_code_data = None
running = True  # Variabele om de hoofdloop te controleren

def draw_rectangle(event, x, y, flags, param):
    global rect_start, rect_end, drawing

    if event == cv2.EVENT_LBUTTONDOWN:
        # Start met tekenen
        drawing = True
        rect_start = (x, y)
        rect_end = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            # Blijf de rechthoek bijwerken terwijl de muisknop ingedrukt is
            rect_end = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        # Stop met tekenen en scan de QR-code
        drawing = False
        rect_end = (x, y)
        scan_qr_code()

def scan_qr_code():
    global rect_start, rect_end, qr_code_data

    if rect_start and rect_end:
        x1, y1 = rect_start
        x2, y2 = rect_end

        # Screenshot van het geselecteerde gebied
        screenshot = ImageGrab.grab(bbox=(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # Opslaan van screenshot voor debuggen
        cv2.imwrite("screenshot_debug.png", screenshot_cv)

        # QR code scannen
        qr_codes = pyzbar.decode(screenshot_cv)

        if qr_codes:
            qr_code_data = qr_codes[0].data.decode('utf-8')
            pyperclip.copy(qr_code_data)
            show_message(qr_code_data)
        else:
            show_message("Geen QR code gevonden!")

def show_message(message):
    root = tk.Tk()
    root.withdraw()  # Verberg het hoofdvenster
    messagebox.showinfo("QR Code Scanner", f"Gekopieerd naar klembord:\n{message}")

def close_program():
    global running
    running = False

def main():
    global rect_start, rect_end, drawing, running

    # Tkinter venster met sluitknop
    root = tk.Tk()
    root.title("Controle Paneel")
    root.geometry("200x100")
    root.configure(bg='black')  # Zwarte achtergrond

    # Sluitknop aanpassen
    close_button = tk.Button(root, text="Sluit Programma", command=close_program, bg='blue', fg='white')
    close_button.pack(pady=20)

    # OpenCV venster voor QR code scanner
    cv2.namedWindow("QR Code Scanner", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("QR Code Scanner", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback("QR Code Scanner", draw_rectangle)

    while running:
        # Neem een screenshot van het hele scherm
        screenshot = ImageGrab.grab()
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # Teken de rechthoek indien er coördinaten zijn
        if rect_start and rect_end:
            cv2.rectangle(frame, rect_start, rect_end, (0, 255, 0), 2)

        cv2.imshow("QR Code Scanner", frame)

        # Controleer of het OpenCV venster gesloten is
        if cv2.getWindowProperty("QR Code Scanner", cv2.WND_PROP_VISIBLE) < 1:
            break

        # Escape-toets controle
        if cv2.waitKey(1) & 0xFF == 27:  # Druk op 'Esc' om te stoppen
            break

        root.update()  # Update het Tkinter venster

    cv2.destroyAllWindows()
    root.destroy()

if __name__ == "__main__":
    main()
