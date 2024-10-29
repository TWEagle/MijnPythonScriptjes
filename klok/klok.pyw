import tkinter as tk
import time
from datetime import datetime
import pytz

def update_time():
    now = datetime.now(pytz.timezone('Europe/Brussels'))
    current_time = now.strftime("%d/%m/%Y %H:%M:%S")
    label.config(text=current_time)
    root.after(1000, update_time)

def close(event):
    root.destroy()

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [x1+radius, y1,
              x1+radius, y1,
              x2-radius, y1,
              x2-radius, y1,
              x2, y1,
              x2, y1+radius,
              x2, y1+radius,
              x2, y2-radius,
              x2, y2-radius,
              x2, y2,
              x2-radius, y2,
              x2-radius, y2,
              x1+radius, y2,
              x1+radius, y2,
              x1, y2,
              x1, y2-radius,
              x1, y2-radius,
              x1, y1+radius,
              x1, y1+radius,
              x1, y1]
    return canvas.create_polygon(points, **kwargs, smooth=True)

root = tk.Tk()
root.title("Digitale Klok")
root.attributes('-topmost', True)  # Houdt het venster bovenaan

# Plaats het venster rechts onderaan
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = 500
window_height = 110
x = screen_width - window_width - 10
y = screen_height - window_height - 50
root.geometry(f'{window_width}x{window_height}+{x}+{y}')

# Maak een canvas voor afgeronde hoeken
canvas = tk.Canvas(root, width=window_width, height=window_height, bg='black', highlightthickness=0)
canvas.pack(fill='both', expand=True)

# Voeg een afgeronde rechthoek toe
radius = 20
create_rounded_rectangle(canvas, 0, 0, window_width, window_height, radius, fill='black')

label = tk.Label(canvas, font=('calibri', 40, 'bold'), background='black', foreground='white')
label.place(relx=0.5, rely=0.5, anchor='center')

update_time()

# Sluit het venster bij klikken
root.bind("<Button-1>", close)

root.mainloop()
