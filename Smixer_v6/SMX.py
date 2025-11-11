import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import sys
import json
import os

import data_handler
from frame_live import create_frame_live
from frame_preparazione import create_frame_preparazione
from frame_correzione import create_frame_correzione
from frame_export import create_frame_export
from frame_domini import create_frame_domini  # frame Domini / FTP
from frame_associa import open_associa_window  # finestra Associa email ↔ cartelle


# === FINESTRA PRINCIPALE === #

root = tk.Tk()
root.title("SMX V0.82 / Gestione Elaborati ")
root.geometry("1280x800")

# Percorso all'icona (funziona anche dentro l'exe)
base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
icon_path = os.path.join(base_path, "icone", "app.ico")

if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print("⚠️ Impossibile impostare l'icona:", e)
else:
    print("⚠️ Icona non trovata:", icon_path)

# Modalità corrente (default: Preparazione)
current_mode = tk.StringVar(value="Preparazione")

# Config condivisa
global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "selected_directory": tk.StringVar(value="nessuna"),
    "current_mode": current_mode,
    # callback opzionali per il pulsante "Aggiorna cartella"
    "refresh_preparazione": None,
    "refresh_live": None,
    "refresh_correzione": None,
    "refresh_export": None,
    "refresh_domini": None,
}

# Riferimenti frame
frame_preparazione = None
frame_live = None
frame_correzione = None
frame_export = None
frame_domini = None  # frame Domini/FTP


# === CAMBIO MODALITÀ === #

def set_mode(mode: str) -> None:
    global frame_preparazione, frame_live, frame_correzione, frame_export, frame_domini

    current_mode.set(mode)

    # Nasconde tutti i frame
    for f in (frame_preparazione, frame_live, frame_correzione, frame_export, frame_domini):
        if f is not None:
            f.pack_forget()

    # Mostra solo il frame corrispondente
    if mode == "Preparazione" and frame_preparazione is not None:
        frame_preparazione.pack(fill="both", expand=True)
    elif mode == "Live" and frame_live is not None:
        frame_live.pack(fill="both", expand=True)
    elif mode == "Correzione" and frame_correzione is not None:
        frame_correzione.pack(fill="both", expand=True)
    elif mode == "Export" and frame_export is not None:
        frame_export.pack(fill="both", expand=True)
    elif mode == "Domini" and frame_domini is not None:
        frame_domini.pack(fill="both", expand=True)


# === SALVA / CARICA CONFIG === #

def salva_configurazione() -> None:
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
            messagebox.showinfo("Salvataggio riuscito", f"Configurazione salvata in {file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")


def carica_configurazione() -> None:
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
                config.get("selected_directory", "nessuna")
            )

            mode = config.get("current_mode", "Preparazione")
            if mode not in ("Preparazione", "Live", "Correzione", "Export", "Domini"):
                mode = "Preparazione"

            set_mode(mode)

            messagebox.showinfo(
                "Caricamento riuscito",
                f"Configurazione caricata da {file_path}",
            )
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {e}")


# === FUNZIONE GLOBALE: REFRESH DIRECTORY (usata dal bottone in header) === #

def refresh_current_directory() -> None:
    """
    Prova a richiamare un callback specifico in base alla modalità corrente
    (ad esempio Correzione / Export), altrimenti forza un "ritrascinamento"
    della stessa directory per riattivare le trace collegate.
    """
    mode = current_mode.get()

    handler_key = None
    if mode == "Preparazione":
        handler_key = "refresh_preparazione"
    elif mode == "Live":
        handler_key = "refresh_live"
    elif mode == "Correzione":
        handler_key = "refresh_correzione"
    elif mode == "Export":
        handler_key = "refresh_export"
    elif mode == "Domini":
        handler_key = "refresh_domini"

    handler = None
    if handler_key is not None:
        handler = global_config.get(handler_key)

    if callable(handler):
        handler()
    else:
        selected_var = global_config.get("selected_directory")
        if selected_var is not None and hasattr(selected_var, "get") and hasattr(selected_var, "set"):
            current_value = selected_var.get()
            # Scrivere lo stesso valore su una StringVar innesca comunque la trace
            selected_var.set(current_value)


# === MENUBAR: File + Associa + Modalità === #

menubar = tk.Menu(root)

# File
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Carica configurazione", command=carica_configurazione)
file_menu.add_command(label="Salva configurazione", command=salva_configurazione)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)


def apri_finestra_associa() -> None:
    open_associa_window(root, global_config)


# Voce singola "Associa"
menubar.add_command(label="Associa", command=apri_finestra_associa)

# Modalità (ordine: Preparazione, Live, Correzione, Export, Domini)
mode_menu = tk.Menu(menubar, tearoff=0)
mode_menu.add_radiobutton(
    label="Preparazione",
    variable=current_mode,
    value="Preparazione",
    command=lambda: set_mode("Preparazione"),
)
mode_menu.add_radiobutton(
    label="Live",
    variable=current_mode,
    value="Live",
    command=lambda: set_mode("Live"),
)
mode_menu.add_radiobutton(
    label="Domini / FTP",
    variable=current_mode,
    value="Domini",
    command=lambda: set_mode("Domini"),
)
mode_menu.add_radiobutton(
    label="Correzione",
    variable=current_mode,
    value="Correzione",
    command=lambda: set_mode("Correzione"),
)
mode_menu.add_radiobutton(
    label="Export",
    variable=current_mode,
    value="Export",
    command=lambda: set_mode("Export"),
)

menubar.add_cascade(label="Modalità", menu=mode_menu)

root.config(menu=menubar)


# === BARRA SUPERIORE: Nome verifica + Directory selezionata + AGGIORNA === #

top_bar = tk.Frame(root, bg="#eeeeee")
top_bar.pack(side="top", fill="x", padx=5, pady=5)

tk.Label(top_bar, text="Nome Verifica:", bg="#eeeeee").grid(
    row=0,
    column=0,
    padx=5,
    pady=2,
    sticky="e",
)

entry_nome = tk.Entry(
    top_bar,
    textvariable=global_config["verifica_name"],
    width=30,
)
entry_nome.grid(row=0, column=1, padx=5, pady=2, sticky="w")

tk.Label(top_bar, text="Directory selezionata:", bg="#eeeeee").grid(
    row=0,
    column=2,
    padx=10,
    pady=2,
    sticky="e",
)

lbl_directory = tk.Label(
    top_bar,
    textvariable=global_config["selected_directory"],
    fg="blue",
    bg="#eeeeee",
    cursor="hand2",
    anchor="w",
)
lbl_directory.grid(row=0, column=3, padx=5, pady=2, sticky="w")


def on_directory_click(event) -> None:
    """
    Se directory è 'nessuna' → chiedi con filedialog.
    Se c'è un percorso valido → apri file manager.
    """
    path = global_config["selected_directory"].get().strip()

    if not path or path.lower() == "nessuna":
        selected = filedialog.askdirectory(
            title="Seleziona directory locale di lavoro (cartelle testXX)"
        )
        if selected:
            global_config["selected_directory"].set(selected)
    else:
        data_handler.open_selected_directory(path)


lbl_directory.bind("<Button-1>", on_directory_click)

# Nuovo bottone "Aggiorna cartella"
btn_refresh_dir = tk.Button(
    top_bar,
    text="Aggiorna cartella",
    command=refresh_current_directory,
)
btn_refresh_dir.grid(row=0, column=4, padx=5, pady=2, sticky="w")

top_bar.grid_columnconfigure(3, weight=1)


# === CONTENITORE FRAME === #

content_frame = tk.Frame(root)
content_frame.pack(side="top", fill="both", expand=True)

# Creazione frame in ordine: Preparazione, Live, Correzione, Export, Domini
frame_preparazione = create_frame_preparazione(content_frame, global_config)
frame_live = create_frame_live(content_frame, global_config)
frame_correzione = create_frame_correzione(content_frame, global_config)
frame_export = create_frame_export(content_frame, global_config)
frame_domini = create_frame_domini(content_frame, global_config)

# Modalità iniziale: Preparazione
set_mode("Preparazione")

if __name__ == "__main__":
    root.mainloop()
