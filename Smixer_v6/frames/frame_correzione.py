import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Scrollbar

# Import logica esistente
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import business_logic
import data_handler
import similarity
import utils

def create_frame_correzione(root):
    frame_correzione = tk.Frame(root, bg="white")

    # Variabili globali locali
    include_prompt_var = tk.BooleanVar(value=True)
    include_subdir_var = tk.BooleanVar(value=True)

    # Directory remota
    lbl_remote_directory = tk.Label(frame_correzione, text="Directory remota:")
    lbl_remote_directory.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    entry_remote_directory = tk.Entry(frame_correzione, width=50)
    entry_remote_directory.insert(0, "Y:\\")
    entry_remote_directory.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

    # Bottoni gestione cartelle
    btn_scan = tk.Button(frame_correzione, text="Scan", command=lambda: utils.scan_test_folders(entry_remote_directory, report_text))
    btn_scan.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

    btn_copy = tk.Button(frame_correzione, text="Crea Copia Locale", command=lambda: utils.create_local_copy(entry_remote_directory, report_text, lbl_directory, tree))
    btn_copy.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

    btn_clear = tk.Button(frame_correzione, text="Pulisci Test Remoti", command=lambda: utils.clear_test_folders(entry_remote_directory, report_text))
    btn_clear.grid(row=1, column=2, sticky="ew", padx=5, pady=5)

    # Prompt
    lbl_prompt = tk.Label(frame_correzione, text="INTRO:")
    lbl_prompt.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    entry_prompt = tk.Text(frame_correzione, width=80, height=2)
    entry_prompt.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    chk_include_prompt = tk.Checkbutton(frame_correzione, text="Includi Intro", variable=include_prompt_var)
    chk_include_prompt.grid(row=3, column=1, sticky="w", padx=10, pady=5)

    chk_include_subdir = tk.Checkbutton(frame_correzione, text="Includi Nome", variable=include_subdir_var)
    chk_include_subdir.grid(row=3, column=2, sticky="w", padx=10, pady=5)

    # Bottone Mix accanto alle checkbox
    btn_mix = tk.Button(frame_correzione, text="Mixa", command=lambda: business_logic.mix_files(lbl_directory, entry_prompt, entry_extension, tree, report_text, include_prompt_var.get(), include_subdir_var.get()))
    btn_mix.grid(row=3, column=0, sticky="ew", padx=5, pady=5)

    # Estensione file
    lbl_extension = tk.Label(frame_correzione, text="Estensione dei file:")
    lbl_extension.grid(row=4, column=0, sticky="w", padx=10, pady=5)

    entry_extension = tk.Entry(frame_correzione)
    entry_extension.grid(row=4, column=1, sticky="ew", padx=10, pady=5)

    # Selezione directory
    btn_choose_directory = tk.Button(frame_correzione, text="Scegli Directory", command=lambda: utils.choose_directory(lbl_directory, tree, entry_extension, report_text))
    btn_choose_directory.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

    lbl_directory = tk.Label(frame_correzione, text="Directory non selezionata", anchor="w")
    lbl_directory.grid(row=5, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    # Treeview
    tree = ttk.Treeview(frame_correzione, columns=("subdirectory", "num_folders", "num_files", "num_extension_files", "extension_files"), show="headings")
    tree.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

    frame_correzione.columnconfigure(2, weight=1)
    frame_correzione.rowconfigure(6, weight=1)

    tree.heading("subdirectory", text="Subdirectory")
    tree.heading("num_folders", text="Cartelle")
    tree.heading("num_files", text="File")
    tree.heading("num_extension_files", text="File con Estensione")
    tree.heading("extension_files", text="Elenco File Estensione")

    # Bottoni principali
    btn_merge_files = tk.Button(frame_correzione, text="MEGAmerge", command=lambda: business_logic.merge_all_files(lbl_directory, report_text))
    btn_merge_files.grid(row=7, column=0, sticky="ew", padx=10, pady=5)

    btn_open_directory = tk.Button(frame_correzione, text="Apri Directory Output", command=lambda: utils.open_selected_directory(lbl_directory))
    btn_open_directory.grid(row=7, column=1, sticky="ew", padx=10, pady=5)

    btn_analyze = tk.Button(frame_correzione, text="Analizza Similarità", command=lambda: similarity.analyze_similarities(lbl_directory, report_text))
    btn_analyze.grid(row=7, column=2, sticky="ew", padx=10, pady=5)

    # Report
    lbl_report = tk.Label(frame_correzione, text="Report:")
    lbl_report.grid(row=9, column=0, sticky="nw", padx=10, pady=5)

    report_text = tk.Text(frame_correzione, width=1024, height=12)
    report_text.grid(row=10, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

    scrollbar = Scrollbar(frame_correzione, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=10, column=3, sticky="ns", pady=5)
    report_text.config(yscrollcommand=scrollbar.set)

    return frame_correzione
