import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading

def fetch_certificate():
    servername = entry.get().strip()
    if not servername:
        messagebox.showerror("Fout", "Voer een geldige servernaam in.")
        print("[FOUT] Geen servernaam ingevoerd.")
        return
    
    # OpenSSL command with full path and -ign_eof to ignore EOF errors
    command = [
        "C:\\openssl\\x64\\bin\\openssl.exe", "s_client", 
        "-connect", f"{servername}:443",
        "-servername", servername,
        "-showcerts",
        "-ign_eof"
    ]
    
    print(f"[INFO] OpenSSL commando wordt uitgevoerd: {' '.join(command)}")
    
    # Show progress bar
    progress_bar.pack(pady=10)
    progress_bar.start(10)
    
    def run_command():
        try:
            # Run the OpenSSL command and capture output
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=None)
            
            print(f"[INFO] OpenSSL commando uitgevoerd met returncode: {result.returncode}")
            
            if result.returncode != 0:
                print(f"[FOUT] Standaardfout output:\n{result.stderr}")
                messagebox.showerror("Fout", f"Er trad een fout op:\n{result.stderr}")
                return
            
            # Ask the user where to save the output
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Opslaan als"
            )
            
            if not file_path:
                print("[INFO] Opslaan geannuleerd door gebruiker.")
                return
            
            # Write the output to the selected file
            with open(file_path, "w") as file:
                file.write(result.stdout)
            
            print(f"[INFO] Certificaat opgeslagen in: {file_path}")
            messagebox.showinfo("Succes", f"Certificaat opgeslagen in {file_path}")
            
            # Open the file in the default text editor
            os.startfile(file_path) if os.name == 'nt' else subprocess.run(["open", file_path] if os.name == 'darwin' else ["xdg-open", file_path])
        
        except Exception as e:
            print(f"[FOUT] Onverwachte fout:\n{e}")
            messagebox.showerror("Fout", f"Er trad een onverwachte fout op:\n{e}")
        finally:
            progress_bar.stop()
            progress_bar.pack_forget()
    
    threading.Thread(target=run_command).start()

# GUI setup
root = tk.Tk()
root.title("OpenSSL Certificaat Ophaler")

label = tk.Label(root, text="Voer de servernaam in (bijv. vlot.onlinesmartcities.be):")
label.pack(pady=10)

entry = tk.Entry(root, width=50)
entry.pack(pady=5)

fetch_button = tk.Button(root, text="Certificaat Ophalen", command=fetch_certificate)
fetch_button.pack(pady=20)

progress_bar = ttk.Progressbar(root, mode="indeterminate", length=300)

root.mainloop()