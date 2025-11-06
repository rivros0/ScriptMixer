# frame_correzione.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Scrollbar
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import utils
import business_logic
import similarity
import data_handler

YELLOW_REPORT_BG = "#fdfdfd"


def create_frame_correzione(root, global_config):
    """
    Modalità 'Correzione'.

    Usa:
      - global_config["file_extension"]
      - global_config["selected_directory"]
    """
    frame_correzione = tk.Frame(root, bg="white")

    include_prompt_var = tk.BooleanVar(value=True)
    include_subdir_var = tk.BooleanVar(value=True)

    # INTRO / PROMPT
    lbl_prompt = tk.Label(frame_correzione, text="INTRO:", bg="white")
    lbl_prompt.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    entry_prompt = tk.Text(frame_correzione, width=80, height=3)
    entry_prompt.grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

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

    # ESTENSIONE
    lbl_extension = tk.Label(frame_correzione, text="Estensione dei file:", bg="white")
    lbl_extension.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    entry_extension = tk.Entry(
        frame_correzione,
        textvariable=global_config["file_extension"],
        width=15,
    )
    entry_extension.grid(row=2, column=1, sticky="w", padx=10, pady=5)

    # LABEL DIRECTORY (locale alla scheda, ma collegata a selected_directory)
    lbl_directory = tk.Label(
        frame_correzione,
        text="Directory selezionata: (nessuna)",
        anchor="w",
        bg="white",
    )
    lbl_directory.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    # LOG / REPORT (lo dichiaro qui così lo vediamo nella callback)
    lbl_report = tk.Label(frame_correzione, text="Log / Report:", bg="white")
    lbl_report.grid(row=6, column=0, sticky="nw", padx=10, pady=5)

    report_text = tk.Text(frame_correzione, width=100, height=10, bg=YELLOW_REPORT_BG)
    report_text.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

    scrollbar = Scrollbar(frame_correzione, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=7, column=3, sticky="ns", pady=5)
    report_text.config(yscrollcommand=scrollbar.set)

    frame_correzione.rowconfigure(7, weight=1)

    # TREEVIEW
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

    frame_correzione.columnconfigure(2, weight=1)
    frame_correzione.rowconfigure(4, weight=1)

    # CALLBACK CENTRALIZZATA QUANDO CAMBIA selected_directory
    def on_selected_directory_change(*_args):
        """
        Quando cambiamo la directory dall'header (o da questa scheda):
          - aggiorna la label locale
          - se la directory esiste, ricarica log + tabella
        """
        path = global_config["selected_directory"].get().strip()

        if not path or path.lower() == "nessuna":
            lbl_directory.config(text="Directory selezionata: (nessuna)")
            report_text.delete("1.0", "end")
            tree.delete(*tree.get_children())
            report_text.insert(
                "end",
                "Nessuna directory selezionata.\n"
                "Seleziona la directory dall'header oppure dal bottone 'Scegli Directory'.\n",
            )
            report_text.see("end")
            return

        lbl_directory.config(text=f"Directory selezionata: {path}")

        if not os.path.isdir(path):
            report_text.delete("1.0", "end")
            tree.delete(*tree.get_children())
            report_text.insert(
                "end",
                f"La directory selezionata non esiste:\n{path}\n",
            )
            report_text.see("end")
            return

        # Aggiorna log con lista file
        utils.update_directory_listing(path, entry_extension, report_text)
        # Aggiorna tabella subdirectory
        utils.update_subdirectories_list(path, tree, entry_extension)

    # TRACE sulla variabile globale selected_directory
    sel_dir_var = global_config.get("selected_directory")
    if sel_dir_var is not None:
        if hasattr(sel_dir_var, "trace_add"):
            sel_dir_var.trace_add("write", on_selected_directory_change)
        elif hasattr(sel_dir_var, "trace"):
            sel_dir_var.trace("w", on_selected_directory_change)

    # BOTTONE SCEGLI DIRECTORY (locale, ma aggiorna la globale)
    def choose_directory():
        selected_directory = filedialog.askdirectory(
            title="Seleziona directory di lavoro (contenente le cartelle testXX)"
        )
        if selected_directory:
            global_config["selected_directory"].set(selected_directory)
            # la callback on_selected_directory_change si occuperà del resto

    btn_choose_directory = tk.Button(
        frame_correzione,
        text="Scegli Directory",
        command=choose_directory,
    )
    btn_choose_directory.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

    # BOTTONE MIX
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

    # BOTTONI EXPORT / ANALISI
    def apri_directory_output():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or base_dir.lower() == "nessuna":
            messagebox.showwarning(
                "Attenzione", "Seleziona prima una directory di lavoro."
            )
            return
        output_dir = os.path.join(base_dir, "00_MixOutput")
        data_handler.open_selected_directory(output_dir)

    btn_merge_files = tk.Button(
        frame_correzione,
        text="MEGAmerge",
        command=lambda: business_logic.merge_all_files(
            global_config["selected_directory"].get(), report_text
        ),
    )
    btn_merge_files.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

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

    # MESSAGGIO INIZIALE
    report_text.insert(
        "end",
        "Modalità Correzione pronta.\n"
        "1) Seleziona la directory dall'header (clic su 'nessuna') oppure da 'Scegli Directory'.\n"
        "2) Imposta l'estensione (es. .cpp) e l'intro.\n"
        "3) Premi 'Mixa' per generare i file *_mix.txt in 00_MixOutput.\n"
        "4) Usa 'MEGAmerge' / 'Analizza Similarità' per esportare e analizzare.\n",
    )
    report_text.see("end")

    # All'avvio: sincronizza lo stato attuale della selected_directory
    on_selected_directory_change()

    return frame_correzione
