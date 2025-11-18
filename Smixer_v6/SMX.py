import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import tkinter.font as tkfont
import sys
import json
import os

import data_handler
from frame_live import create_frame_live
from frame_preparazione import create_frame_preparazione
from frame_correzione import create_frame_correzione
from frame_export import create_frame_export
from frame_domini import create_frame_domini
from frame_associa import open_associa_window


# =========================
# FINESTRA PRINCIPALE
# =========================

root = tk.Tk()
root.title("SMX V085 / Gestione Elaborati")
root.geometry("1280x800")

# Icona (se presente)
base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
icon_path = os.path.join(base_path, "icone", "app.ico")
if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except Exception:
        pass


# =========================
# STATO GLOBALE
# =========================

current_mode = tk.StringVar(value="Preparazione")

global_config = {
    "remote_directory": tk.StringVar(),
    "file_extension": tk.StringVar(value=".cpp"),
    "verifica_name": tk.StringVar(),
    "selected_directory": tk.StringVar(value="nessuna"),
    "current_mode": current_mode,

    # Riferimento al file CSV che contiene i dati di autenticazione / lista domini
    # verrà salvato e ricaricato nel file di configurazione JSON
    "domains_csv_path": tk.StringVar(),
    "ftp_config_path": tk.StringVar(),


    # callback opzionali per pulsante "Aggiorna cartella"
    "refresh_preparazione": None,
    "refresh_live": None,
    "refresh_correzione": None,
    "refresh_export": None,
    "refresh_domini": None,

    # eventuali credenziali Dominii/FTP (se frame_domini le inserisce qui)
    # Esempi:
    # "dom_host": tk.StringVar(),
    # "dom_user": tk.StringVar(),
    # "dom_pass": tk.StringVar(),
    # "dom_port": tk.StringVar(),
    # "dom_tls": tk.BooleanVar(),
    #
    # oppure in forma nidificata:
    # "domini": {"host": tk.StringVar(), "user": tk.StringVar(), ...}
}

# Riferimenti frame
frame_preparazione = None
frame_live = None
frame_correzione = None
frame_export = None
frame_domini = None


# =========================
# FUNZIONI DI NAVIGAZIONE
# =========================

def set_mode_preparazione():
    current_mode.set("Preparazione")
    _show_only("Preparazione")


def set_mode_live():
    current_mode.set("Live")
    _show_only("Live")


def set_mode_correzione():
    current_mode.set("Correzione")
    _show_only("Correzione")


def set_mode_export():
    current_mode.set("Export")
    _show_only("Export")


def set_mode_domini():
    current_mode.set("Domini")
    _show_only("Domini")


def _show_only(mode_name: str):
    """
    Mostra solo il frame corrispondente a mode_name,
    nascondendo tutti gli altri.
    """
    frames = {
        "Preparazione": frame_preparazione,
        "Live": frame_live,
        "Correzione": frame_correzione,
        "Export": frame_export,
        "Domini": frame_domini,
    }

    for key, frm in frames.items():
        if frm is not None:
            frm.pack_forget()

    target = frames.get(mode_name)
    if target is not None:
        target.pack(fill="both", expand=True)


# =========================
# PERSISTENZA CONFIGURAZIONE
# =========================

def salva_configurazione():
    """
    Salva su file JSON:
      - remote_directory
      - file_extension
      - verifica_name
      - selected_directory
      - current_mode
      - domains_csv_path (percorso file CSV con dati domini)
      - eventuali credenziali dom_* e dizionario "domini"
    """
    config = {
        "remote_directory": global_config["remote_directory"].get(),
        "file_extension": global_config["file_extension"].get(),
        "verifica_name": global_config["verifica_name"].get(),
        "selected_directory": global_config["selected_directory"].get(),
        "current_mode": current_mode.get(),
        "domains_csv_path": global_config["domains_csv_path"].get(),
    }

    # Persistenza credenziali, se presenti
    for key in ("dom_host", "dom_user", "dom_pass", "dom_port", "dom_tls"):
        if key in global_config:
            val = global_config[key]
            try:
                if hasattr(val, "get"):
                    config[key] = val.get()
                else:
                    config[key] = val
            except Exception:
                config[key] = str(val)

    if "domini" in global_config and isinstance(global_config["domini"], dict):
        dom_dict = {}
        for k, v in global_config["domini"].items():
            try:
                if hasattr(v, "get"):
                    dom_dict[k] = v.get()
                else:
                    dom_dict[k] = v
            except Exception:
                dom_dict[k] = str(v)
        config["domini"] = dom_dict

    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Salva configurazione",
    )

    if not file_path:
        return

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        messagebox.showinfo(
            "Salvataggio riuscito",
            "Configurazione salvata in " + file_path
        )
    except Exception as e:
        messagebox.showerror("Errore", "Errore nel salvataggio: " + str(e))


def carica_configurazione():
    """
    Carica da file JSON:
      - remote_directory
      - file_extension
      - verifica_name
      - selected_directory
      - current_mode
      - domains_csv_path
      - eventuali credenziali dom_* e dizionario "domini"

    Dopo aver impostato current_mode viene mostrato il frame
    corrispondente. La variabile domains_csv_path viene popolata
    e può essere utilizzata da frame_domini per leggere la lista domini.
    """
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")],
        title="Carica configurazione",
    )

    if not file_path or not os.path.exists(file_path):
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        global_config["remote_directory"].set(
            config.get("remote_directory", "")
        )
        global_config["file_extension"].set(
            config.get("file_extension", ".cpp")
        )
        global_config["verifica_name"].set(
            config.get("verifica_name", "")
        )
        global_config["selected_directory"].set(
            config.get("selected_directory", "nessuna")
        )
        global_config["domains_csv_path"].set(
            config.get("domains_csv_path", "")
        )

        mode_val = config.get("current_mode", "Preparazione")
        if mode_val not in ("Preparazione", "Live", "Correzione", "Export", "Domini"):
            mode_val = "Preparazione"

        current_mode.set(mode_val)
        _show_only(mode_val)

        # Ripristino credenziali se presenti
        for key in ("dom_host", "dom_user", "dom_pass", "dom_port", "dom_tls"):
            if key in config and key in global_config:
                target = global_config[key]
                try:
                    if hasattr(target, "set"):
                        target.set(config[key])
                    else:
                        global_config[key] = config[key]
                except Exception:
                    global_config[key] = config[key]

        # Ripristino eventuale dizionario "domini"
        if "domini" in config and "domini" in global_config and isinstance(global_config["domini"], dict):
            for k, v in config["domini"].items():
                if k in global_config["domini"]:
                    tgt = global_config["domini"][k]
                    try:
                        if hasattr(tgt, "set"):
                            tgt.set(v)
                        else:
                            global_config["domini"][k] = v
                    except Exception:
                        global_config["domini"][k] = v

        messagebox.showinfo(
            "Caricamento riuscito",
            "Configurazione caricata da " + file_path
        )

    except Exception as e:
        messagebox.showerror("Errore", "Errore nel caricamento: " + str(e))


# =========================
# MENUBAR
# (con stato modalità in grassetto dopo "Modalità")
# =========================

menubar = tk.Menu(root)

# --- File
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Carica configurazione", command=carica_configurazione)
file_menu.add_command(label="Salva configurazione", command=salva_configurazione)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)


# --- Associa
def apri_finestra_associa():
    open_associa_window(root, global_config)


menubar.add_command(label="Associa", command=apri_finestra_associa)


# --- Modalità (cascade)
mode_menu = tk.Menu(menubar, tearoff=0)
mode_menu.add_radiobutton(
    label="Preparazione",
    variable=current_mode,
    value="Preparazione",
    command=set_mode_preparazione
)
mode_menu.add_radiobutton(
    label="Live",
    variable=current_mode,
    value="Live",
    command=set_mode_live
)
mode_menu.add_radiobutton(
    label="Domini / FTP",
    variable=current_mode,
    value="Domini",
    command=set_mode_domini
)
mode_menu.add_radiobutton(
    label="Correzione",
    variable=current_mode,
    value="Correzione",
    command=set_mode_correzione
)
mode_menu.add_radiobutton(
    label="Export",
    variable=current_mode,
    value="Export",
    command=set_mode_export
)
menubar.add_cascade(label="    Modalità", menu=mode_menu)


# --- Etichetta stato modalità in grassetto, subito dopo "Modalità"

mode_status_font = tkfont.nametofont("TkMenuFont").copy()
mode_status_font.configure(weight="bold")
_mode_status_index = None


def _init_mode_status_entry():
    """
    Aggiunge una voce di menu disabilitata che mostra la modalità corrente.
    """
    global _mode_status_index

    label_text = "Modalità: " + current_mode.get()
    menubar.add_cascade(
        label=label_text,
        state="disabled",
        font=mode_status_font
    )
    _mode_status_index = menubar.index("end")


def _on_mode_change(*_args):
    """
    Aggiorna il testo della voce di stato modalità quando current_mode cambia.
    """
    if _mode_status_index is not None:
        menubar.entryconfig(
            _mode_status_index,
            label="Modalità: " + current_mode.get()
        )


if hasattr(current_mode, "trace_add"):
    current_mode.trace_add("write", _on_mode_change)
else:
    current_mode.trace("w", _on_mode_change)

_init_mode_status_entry()
root.config(menu=menubar)


# =========================
# BARRA SUPERIORE
# (Nome, Modifica cartella, Directory, Aggiorna)
# =========================

top_bar = tk.Frame(root, bg="#eeeeee")
top_bar.pack(side="top", fill="x", padx=5, pady=5)

lbl_nome = tk.Label(top_bar, text="Nome Verifica:", bg="#eeeeee")
lbl_nome.grid(row=0, column=0, padx=5, pady=2, sticky="e")

entry_nome = tk.Entry(top_bar, textvariable=global_config["verifica_name"], width=30)
entry_nome.grid(row=0, column=1, padx=5, pady=2, sticky="w")


def _modifica_cartella():
    """
    Permette di scegliere la directory locale di lavoro (cartelle testXX).
    """
    selected = filedialog.askdirectory(
        title="Seleziona directory locale di lavoro (cartelle testXX)"
    )
    if selected:
        global_config["selected_directory"].set(selected)


btn_modifica = tk.Button(top_bar, text="Modifica cartella", command=_modifica_cartella)
btn_modifica.grid(row=0, column=2, padx=5, pady=2, sticky="w")

lbl_dir_title = tk.Label(top_bar, text="Directory selezionata:", bg="#eeeeee")
lbl_dir_title.grid(row=0, column=3, padx=10, pady=2, sticky="e")

lbl_directory = tk.Label(
    top_bar,
    textvariable=global_config["selected_directory"],
    fg="blue",
    bg="#eeeeee",
    cursor="hand2",
    anchor="w",
)
lbl_directory.grid(row=0, column=4, padx=5, pady=2, sticky="w")


def on_directory_click(event):
    """
    Se non c'è directory selezionata, apre il dialogo di scelta.
    Altrimenti prova ad aprire la directory esistente.
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


# Binding corretto del click sinistro sul label directory
lbl_directory.bind("<Button-1>", on_directory_click)


def refresh_current_directory():
    """
    Invoca la callback di refresh relativa alla modalità corrente,
    se definita in global_config. In caso contrario forza un "refresh" minimo
    riapplicando la stessa selected_directory.
    """
    mode = current_mode.get()
    key = None

    if mode == "Preparazione":
        key = "refresh_preparazione"
    elif mode == "Live":
        key = "refresh_live"
    elif mode == "Correzione":
        key = "refresh_correzione"
    elif mode == "Export":
        key = "refresh_export"
    elif mode == "Domini":
        key = "refresh_domini"

    handler = None
    if key is not None:
        handler = global_config.get(key)

    if callable(handler):
        handler()
    else:
        sel = global_config["selected_directory"]
        sel.set(sel.get())


btn_refresh_dir = tk.Button(top_bar, text="Aggiorna cartella", command=refresh_current_directory)
btn_refresh_dir.grid(row=0, column=5, padx=5, pady=2, sticky="w")

top_bar.grid_columnconfigure(4, weight=1)


# =========================
# CONTENITORE FRAME
# =========================

content_frame = tk.Frame(root)
content_frame.pack(side="top", fill="both", expand=True)

frame_preparazione = create_frame_preparazione(content_frame, global_config)
frame_live = create_frame_live(content_frame, global_config)
frame_correzione = create_frame_correzione(content_frame, global_config)
frame_export = create_frame_export(content_frame, global_config)
frame_domini = create_frame_domini(content_frame, global_config)

# Modalità iniziale
_show_only("Preparazione")


if __name__ == "__main__":
    root.mainloop()
