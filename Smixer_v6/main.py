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
from frame_domini import create_frame_domini  # nuova frame Domini/FTP
from frame_associa import open_associa_window  # nuova finestra Associa


# === FINESTRA PRINCIPALE === #

root = tk.Tk()
root.title("SMX V0.811 / Gestione Elaborati ")
root.geometry("1280x800")

# Percorso all'icona (funziona anche dentro l'exe)
base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
icon_path = os.path.join(base_path, "icone", "app.ico")

if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"⚠️ Impossibile impostare l'icona: {e}")
else:
    print(f"⚠️ Icona non trovata: {icon_path}")

# Modalità corrente (default: Preparazione)
current_mode = tk.StringVar(value="Preparazione")

# Config condivisa
global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "selected_directory": tk.StringVar(value="nessuna"),
    "current_mode": current_mode,
}

# Riferimenti frame
frame_preparazione = None
frame_live = None
frame_correzione = None
frame_export = None
frame_domini = None  # nuova frame Domini/FTP


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
            messagebox.showinfo(
                "Salvataggio riuscito",
                f"Configurazione salvata in {file_path}",
            )
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


# === MENUBAR: File + Associa + Modalità === #

menubar = tk.Menu(root)

# File
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Carica configurazione", command=carica_configurazione)
file_menu.add_command(label="Salva configurazione", command=salva_configurazione)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)

# Associa (nuova voce, apre la finestra di associazione email ↔ cartelle test)
menubar.add_command(
    label="Associa",
    command=lambda: open_associa_window(root, global_config),
)

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


# === BARRA SUPERIORE: Nome + Directory selezionata === #

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


# Correzione: si usa il click sinistro del mouse
lbl_directory.bind("<Button-1>", on_directory_click)

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
