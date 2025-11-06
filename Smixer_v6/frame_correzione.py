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

    # ESTENSIONI
    lbl_extension = tk.Label(
        frame_correzione,
        text="Estensioni dei file (es: .php,.html,.css):",
        bg="white",
    )
    lbl_extension.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    entry_extension = tk.Entry(
        frame_correzione,
        textvariable=global_config["file_extension"],
        width=25,
    )
    entry_extension.grid(row=2, column=1, sticky="w", padx=10, pady=5)

    # LABEL DIRECTORY LOCALE
    lbl_directory = tk.Label(
        frame_correzione,
        text="Directory selezionata: (nessuna)",
        anchor="w",
        bg="white",
    )
    lbl_directory.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

    # LOG / REPORT
    lbl_report = tk.Label(frame_correzione, text="Log / Report:", bg="white")
    lbl_report.grid(row=6, column=0, sticky="nw", padx=10, pady=5)

    report_text = tk.Text(frame_correzione, width=100, height=10, bg=YELLOW_REPORT_BG)
    report_text.grid(row=7, column=0, columnspan=4, sticky="nsew", padx=10, pady=5)

    scrollbar = Scrollbar(frame_correzione, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=7, column=4, sticky="ns", pady=5)
    report_text.config(yscrollcommand=scrollbar.set)

    frame_correzione.rowconfigure(7, weight=1)

    # TREEVIEW (con colonna Mix file)
    tree = ttk.Treeview(
        frame_correzione,
        columns=(
            "subdirectory",
            "num_folders",
            "num_files",
            "num_extension_files",
            "extension_files",
            "mix_file",
        ),
        show="headings",
    )
    tree.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

    tree.heading("subdirectory", text="Subdirectory")
    tree.heading("num_folders", text="Cartelle")
    tree.heading("num_files", text="File")
    tree.heading("num_extension_files", text="File con estensione")
    tree.heading("extension_files", text="Elenco file estensione")
    tree.heading("mix_file", text="Mix file (clic per copiare)")

    tree.column("subdirectory", width=100, anchor="w")
    tree.column("num_folders", width=80, anchor="center")
    tree.column("num_files", width=80, anchor="center")
    tree.column("num_extension_files", width=140, anchor="center")
    tree.column("extension_files", width=350, anchor="w")
    tree.column("mix_file", width=220, anchor="w")

    frame_correzione.columnconfigure(2, weight=1)
    frame_correzione.rowconfigure(4, weight=1)

    # CLICK SULLA COLONNA MIX_FILE -> COPIA IN CLIPBOARD
    def on_tree_click(event):
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        item_id = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)  # "#1", "#2", ...

        if not item_id:
            return

        # Trova indice della colonna "mix_file"
        columns = tree["columns"]
        try:
            mix_index = columns.index("mix_file")  # 0-based
        except ValueError:
            return

        # col_id è "#1" per la prima, "#2" per la seconda, ...
        if col_id != f"#{mix_index + 1}":
            return

        mix_path = tree.set(item_id, "mix_file")
        if not mix_path:
            messagebox.showinfo(
                "Info",
                "Per questa subdirectory non è ancora stato creato alcun mix.",
            )
            return

        if not os.path.exists(mix_path):
            messagebox.showwarning(
                "Attenzione",
                f"Il file di mix non esiste più:\n{mix_path}",
            )
            return

        try:
            with open(mix_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(mix_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        # copia in clipboard
        root_widget = frame_correzione.winfo_toplevel()
        root_widget.clipboard_clear()
        root_widget.clipboard_append(content)

        messagebox.showinfo(
            "Copiato",
            f"Contenuto di\n{os.path.basename(mix_path)}\n"
            "copiato negli appunti.",
        )

    tree.bind("<Button-1>", on_tree_click)

    # CALLBACK QUANDO CAMBIA selected_directory
    def on_selected_directory_change(*_args):
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

        utils.update_directory_listing(path, entry_extension, report_text)
        utils.update_subdirectories_list(path, tree, entry_extension)

    sel_dir_var = global_config.get("selected_directory")
    if sel_dir_var is not None:
        if hasattr(sel_dir_var, "trace_add"):
            sel_dir_var.trace_add("write", on_selected_directory_change)
        elif hasattr(sel_dir_var, "trace"):
            sel_dir_var.trace("w", on_selected_directory_change)

    # BOTTONE SCEGLI DIRECTORY
    def choose_directory():
        selected_directory = filedialog.askdirectory(
            title="Seleziona directory di lavoro (contenente le cartelle testXX)"
        )
        if selected_directory:
            global_config["selected_directory"].set(selected_directory)

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

    # BOTTONI VARI
    def apri_directory_output():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or base_dir.lower() == "nessuna":
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
    btn_open_directory.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

    btn_analyze = tk.Button(
        frame_correzione,
        text="Analizza Similarità",
        command=lambda: similarity.analyze_similarities(lbl_directory, report_text),
    )
    btn_analyze.grid(row=5, column=1, sticky="ew", padx=10, pady=5)

    # MESSAGGIO INIZIALE
    report_text.insert(
        "end",
        "Modalità Correzione pronta.\n"
        "1) Seleziona la directory dall'header (clic su 'nessuna') oppure da 'Scegli Directory'.\n"
        "2) Imposta le estensioni (es. .php,.html,.css) e l'intro.\n"
        "3) Premi 'Mixa' per generare i file *_mix.txt in 00_MixOutput.\n"
        "   → la colonna 'Mix file' mostrerà il percorso del file di mix.\n"
        "   → cliccando su una cella di quella colonna, il contenuto verrà copiato negli appunti.\n"
        "4) Usa Export / 'Analizza Similarità' per esportare e analizzare.\n",
    )
    report_text.see("end")

    on_selected_directory_change()

    return frame_correzione
