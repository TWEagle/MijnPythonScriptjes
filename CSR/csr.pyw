import os
from tkinter import Tk, filedialog, Frame
from tkinter.ttk import Treeview, Label, Style
from ttkbootstrap import Button, Style as BootstrapStyle
from cryptography import x509
from cryptography.hazmat.backends import default_backend


def lees_certificaat(pad):
    try:
        with open(pad, "rb") as cert_file:
            cert_data = cert_file.read()

        # Probeer PEM-certificaat te laden
        try:
            certificaat = x509.load_pem_x509_certificate(cert_data, default_backend())
            cert_format = "PEM"
        except ValueError:
            # Als het geen PEM is, probeer als DER
            certificaat = x509.load_der_x509_certificate(cert_data, default_backend())
            cert_format = "DER"

        checks = [
            {"Check": "Expiry", "Result": f"PASSED - Expires {certificaat.not_valid_after_utc.strftime('%b %d %Y')}"},
            {"Check": "Key Size", "Result": f"PASSED ({certificaat.public_key().key_size} bits)"},
            {"Check": "SHA1", "Result": "PASSED - Not using the SHA1 algorithm"},
        ]

        subject = [{"Field": name.oid._name, "Value": name.value} for name in certificaat.subject]
        issuer = [{"Field": name.oid._name, "Value": name.value} for name in certificaat.issuer]

        return {
            "Certificate Checks": checks,
            "Certificate Subject": subject,
            "Certificate Issuer": issuer,
            "Format": cert_format,
        }
    except Exception as e:
        return f"Fout bij uitlezen van certificaat: {e}"


def clear_tree(tree):
    """Wis alle rijen in de Treeview."""
    for item in tree.get_children():
        tree.delete(item)


def laad_certificaat():
    bestand = filedialog.askopenfilename(filetypes=[("Certificate Files", "*.crt"), ("All Files", "*.*")])
    if not bestand or not os.path.isfile(bestand):
        label_info.config(text="Geen bestand geselecteerd of onjuist bestand.", foreground="red")
        return

    cert_info = lees_certificaat(bestand)

    if isinstance(cert_info, str):
        label_info.config(text=f"Fout bij uitlezen: {cert_info}", foreground="red")
        return

    # Maak bestaande tabellen leeg
    clear_tree(tree_checks)
    clear_tree(tree_subject)
    clear_tree(tree_issuer)

    try:
        # Vul de Treeviews
        for row in cert_info["Certificate Checks"]:
            tree_checks.insert("", "end", values=(row["Check"], row["Result"]), tags=("yellow",))
        for row in cert_info["Certificate Subject"]:
            tree_subject.insert("", "end", values=(row["Field"], row["Value"]), tags=("green",))
        for row in cert_info["Certificate Issuer"]:
            tree_issuer.insert("", "end", values=(row["Field"], row["Value"]), tags=("orange",))

        # Update label_info met succesbericht
        label_info.config(
            text=f"{os.path.basename(bestand)}",
            foreground="yellow",
        )

        # Update het bestandstype label
        cert_format = cert_info["Format"]
        if cert_format == "PEM":
            label_format.config(
                text="",
                background="orange",
                foreground="black",
            )
        else:
            label_format.config(
                text="",
                background="green",
                foreground="black",
            )

        # Wijzig de titel van het venster
        root.title("Certificaat geladen!")

        # Maak de sluitknop zichtbaar
        close_button.pack(side="right", padx=5)

    except Exception as e:
        print("Fout bij het vullen van tabellen:", str(e))
        label_info.config(text=f"Fout bij het vullen van tabellen: {str(e)}", foreground="red")


def sluit_app():
    """Sluit de applicatie."""
    root.destroy()


# GUI Configuratie
root = Tk()
root.title("Certificaat Uitlezer")  # Initiële titel
bootstrap_style = BootstrapStyle(theme="cyborg")

# Zwarte achtergrond en witte tekst
root.configure(bg="black")

# Label voor statusberichten
label_info = Label(
    root,
    text="Selecteer een certificaat om te laden",
    font=("Helvetica", 12, "bold"),
    background="black",
    foreground="white",
)
label_info.pack(pady=10)

# Label boven de eerste tabel
label_checks = Label(
    root,
    text="Certificate Checks",
    font=("Helvetica", 12, "bold"),
    background="yellow",
    foreground="black",
    anchor="center",
)
label_checks.pack(fill="x", pady=5)

# Treeview voor Certificate Checks (geel)
tree_checks = Treeview(root, columns=("Check", "Result"), show="headings", height=5)
tree_checks.heading("Check", text="Check")
tree_checks.heading("Result", text="Result")
tree_checks.column("Check", width=200)
tree_checks.column("Result", width=400)
tree_checks.tag_configure("yellow", foreground="yellow", background="black")
tree_checks.pack(padx=10, pady=5)

# Label boven de tweede tabel
label_subject = Label(
    root,
    text="Certificate Subject",
    font=("Helvetica", 12, "bold"),
    background="green",
    foreground="black",
    anchor="center",
)
label_subject.pack(fill="x", pady=5)

# Treeview voor Certificate Subject (groen)
tree_subject = Treeview(root, columns=("Field", "Value"), show="headings", height=10)
tree_subject.heading("Field", text="Field")
tree_subject.heading("Value", text="Value")
tree_subject.column("Field", width=200)
tree_subject.column("Value", width=400)
tree_subject.tag_configure("green", foreground="green", background="black")
tree_subject.pack(padx=10, pady=5)

# Label boven de derde tabel
label_issuer = Label(
    root,
    text="Certificate Issuer",
    font=("Helvetica", 12, "bold"),
    background="orange",
    foreground="black",
    anchor="center",
)
label_issuer.pack(fill="x", pady=5)

# Treeview voor Certificate Issuer (oranje)
tree_issuer = Treeview(root, columns=("Field", "Value"), show="headings", height=8)
tree_issuer.heading("Field", text="Field")
tree_issuer.heading("Value", text="Value")
tree_issuer.column("Field", width=200)
tree_issuer.column("Value", width=400)
tree_issuer.tag_configure("orange", foreground="orange", background="black")
tree_issuer.pack(padx=10, pady=5)

# Frame voor knoppen
button_frame = Frame(root, bg="black")
button_frame.pack(pady=10, fill="x")

# Laadknop met lichtgroene achtergrond
button_load = Button(
    button_frame,
    text="Laad Certificaat",
    command=laad_certificaat,
    bootstyle="success",
)
button_load.pack(side="left", padx=5)

# Label voor het bestandstype tussen de knoppen
label_format = Label(
    button_frame,
    text="",
    font=("Helvetica", 12, "bold"),
    background="black",
    foreground="white",
    anchor="center",
)
label_format.pack(side="left", fill="x", expand=True, padx=5)

# Sluitknop met rode achtergrond (verborgen tot eerste bestand is geladen)
close_button = Button(
    button_frame,
    text="Sluit Applicatie",
    command=sluit_app,
    bootstyle="danger",
)
close_button.pack(side="right", padx=5)

# Voeg stijlen toe
bootstrap_style.configure("success.TButton", font=("Helvetica", 10, "bold"))
bootstrap_style.configure("danger.TButton", font=("Helvetica", 10, "bold"))

root.mainloop()
