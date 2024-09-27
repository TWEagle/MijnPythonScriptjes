import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os

def custom_style():
    style = {
        "bg": "black",
        "fg": "white",
        "font": ("Arial", 14),
        "button": {"bg": "dark green", "fg": "white", "activebackground": "green", "font": ("Arial", 14)}
    }
    return style

def browse_file():
    global input_file_path
    input_file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
    if input_file_path:
        file_label.config(text=os.path.basename(input_file_path))

def browse_folder():
    global output_dir
    output_dir = filedialog.askdirectory()
    if output_dir:
        folder_label.config(text=output_dir)

def autofit_columns(worksheet, dataframe):
    """Stel de kolombreedte in op basis van de maximale lengte van de waarden."""
    for idx, col in enumerate(dataframe.columns):
        max_len = max(dataframe[col].astype(str).map(len).max(), len(col)) + 2
        worksheet.set_column(idx, idx, max_len)

def run_script():
    if not (input_file_path and output_dir):
        messagebox.showerror("Error", "Gelieve een bestand en map te selecteren.")
        return

    try:
        gemeente_dir = os.path.join(output_dir, "Gemeente")
        os.makedirs(gemeente_dir, exist_ok=True)

        # Lees de Excel sheets in
        domeinen_df = pd.read_excel(input_file_path, sheet_name='Domeinen')
        toepassingen_df = pd.read_excel(input_file_path, sheet_name='Toepassingen')
        certificaten_df = pd.read_excel(input_file_path, sheet_name='Certificaten')
        dile_df = pd.read_excel(input_file_path, sheet_name='DienstenLeveranciers')

        # Debug: toon de unieke waarden in de GF kolom
        print("Unieke waarden in GF-kolom:", dile_df['GF'].unique())

        # Controleer of 'Nieuwe-OrgNaam' aanwezig is
        if 'Nieuwe-OrgNaam' not in domeinen_df.columns or 'Nieuwe-OrgNaam' not in toepassingen_df.columns or 'Nieuwe-OrgNaam' not in certificaten_df.columns:
            messagebox.showerror("Error", "De kolom 'Nieuwe-OrgNaam' ontbreekt in één of meerdere werkbladen.")
            return

        unieke_orgnamen = domeinen_df['Nieuwe-OrgNaam'].unique()

        gemeente_count = 0

        # Loop door elke unieke 'Nieuwe-OrgNaam'
        for orgnaam in unieke_orgnamen:
            print(f"Bezig met filtering voor orgnaam: {orgnaam}")  # Debug: toon welke orgnaam gefilterd wordt

            domeinen_filtered = domeinen_df[domeinen_df['Nieuwe-OrgNaam'] == orgnaam]
            toepassingen_filtered = toepassingen_df[toepassingen_df['Nieuwe-OrgNaam'] == orgnaam]
            certificaten_filtered = certificaten_df[certificaten_df['Nieuwe-OrgNaam'] == orgnaam]
            
            # Haal het GF ID op uit de kolom GF voor de bestandsnaam
            org_id = domeinen_filtered['GF'].iloc[0]  # Hier gebruiken we GF voor de bestandsnaam
            
            # Filter op de GF-kolom gebaseerd op org_id (GF)
            dile_filtered = dile_df[dile_df['GF'].str.strip().str.lower() == org_id.strip().lower()]
            
            print(f"Gefilterde gegevens voor DienstenLeveranciers bij {orgnaam} (GF: {org_id}):")
            print(dile_filtered)  # Debug: toon de gefilterde data

            if 'GF' not in domeinen_filtered.columns:
                messagebox.showerror("Error", f"De kolom 'GF' ontbreekt in het werkblad 'Domeinen' voor orgnaam {orgnaam}.")
                continue

            # Gebruik de waarde van GF als bestandsnaam
            output_path = os.path.join(gemeente_dir, f"{org_id}.xlsx")

            # Schrijf naar een nieuw Excel-bestand met xlsxwriter
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                domeinen_filtered.to_excel(writer, sheet_name='Domeinen', index=False)
                toepassingen_filtered.to_excel(writer, sheet_name='Toepassingen', index=False)
                certificaten_filtered.to_excel(writer, sheet_name='Certificaten', index=False)
                dile_filtered.to_excel(writer, sheet_name='DienstenLeveranciers', index=False)

                workbook = writer.book

                # Voeg tabel toe met stijl 'Table Style Light 8' als de DataFrame niet leeg is
                for sheet_name, dataframe in [('Domeinen', domeinen_filtered), 
                                              ('Toepassingen', toepassingen_filtered), 
                                              ('Certificaten', certificaten_filtered), 
                                              ('DienstenLeveranciers', dile_filtered)]:
                    worksheet = writer.sheets[sheet_name]

                    if not dataframe.empty:
                        worksheet.add_table(0, 0, dataframe.shape[0], dataframe.shape[1] - 1, {
                            'columns': [{'header': col} for col in dataframe.columns],
                            'style': 'Table Style Light 8'
                        })

                        autofit_columns(worksheet, dataframe)

            gemeente_count += 1

        messagebox.showinfo("Voltooid", f"Proces is perfect doorlopen!\nGemeente-bestanden: {gemeente_count}\n")
        os.startfile(output_dir)

    except Exception as e:
        messagebox.showerror("Error", f"Er is een fout opgetreden: {str(e)}")

def close_application():
    root.destroy()

root = tk.Tk()
root.title("Gemeentefusies Hulp Tool voor Excel")
style = custom_style()

root.config(bg=style["bg"])
root.geometry('1000x200')

file_button = tk.Button(root, text="Selecteer het Excel bestand", command=browse_file, **style["button"])
file_label = tk.Label(root, text="Geen bestand geselecteerd", bg=style["bg"], fg=style["fg"], font=style["font"])
folder_button = tk.Button(root, text="Selecteer de map waar alles opgeslagen wordt", command=browse_folder, **style["button"])
folder_label = tk.Label(root, text="Geen map geselecteerd", bg=style["bg"], fg=style["fg"], font=style["font"])
start_button = tk.Button(root, text="Starten", command=run_script, **style["button"])
close_button = tk.Button(root, text="Sluiten", command=close_application, **style["button"])

file_button.grid(row=0, column=0, padx=(10, 20), pady=(10, 0), sticky='w')
file_label.grid(row=0, column=1, padx=(10, 20), pady=(10, 0), sticky='w')
folder_button.grid(row=1, column=0, padx=(10, 20), pady=(10, 0), sticky='w')
folder_label.grid(row=1, column=1, padx=(10, 20), pady=(10, 0), sticky='w')
start_button.grid(row=3, column=0, padx=(10, 20), pady=(10, 0), sticky='w')
close_button.grid(row=3, column=1, padx=(10, 20), pady=(10, 0), sticky='w')

root.mainloop()
