import tkinter as tk
from tkinter import messagebox
import os

# Import dei frame
from frame_preparazione import create_frame_preparazione
from frame_live import create_frame_live
from frame_correzione import create_frame_correzione

import utils

# Finestra principale
root = tk.Tk()
root.title("Smixer V7")
root.geometry("1280x800")

# Variabile per la modalità corrente
current_mode = tk.StringVar(value="Preparazione")

# Variabili condivise per la configurazione
global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "current_mode": current_mode
}

# Creazione dei frame
frame_preparazione = create_frame_preparazione(root, global_config)
frame_live = create_frame_live(root, global_config)
frame_correzione = create_frame_correzione(root, global_config)


# Funzione per cambiare modalità
def set_mode(mode):
    current_mode.set(mode)
    for f in (frame_preparazione, frame_live, frame_correzione):
        f.pack_forget()
    if mode == "Preparazione":
        frame_preparazione.pack(fill="both", expand=True)
    elif mode == "Live":
        frame_live.pack(fill="both", expand=True)
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
    utils.salva_configurazione(config)


def carica_configurazione():
    config = utils.carica_configurazione()
    if config:
        global_config["remote_directory"].set(config.get("remote_directory", ""))
        global_config["file_extension"].set(config.get("file_extension", ".cpp"))
        global_config["verifica_name"].set(config.get("verifica_name", ""))
        mode = config.get("current_mode", "Preparazione")
        if mode in ("Preparazione", "Live", "Correzione"):
            set_mode(mode)
        messagebox.showinfo("Caricamento riuscito", "Configurazione caricata correttamente.")


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
mode_menu.add_radiobutton(label="Preparazione", variable=current_mode, value="Preparazione", command=lambda: set_mode("Preparazione"))
mode_menu.add_radiobutton(label="Live", variable=current_mode, value="Live", command=lambda: set_mode("Live"))
mode_menu.add_radiobutton(label="Correzione", variable=current_mode, value="Correzione", command=lambda: set_mode("Correzione"))
menubar.add_cascade(label="Modalità", menu=mode_menu)

# Applica il menu
root.config(menu=menubar)

# Mostra inizialmente la modalità Preparazione
set_mode("Preparazione")

# Avvia il mainloop
root.mainloop()
