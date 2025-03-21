import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from PIL import Image, ImageDraw, ImageFont
import qrcode

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class QRApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("QR code generator")
        self.geometry("500x550")
        self.green = (0, 152, 68)
        self.font_path = 'fonts/SourceSansPro-Bold.ttf'

        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(padx=20, pady=20, fill='both', expand=True)

        title_label = ctk.CTkLabel(self.main_frame, text="QR Code Generator", font=("Arial", 20, "bold"))
        title_label.pack(pady=10)

        self.map_input = ctk.CTkEntry(self.main_frame, placeholder_text="Opslagmap", width=350)
        self.map_input.pack(pady=5)
        browse_btn = ctk.CTkButton(self.main_frame, text="Bladeren", command=self.select_folder)
        browse_btn.pack(pady=5)

        self.url_input = ctk.CTkEntry(self.main_frame, placeholder_text="Voer de URL in", width=350)
        self.url_input.pack(pady=5)

        self.bestand_input = ctk.CTkEntry(self.main_frame, placeholder_text="Bestandsnaam", width=350)
        self.bestand_input.pack(pady=5)

        self.afdeling_input = ctk.CTkEntry(self.main_frame, placeholder_text="Afdeling", width=350)
        self.afdeling_input.pack(pady=5)

        self.subtekst_input = ctk.CTkEntry(self.main_frame, placeholder_text="Tekst onder QR-code", width=350)
        self.subtekst_input.pack(pady=5)

        self.checkbox = ctk.CTkCheckBox(self.main_frame, text="Geen popup na genereren")
        self.checkbox.pack(pady=5)

        generate_btn = ctk.CTkButton(self.main_frame, text="Genereer QR-code", command=self.generate_qr, height=40)
        generate_btn.pack(pady=15)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.map_input.delete(0, 'end')
            self.map_input.insert(0, folder)

    def generate_qr(self):
        mapje = self.map_input.get()
        url = self.url_input.get()
        word = self.bestand_input.get()
        afdeling = self.afdeling_input.get()
        subtekst = self.subtekst_input.get()
        bestand = os.path.join(mapje, f"{word}.png")

        frame = Image.new("RGB", (700, 900), self.green)
        draw = ImageDraw.Draw(frame)
        draw.text((32, 609), "Gezinsbond", font=ImageFont.truetype(self.font_path, 120), fill="white")

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            version=10,
            border=1,
        )
        qr.add_data(url)
        qr.make()
        qr_img = qr.make_image(fill_color="#009844", back_color="#ffffff").convert("RGB")

        frame.paste(qr_img, (54, 22))
        frame.save(bestand)

        if not self.checkbox.get():
            response = messagebox.askyesno("Gelukt", f"Het bestand is opgeslagen:\n{bestand}\nWil je de QR-code tonen?")
            if response:
                frame.show()

        messagebox.showinfo("Succes", "QR-code succesvol aangemaakt!")


if __name__ == "__main__":
    app = QRApp()
    app.mainloop()
