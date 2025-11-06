# frame_correzione.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Scrollbar
import os
import sys

# Aggiunge la root del progetto al path per importare i moduli principali
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import utils
import business_logic
import similarity
import data_handler


YELLOW_REPORT_BG = "#fdfdfd"  # leggero bianco sporco per il report (se vuoi puoi cambiarlo)


def create_frame_correzione(root, global_config):
    """
    Crea il frame della modalità 'Correzione'.

    Usa:
      - global_config["file_extension"]     : estensione dei file (.cpp, .java, ...)
      - global_config["selected_directory"]: directory di lavoro corrente
    """
    frame_correzione = tk.Frame(root, bg="white")

    # =========================================================================
    #  VARIABILI LOCALI
    # =========================================================================
    include_prompt_var = tk.BooleanVar(value=True)
    include_subdir_var = tk.BooleanVar(value=True)

    # =========================================================================
    #  INTRO / PROMPT
    # =========================================================================
    lbl_prompt = tk.Label(frame_correzione, text="INTRO:", bg="white")
    lbl_prompt.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    entry_prompt = tk.Text(frame_correzione, width=80, height=3)
    entry_prompt.grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    # Checkbox e bottone MIX
    chk_include_prompt = tk.Checkbutton(
        frame_correzione,
        text="Includi Intro",
        variable=include_prompt_var,
        bg="white",
    )
    chk_include_prompt.grid(row=1, column=1, sticky="w", padx=10, pady=2)

    chk_include_subdir = tk.Checkbutton(
        frame_correzione,
        text="Includi Nome (subdir)",
        variable=include_subdir_var,
        bg="white",
    )
    chk_include_subdir.grid(row=1, column=2, sticky="w", padx=10, pady=2)

    # =========================================================================
    #  ESTENSIONE FILE
    # =========================================================================
    lbl_extension = tk.Label(frame_correzione, text="Estensione dei file:", bg="white")
    lbl_extension.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    entry_extension = tk.Entry(
        frame_correzione,
        textvariable=global_config["file_extension"],  # legato alla config globale
        width=15,
    )
    entry_extension.grid(row=2, column=1, sticky="w", padx=10, pady=5)

    # =========================================================================
    #  SELEZIONE DIRECTORY DI LAVORO (LOCALE PER LA CORREZIONE)
    # =========================================================================
    lbl_directory = tk.Label(
        frame_correzione,
        text="Directory selezionata: (nessuna)",
        anchor="w",
        bg="white",
    )
    lbl_directory.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    def aggiorna_percorso_selezionato(path: str):
        """
        Aggiorna:
          - l'etichetta locale della scheda Correzione
          - la directory selezionata globale, usata nella barra superiore
        """
        path = path.strip()
        global_config["selected_directory"].set(path)
        lbl_directory.config(text=f"Directory selezionata: {path}")

    def choose_directory():
        """
        Dialogo di scelta directory specifico per la scheda Correzione.
        Aggiorna:
          - label della scheda
          - global_config["selected_directory"]
          - lista file (report) e tabella subdirectory
        """
        selected_directory = filedialog.askdirectory(
            title="Seleziona directory di lavoro (contenente le cartelle testXX)"
        )
        if selected_directory:
            aggiorna_percorso_selezionato(selected_directory)
            # aggiorna elenco file nel report
            utils.update_directory_listing(
                selected_directory,
                entry_extension,
                report_text,
            )
            # aggiorna tabella subdirectory
            utils.update_subdirectories_list(
                selected_directory,
                tree,
                entry_extension,
            )

    btn_choose_directory = tk.Button(
        frame_correzione,
        text="Scegli Directory",
        command=choose_directory,
    )
    btn_choose_directory.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

    # Ora che lbl_directory esiste, possiamo creare il bottone MIX
    btn_mix = tk.Button(
        frame_correzione,
        text="Mixa",
        command=lambda: business_logic.mix_files(
            lbl_directory,
            entry_prompt,
            entry_extension,
            tree,
            report_text,
            include_prompt_var.get(),
            include_subdir_var.get(),
        ),
    )
    btn_mix.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

    # =========================================================================
    #  TABELLA (TREEVIEW) CON LE SOTTOCARTELLE
    # =========================================================================
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
    tree.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

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

    # Rende la tabella espandibile
    frame_correzione.columnconfigure(2, weight=1)
    frame_correzione.rowconfigure(4, weight=1)

    # =========================================================================
    #  BOTTONI PRINCIPALI (EXPORT / ANALISI)
    # =========================================================================
    def apri_directory_output():
        """
        Apre la directory 00_MixOutput sotto la directory selezionata attuale.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir:
            messagebox.showwarning(
                "Attenzione", "Seleziona prima una directory di lavoro."
            )
            return
        output_dir = os.path.join(base_dir, "00_MixOutput")
        data_handler.open_selected_directory(output_dir)

    
    btn_open_directory = tk.Button(
        frame_correzione,
        text="Apri Directory Output",
        command=apri_directory_output,
    )
    btn_open_directory.grid(row=5, column=1, sticky="ew", padx=10, pady=5)

    btn_analyze = tk.Button(
        frame_correzione,
        text="Analizza Similarità",
        command=lambda: similarity.analyze_similarities(lbl_directory, report_text),
    )
    btn_analyze.grid(row=5, column=2, sticky="ew", padx=10, pady=5)

    # =========================================================================
    #  REPORT / LOG EVENTI
    # =========================================================================
    lbl_report = tk.Label(frame_correzione, text="Log / Report:", bg="white")
    lbl_report.grid(row=6, column=0, sticky="nw", padx=10, pady=5)

    report_text = tk.Text(frame_correzione, width=100, height=10, bg=YELLOW_REPORT_BG)
    report_text.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

    scrollbar = Scrollbar(frame_correzione, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=7, column=3, sticky="ns", pady=5)
    report_text.config(yscrollcommand=scrollbar.set)

    frame_correzione.rowconfigure(7, weight=1)

    # Messaggio iniziale nel log
    report_text.insert(
        "end",
        "Modalità Correzione pronta.\n"
        "1) Scegli la directory contenente le cartelle test01..test30.\n"
        "2) Imposta l'estensione (es. .cpp) e l'intro.\n"
        "3) Premi 'Mixa' per generare i file *_mix.txt in 00_MixOutput.\n"
        "4) Usa 'MEGAmerge' / 'Analizza Similarità' per esportare e analizzare.\n",
    )
    report_text.see("end")

    # Se esiste già una directory selezionata in global_config, la riflettiamo nell'etichetta
    initial_dir = global_config["selected_directory"].get().strip()
    if initial_dir:
        lbl_directory.config(text=f"Directory selezionata: {initial_dir}")

    return frame_correzione
