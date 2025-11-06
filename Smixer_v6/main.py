import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import json
import os

import data_handler  # per aprire la directory selezionata

# Import dei frame (li andremo a creare/aggiornare a breve)
from frame_live import create_frame_live
from frame_preparazione import create_frame_preparazione
from frame_correzione import create_frame_correzione
from frame_export import create_frame_export  # NUOVA scheda Export


# === FINESTRA PRINCIPALE === #
root = tk.Tk()
root.title("Smixer / Gestione Elaborati")
root.geometry("1280x800")

# Variabile per la modalità corrente
current_mode = tk.StringVar(value="Correzione")

# Variabili condivise per la configurazione
global_config = {
    # directory remota (usata soprattutto in Live)
    "remote_directory": tk.StringVar(),
    # estensione file (cpp, java, ecc.)
    "file_extension": tk.StringVar(value=".cpp"),
    # nome della verifica (campo “Nome” richiesto)
    "verifica_name": tk.StringVar(),
    # directory di lavoro corrente (mostrata nella barra in alto)
    "selected_directory": tk.StringVar(value="(nessuna)"),
    # modalità corrente
    "current_mode": current_mode,
}

# Riferimenti ai frame (modalità)
frame_live = None
frame_raccolta = None
frame_correzione = None
frame_export = None


# === FUNZIONE CAMBIO MODALITÀ === #
def set_mode(mode: str):
    """
    Mostra il frame corrispondente alla modalità scelta
    e nasconde gli altri.
    """
    global frame_live, frame_raccolta, frame_correzione, frame_export

    current_mode.set(mode)

    # Nascondi tutti
    for f in (frame_live, frame_raccolta, frame_correzione, frame_export):
        if f is not None:
            f.pack_forget()

    # Mostra solo il frame selezionato
    if mode == "Live" and frame_live is not None:
        frame_live.pack(fill="both", expand=True)
    elif mode == "Raccolta" and frame_raccolta is not None:
        frame_raccolta.pack(fill="both", expand=True)
    elif mode == "Correzione" and frame_correzione is not None:
        frame_correzione.pack(fill="both", expand=True)
    elif mode == "Export" and frame_export is not None:
        frame_export.pack(fill="both", expand=True)


# === SALVA / CARICA CONFIG === #
def salva_configurazione():
    config = {
        "remote_directory": global_config["remote_directory"].get(),
        "file_extension": global_config["file_extension"].get(),
        "verifica_name": global_config["verifica_name"].get(),
        "selected_directory": global_config["selected_directory"].get(),
        "current_mode": current_mode.get(),
    }
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Salva configurazione",
    )
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo(
                "Salvataggio riuscito", f"Configurazione salvata in {file_path}"
            )
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")


def carica_configurazione():
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")],
        title="Carica configurazione",
    )
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            global_config["remote_directory"].set(config.get("remote_directory", ""))
            global_config["file_extension"].set(config.get("file_extension", ".cpp"))
            global_config["verifica_name"].set(config.get("verifica_name", ""))
            global_config["selected_directory"].set(
                config.get("selected_directory", "(nessuna)")
            )

            mode = config.get("current_mode", "Correzione")
            if mode not in ("Live", "Raccolta", "Correzione", "Export"):
                mode = "Correzione"

            set_mode(mode)

            messagebox.showinfo(
                "Caricamento riuscito", f"Configurazione caricata da {file_path}"
            )
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {e}")


# === MENU PRINCIPALE === #
menubar = tk.Menu(root)

# Menù File
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Carica configurazione", command=carica_configurazione)
file_menu.add_command(label="Salva configurazione", command=salva_configurazione)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)

# NOTA: la scelta della modalità NON è più nel menù,
# ma in un menù a tendina (Combobox) nella barra superiore.
root.config(menu=menubar)


# === BARRA SUPERIORE COMUNE (Nome + Directory + Modalità) === #
top_bar = tk.Frame(root, bg="#eeeeee")
top_bar.pack(side="top", fill="x", padx=5, pady=5)

# Modalità - menù a tendina
tk.Label(top_bar, text="Modalità:", bg="#eeeeee").grid(
    row=0, column=0, padx=5, pady=2, sticky="w"
)
mode_combo = ttk.Combobox(
    top_bar,
    textvariable=current_mode,
    values=["Live", "Raccolta", "Correzione", "Export"],
    state="readonly",
    width=15,
)
mode_combo.grid(row=0, column=1, padx=5, pady=2, sticky="w")
mode_combo.bind("<<ComboboxSelected>>", lambda e: set_mode(current_mode.get()))

# Campo Nome (nome verifica)
tk.Label(top_bar, text="Nome:", bg="#eeeeee").grid(
    row=0, column=2, padx=10, pady=2, sticky="e"
)
entry_nome = tk.Entry(
    top_bar,
    textvariable=global_config["verifica_name"],
    width=30,
)
entry_nome.grid(row=0, column=3, padx=5, pady=2, sticky="w")

# Directory selezionata (cliccabile)
tk.Label(top_bar, text="Directory selezionata:", bg="#eeeeee").grid(
    row=0, column=4, padx=10, pady=2, sticky="e"
)

lbl_directory = tk.Label(
    top_bar,
    textvariable=global_config["selected_directory"],
    fg="blue",
    bg="#eeeeee",
    cursor="hand2",
)
lbl_directory.grid(row=0, column=5, padx=5, pady=2, sticky="w")


def on_directory_click(event):
    """
    Apertura nel file browser della directory attualmente selezionata.
    """
    path = global_config["selected_directory"].get()
    data_handler.open_selected_directory(path)


lbl_directory.bind("<Button-1>", on_directory_click)

# Allarga bene le colonne centrali
top_bar.grid_columnconfigure(3, weight=1)
top_bar.grid_columnconfigure(5, weight=1)


# === CONTENITORE DEI FRAME (MODALITÀ) === #
content_frame = tk.Frame(root)
content_frame.pack(side="top", fill="both", expand=True)

# Creazione dei frame delle varie modalità
frame_live = create_frame_live(content_frame, global_config)
frame_raccolta = create_frame_preparazione(content_frame, global_config)
frame_correzione = create_frame_correzione(content_frame, global_config)
frame_export = create_frame_export(content_frame, global_config)  # da implementare


# Mostra inizialmente la modalità Correzione
set_mode("Correzione")

# Avvia il mainloop
root.mainloop()
