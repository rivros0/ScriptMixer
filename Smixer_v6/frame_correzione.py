import tkinter as tk
from tkinter import ttk, filedialog, Scrollbar, messagebox
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import utils
import business_logic
import similarity


def create_frame_correzione(root, global_config):
    frame_correzione = tk.Frame(root, bg="lightgreen")

    # Variabili di controllo
    include_prompt_var = tk.BooleanVar(value=True)
    include_subdir_var = tk.BooleanVar(value=True)

    # Prompt
    lbl_prompt = tk.Label(frame_correzione, text="INTRO:", bg="lightgreen")
    lbl_prompt.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    entry_prompt = tk.Text(frame_correzione, width=80, height=2)
    entry_prompt.grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    chk_include_prompt = tk.Checkbutton(
        frame_correzione, text="Includi Intro", variable=include_prompt_var, bg="lightgreen"
    )
    chk_include_prompt.grid(row=1, column=1, sticky="w", padx=10, pady=5)

    chk_include_subdir = tk.Checkbutton(
        frame_correzione, text="Includi Nome Subdir", variable=include_subdir_var, bg="lightgreen"
    )
    chk_include_subdir.grid(row=1, column=2, sticky="w", padx=10, pady=5)

    # Bottone Mix
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
    btn_mix.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

    # Estensione file
    lbl_extension = tk.Label(frame_correzione, text="Estensione dei file:", bg="lightgreen")
    lbl_extension.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    entry_extension = tk.Entry(frame_correzione, textvariable=global_config["file_extension"])
    entry_extension.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

    # Selezione directory
    lbl_directory = tk.Label(frame_correzione, text="Directory non selezionata", anchor="w", bg="lightgreen")
    lbl_directory.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    def scegli_directory():
        selected_directory = filedialog.askdirectory(title="Seleziona directory base")
        if selected_directory:
            lbl_directory.config(text=f"Directory selezionata: {selected_directory}")
            utils.update_directory_listing(selected_directory, entry_extension, report_text)
            utils.update_subdirectories_list(selected_directory, tree, entry_extension)

    btn_choose_directory = tk.Button(frame_correzione, text="Scegli Directory", command=scegli_directory)
    btn_choose_directory.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

    # Treeview
    tree = ttk.Treeview(
        frame_correzione,
        columns=("subdirectory", "num_folders", "num_files", "num_extension_files", "extension_files", "stato_mix"),
        show="headings",
    )
    tree.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

    frame_correzione.columnconfigure(2, weight=1)
    frame_correzione.rowconfigure(4, weight=1)

    tree.heading("subdirectory", text="Subdirectory")
    tree.heading("num_folders", text="Cartelle")
    tree.heading("num_files", text="File")
    tree.heading("num_extension_files", text="File con Estensione")
    tree.heading("extension_files", text="Elenco File Estensione")
    tree.heading("stato_mix", text="Mix")

    # Funzione copia in clipboard con doppio click
    def on_tree_double_click(event):
        selected_item = tree.selection()
        if not selected_item:
            return
        values = tree.item(selected_item[0], "values")
        if not values or len(values) < 6:
            return
        subdir, _, _, _, _, stato_mix = values
        if stato_mix == "CopiaInClipboard":
            base_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
            mix_file_path = os.path.join(base_directory, "00_MixOutput", f"{subdir}_mix.txt")
            if os.path.exists(mix_file_path):
                try:
                    with open(mix_file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    root.clipboard_clear()
                    root.clipboard_append(content)
                    messagebox.showinfo("Copia riuscita", f"Il contenuto di {subdir}_mix.txt è stato copiato negli appunti.")
                except Exception as e:
                    messagebox.showerror("Errore", f"Impossibile copiare in clipboard:\n{e}")

    tree.bind("<Double-1>", on_tree_double_click)

    # Bottoni principali
    btn_merge_files = tk.Button(
        frame_correzione,
        text="MEGAmerge",
        command=lambda: business_logic.merge_all_files(lbl_directory, report_text),
    )
    btn_merge_files.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

    btn_open_directory = tk.Button(
        frame_correzione,
        text="Apri Directory Output",
        command=lambda: utils.open_selected_directory(lbl_directory),
    )
    btn_open_directory.grid(row=5, column=1, sticky="ew", padx=10, pady=5)

    btn_analyze = tk.Button(
        frame_correzione,
        text="Analizza Similarità",
        command=lambda: similarity.analyze_similarities(lbl_directory, report_text),
    )
    btn_analyze.grid(row=5, column=2, sticky="ew", padx=10, pady=5)

    # Report
    lbl_report = tk.Label(frame_correzione, text="Report:", bg="lightgreen")
    lbl_report.grid(row=6, column=0, sticky="nw", padx=10, pady=5)

    report_text = tk.Text(frame_correzione, width=1024, height=12)
    report_text.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

    scrollbar = Scrollbar(frame_correzione, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=7, column=3, sticky="ns", pady=5)
    report_text.config(yscrollcommand=scrollbar.set)

    return frame_correzione
