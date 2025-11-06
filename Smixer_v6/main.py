import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os
import sys

def resource_path(relative_path):
    """Gestisce il percorso delle risorse anche in eseguibili PyInstaller."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Import dei frame (usano global_config)
from frame_live import create_frame_live
from frame_preparazione import create_frame_preparazione
from frame_correzione import create_frame_correzione

# ---- App ----
root = tk.Tk()
root.title("Smixer V0.8")

# Icona (se disponibile)
try:
    icon_path = resource_path("icone/app.png")
    if os.path.exists(icon_path):
        icon = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon)
except Exception as e:
    print(f"Impossibile caricare l'icona: {e}")

root.geometry("1280x800")

# Stato globale condiviso
current_mode = tk.StringVar(value="Preparazione")  # Avvio su Preparazione

global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "current_mode": current_mode,
    "intro_text": tk.StringVar(value=""),
    "include_prompt": tk.BooleanVar(value=True),
    "include_subdir": tk.BooleanVar(value=True),
    "last_copy_timestamp": tk.StringVar(value=""),
    # Radice/pattern cartelle (di default: test*)
    "root_prefix": tk.StringVar(value="test*"),
}

# --- CREAZIONE FRAME NELL’ORDINE RICHIESTO: Preparazione → Live → Correzione --- #
frame_preparazione = create_frame_preparazione(root, global_config)
frame_live = create_frame_live(root, global_config)
frame_correzione = create_frame_correzione(root, global_config)

# --- Gestione cambio modalità --- #
def set_mode(mode: str):
    current_mode.set(mode)
    for f in (frame_preparazione, frame_live, frame_correzione):
        f.pack_forget()
    if mode == "Preparazione":
        frame_preparazione.pack(fill="both", expand=True)
    elif mode == "Live":
        frame_live.pack(fill="both", expand=True)
    elif mode == "Correzione":
        frame_correzione.pack(fill="both", expand=True)

# --- Salvataggio/Caricamento configurazione --- #
def salva_configurazione():
    config = {
        "remote_directory": global_config["remote_directory"].get(),
        "file_extension": global_config["file_extension"].get(),
        "verifica_name": global_config["verifica_name"].get(),
        "current_mode": current_mode.get(),
        "intro_text": global_config["intro_text"].get(),
        "include_prompt": global_config["include_prompt"].get(),
        "include_subdir": global_config["include_subdir"].get(),
        "last_copy_timestamp": global_config["last_copy_timestamp"].get(),
        "root_prefix": global_config["root_prefix"].get(),
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
            global_config["intro_text"].set(config.get("intro_text", ""))
            global_config["include_prompt"].set(config.get("include_prompt", True))
            global_config["include_subdir"].set(config.get("include_subdir", True))
            global_config["last_copy_timestamp"].set(config.get("last_copy_timestamp", ""))
            global_config["root_prefix"].set(config.get("root_prefix", "test*"))
            mode = config.get("current_mode", "Preparazione")
            if mode in ("Preparazione", "Live", "Correzione"):
                set_mode(mode)
            messagebox.showinfo("Caricamento riuscito", f"Configurazione caricata da {file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {e}")

# --- Menu --- #
menubar = tk.Menu(root)

file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Carica configurazione", command=carica_configurazione)
file_menu.add_command(label="Salva configurazione", command=salva_configurazione)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)

mode_menu = tk.Menu(menubar, tearoff=0)
mode_menu.add_radiobutton(label="Preparazione", variable=current_mode, value="Preparazione", command=lambda: set_mode("Preparazione"))
mode_menu.add_radiobutton(label="Live", variable=current_mode, value="Live", command=lambda: set_mode("Live"))
mode_menu.add_radiobutton(label="Correzione", variable=current_mode, value="Correzione", command=lambda: set_mode("Correzione"))
menubar.add_cascade(label="Modalità", menu=mode_menu)

root.config(menu=menubar)

# Avvio su Preparazione
set_mode("Preparazione")

root.mainloop()
