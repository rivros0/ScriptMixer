# frame_correzione.py

import tkinter as tk
from tkinter import ttk, messagebox, Scrollbar
import os
import sys

# Aggiunge la cartella superiore al path per gli import locali
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import utils
import business_logic
import similarity
import data_handler


YELLOW_REPORT_BG = "white"


def create_frame_correzione(root, global_config):
    """
    Modalità 'Correzione'.

    Usa:
      - global_config["file_extension"]
      - global_config["selected_directory"]
      - global_config["refresh_correzione"] (callback per il pulsante "Aggiorna cartella" in header)
    """

    frame_correzione = tk.Frame(root, bg="#089C52")

    include_prompt_var = tk.BooleanVar(value=True)
    include_subdir_var = tk.BooleanVar(value=True)

    # ======================================================================
    # RIGA 0: ESTENSIONE (spostata PRIMA dell'INTRO)
    # ======================================================================
    lbl_extension = tk.Label(frame_correzione, text="Estensione dei file:", bg="white")
    lbl_extension.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    entry_extension = tk.Entry(
        frame_correzione,
        textvariable=global_config["file_extension"],
        width=15,
    )
    entry_extension.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    # ======================================================================
    # RIGA 1: INTRO / PROMPT
    # ======================================================================
    lbl_prompt = tk.Label(frame_correzione, text="INTRO:", bg="white")
    lbl_prompt.grid(row=1, column=0, sticky="nw", padx=10, pady=5)

    entry_prompt = tk.Text(frame_correzione, width=80, height=3)
    entry_prompt.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    # ======================================================================
    # RIGA 2: CHECKBOX INTRO / SUBDIR + PULSANTE MIX
    # ======================================================================
    btn_mix = tk.Button(frame_correzione, text="Mixa")
    btn_mix.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

    chk_include_prompt = tk.Checkbutton(
        frame_correzione,
        text="Includi Intro",
        variable=include_prompt_var,
        bg="white",
    )
    chk_include_prompt.grid(row=2, column=1, sticky="w", padx=10, pady=2)

    chk_include_subdir = tk.Checkbutton(
        frame_correzione,
        text="Includi Nome (subdir)",
        variable=include_subdir_var,
        bg="white",
    )
    chk_include_subdir.grid(row=2, column=2, sticky="w", padx=10, pady=2)

    # ======================================================================
    # RIGA 3: TREEVIEW RIEPILOGO SUBDIRECTORY
    # ======================================================================
    tree = ttk.Treeview(
        frame_correzione,
        columns=(
            "subdirectory",
            "num_folders",
            "num_files",
            "num_extension_files",
            "extension_files",
        ),
        show="headings",
    )
    tree.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

    tree.heading("subdirectory", text="Subdirectory")
    tree.heading("num_folders", text="Cartelle")
    tree.heading("num_files", text="File")
    tree.heading("num_extension_files", text="File con Estensione")
    tree.heading("extension_files", text="Elenco File Estensione")

    tree.column("subdirectory", width=120, anchor="w")
    tree.column("num_folders", width=80, anchor="center")
    tree.column("num_files", width=80, anchor="center")
    tree.column("num_extension_files", width=140, anchor="center")
    tree.column("extension_files", width=400, anchor="w")

    frame_correzione.columnconfigure(2, weight=1)
    frame_correzione.rowconfigure(3, weight=1)

    # ======================================================================
    # RIGA 4: PULSANTI OUTPUT / ANALISI
    # ======================================================================
    btn_open_directory = tk.Button(frame_correzione, text="Apri Directory Output")
    btn_open_directory.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

    btn_analyze = tk.Button(frame_correzione, text="Analizza Similarità")
    btn_analyze.grid(row=4, column=1, sticky="ew", padx=10, pady=5)

    # ======================================================================
    # RIGHE 5-6: LOG / REPORT
    # ======================================================================
    lbl_report = tk.Label(frame_correzione, text="Log / Report:", bg="white")
    lbl_report.grid(row=5, column=0, sticky="nw", padx=10, pady=5)

    report_text = tk.Text(
        frame_correzione,
        width=100,
        height=10,
        bg=YELLOW_REPORT_BG,
    )
    report_text.grid(
        row=6,
        column=0,
        columnspan=3,
        sticky="nsew",
        padx=10,
        pady=5,
    )

    scrollbar = Scrollbar(frame_correzione, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=6, column=3, sticky="ns", pady=5)
    report_text.config(yscrollcommand=scrollbar.set)

    frame_correzione.rowconfigure(6, weight=1)

    # ======================================================================
    # LOGICA DI AGGIORNAMENTO (selected_directory)
    # ======================================================================

    def refresh_current_directory_state():
        """
        Aggiorna log e tabella in base alla directory selezionata globale.

        Usato:
          - dal trace su global_config["selected_directory"]
          - dal pulsante 'Aggiorna cartella' nella barra superiore
            tramite global_config["refresh_correzione"].
        """
        path = global_config["selected_directory"].get().strip()

        if not path or path.lower() == "nessuna":
            report_text.delete("1.0", "end")
            tree.delete(*tree.get_children())
            report_text.insert(
                "end",
                "Nessuna directory selezionata.\n"
                "Seleziona la directory dalla barra superiore (clic sulla voce blu)\n"
                "oppure crea una copia locale dalla scheda Preparazione o Live.\n",
            )
            report_text.see("end")
            return

        if not os.path.isdir(path):
            report_text.delete("1.0", "end")
            tree.delete(*tree.get_children())
            report_text.insert(
                "end",
                "La directory selezionata non esiste:\n" + path + "\n",
            )
            report_text.see("end")
            return

        # Aggiorna log con lista file
        utils.update_directory_listing(path, entry_extension, report_text)

        # Aggiorna tabella subdirectory
        utils.update_subdirectories_list(path, tree, entry_extension)

    def on_selected_directory_change(*_args):
        """
        Richiamata quando cambia global_config["selected_directory"].
        """
        refresh_current_directory_state()

    sel_dir_var = global_config.get("selected_directory")
    if sel_dir_var is not None:
        if hasattr(sel_dir_var, "trace_add"):
            sel_dir_var.trace_add("write", on_selected_directory_change)
        elif hasattr(sel_dir_var, "trace"):
            sel_dir_var.trace("w", on_selected_directory_change)

    # Registrazione callback per il pulsante globale "Aggiorna cartella"
    global_config["refresh_correzione"] = refresh_current_directory_state

    # ======================================================================
    # CALLBACK PULSANTI
    # ======================================================================

    def do_mix():
        """
        Avvia il mix dei file per le sottocartelle elencate nella tabella.
        Usa la directory globale selezionata.
        """
        business_logic.mix_files(
            global_config["selected_directory"],  # StringVar (gestita da _resolve_base_directory)
            entry_prompt,
            entry_extension,
            tree,
            report_text,
            include_prompt_var.get(),
            include_subdir_var.get(),
        )

    def apri_directory_output():
        """
        Apre la directory 00_MixOutput sotto la directory selezionata.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or base_dir.lower() == "nessuna":
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima una directory di lavoro (Preparazione / Correzione).",
            )
            return

        output_dir = os.path.join(base_dir, "00_MixOutput")
        data_handler.open_selected_directory(output_dir)

    def analizza_similarita():
        """
        Avvia l'analisi delle similarità sui file *_mix.txt presenti in 00_MixOutput.
        """
        similarity.analyze_similarities(global_config["selected_directory"], report_text)

    btn_mix.config(command=do_mix)
    btn_open_directory.config(command=apri_directory_output)
    btn_analyze.config(command=analizza_similarita)

    # ======================================================================
    # MESSAGGIO INIZIALE
    # ======================================================================
    report_text.insert(
        "end",
        "Modalità Correzione pronta.\n"
        "1) Seleziona la directory di lavoro dalla barra superiore (clic sulla directory blu)\n"
        "   oppure crea una copia locale in Preparazione / Live.\n"
        "2) Imposta l'estensione (es. .cpp) e l'INTRO se desiderato.\n"
        "3) Premi 'Mixa' per generare i file *_mix.txt in 00_MixOutput.\n"
        "4) Usa 'Apri Directory Output' e 'Analizza Similarità' per le fasi successive.\n",
    )
    report_text.see("end")

    # All'avvio: sincronizza lo stato attuale
    refresh_current_directory_state()

    return frame_correzione
