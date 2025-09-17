import tkinter as tk
from tkinter import messagebox
import os

# Import dei frame
from frame_preparazione import create_frame_preparazione
from frame_live import create_frame_live
from frame_correzione import create_frame_correzione

import utils

# === Finestra principale === #
root = tk.Tk()
root.title("Smixer V7")

# Usa la stessa icona anche per la finestra
root.iconbitmap("icone/app.ico")

root.geometry("1280x800")

# Variabile per la modalità corrente
current_mode = tk.StringVar(value="Preparazione")

# Variabili condivise per la configurazione
global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "current_mode": current_mode,
    # nuove variabili persistenti
    "include_prompt": tk.BooleanVar(value=True),
    "include_subdir": tk.BooleanVar(value=True),
    "intro_text": tk.StringVar(value=""),
    "last_copy_timestamp": tk.StringVar(value="")
}

# === Creazione dei frame === #
frame_preparazione = create_frame_preparazione(root, global_config)
frame_live = create_frame_live(root, global_config)
frame_correzione = create_frame_correzione(root, global_config)


# === Cambio modalità === #
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


# === Salvataggio configurazione === #
def salva_configurazione():
    config = {
        "remote_directory": global_config["remote_directory"].get(),
        "file_extension": global_config["file_extension"].get(),
        "verifica_name": global_config["verifica_name"].get(),
        "current_mode": current_mode.get(),
        "include_prompt": global_config["include_prompt"].get(),
        "include_subdir": global_config["include_subdir"].get(),
        "intro_text": global_config["intro_text"].get(),
        "last_copy_timestamp": global_config["last_copy_timestamp"].get()
    }
    utils.salva_configurazione(config)


# === Caricamento configurazione === #
def carica_configurazione():
    config = utils.carica_configurazione()
    if config:
        global_config["remote_directory"].set(config.get("remote_directory", ""))
        global_config["file_extension"].set(config.get("file_extension", ".cpp"))
        global_config["verifica_name"].set(config.get("verifica_name", ""))
        global_config["current_mode"].set(config.get("current_mode", "Preparazione"))

        global_config["include_prompt"].set(config.get("include_prompt", True))
        global_config["include_subdir"].set(config.get("include_subdir", True))
        global_config["intro_text"].set(config.get("intro_text", ""))
        global_config["last_copy_timestamp"].set(config.get("last_copy_timestamp", ""))

        set_mode(config.get("current_mode", "Preparazione"))
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
mode_menu.add_radiobutton(
    label="Preparazione",
    variable=current_mode,
    value="Preparazione",
    command=lambda: set_mode("Preparazione")
)
mode_menu.add_radiobutton(
    label="Live",
    variable=current_mode,
    value="Live",
    command=lambda: set_mode("Live")
)
mode_menu.add_radiobutton(
    label="Correzione",
    variable=current_mode,
    value="Correzione",
    command=lambda: set_mode("Correzione")
)
menubar.add_cascade(label="Modalità", menu=mode_menu)

# Applica il menu
root.config(menu=menubar)

# Mostra inizialmente la modalità Preparazione
set_mode("Preparazione")

# Avvia il mainloop
root.mainloop()
