import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os
import sys

# funzione per gestire le risorse con PyInstaller
def resource_path(relative_path):
    """ Restituisce il percorso assoluto della risorsa,
        compatibile con PyInstaller (cartella temporanea _MEIPASS).
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Import dei frame (tutti nella stessa cartella)
from frame_live import create_frame_live
from frame_preparazione import create_frame_preparazione
from frame_correzione import create_frame_correzione

# Finestra principale
root = tk.Tk()
root.title("Smixer V7")

# 👇 Usa PNG per l’icona della GUI
try:
    icon_path = resource_path("icone/app.png")
    icon = tk.PhotoImage(file=icon_path)
    root.iconphoto(True, icon)
except Exception as e:
    print(f"Impossibile caricare l'icona PNG: {e}")

root.geometry("1280x800")

# Variabile per la modalità corrente
current_mode = tk.StringVar(value="Correzione")

# Variabili condivise per la configurazione
global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "current_mode": current_mode
}

# Creazione dei frame (👈 qui serviva global_config!)
frame_live = create_frame_live(root, global_config)
frame_raccolta = create_frame_raccolta(root, global_config)
frame_correzione = create_frame_correzione(root, global_config)

# Funzione per cambiare modalità
def set_mode(mode):
    current_mode.set(mode)
    for f in (frame_live, frame_raccolta, frame_correzione):
        f.pack_forget()
    if mode == "Live":
        frame_live.pack(fill="both", expand=True)
    elif mode == "Raccolta":
        frame_raccolta.pack(fill="both", expand=True)
    elif mode == "Correzione":
        frame_correzione.pack(fill="both", expand=True)

# === SALVA / CARICA CONFIG === #

def salva_configurazione():
    config = {
        "remote_directory": global_config["remote_directory"].get(),
        "file_extension": global_config["file_extension"].get(),
        "verifica_name": global_config["verifica_name"].get(),
        "current_mode": current_mode.get()
    }
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Salva configurazione"
    )
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Salvataggio riuscito", f"Configurazione salvata in {file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")


def carica_configurazione():
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")],
        title="Carica configurazione"
    )
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            global_config["remote_directory"].set(config.get("remote_directory", ""))
            global_config["file_extension"].set(config.get("file_extension", ".cpp"))
            global_config["verifica_name"].set(config.get("verifica_name", ""))
            mode = config.get("current_mode", "Correzione")
            if mode in ("Live", "Raccolta", "Correzione"):
                set_mode(mode)
            messagebox.showinfo("Caricamento riuscito", f"Configurazione caricata da {file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {e}")

# === MENU === #
menubar = tk.Menu(root)

# Menù File
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Carica configurazione", command=carica_configurazione)
file_menu.add_command(label="Salva configurazione", command=salva_configurazione)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)

# Menù Modalità
mode_menu = tk.Menu(menubar, tearoff=0)
mode_menu.add_radiobutton(label="Live", variable=current_mode, value="Live", command=lambda: set_mode("Live"))
mode_menu.add_radiobutton(label="Raccolta", variable=current_mode, value="Raccolta", command=lambda: set_mode("Raccolta"))
mode_menu.add_radiobutton(label="Correzione", variable=current_mode, value="Correzione", command=lambda: set_mode("Correzione"))
menubar.add_cascade(label="Modalità", menu=mode_menu)

# Applica il menu
root.config(menu=menubar)

# Mostra inizialmente la modalità Correzione
set_mode("Correzione")

# Avvia il mainloop
root.mainloop()
