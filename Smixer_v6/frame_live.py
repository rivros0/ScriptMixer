import os
import tkinter as tk
from tkinter import filedialog, ttk

from utils import scan_remote_directory, copy_test_directories

SCAN_INTERVAL = 30000  # 30 secondi


def create_frame_live(root, global_config):
    """
    Frame modalità LIVE.
    """
    frame = tk.Frame(root, bg="#046276")

    # === Directory Remota === #
    lbl_remote = tk.Label(frame, text="Directory remota:", bg="white")
    lbl_remote.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    entry_remote = tk.Entry(
        frame,
        width=80,
        textvariable=global_config["remote_directory"],
    )
    entry_remote.grid(row=0, column=1, padx=5, pady=5, columnspan=3, sticky="ew")

    # === Estensioni === #
    lbl_ext = tk.Label(frame, text="Estensioni (es: .php,.html,.css):", bg="white")
    lbl_ext.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    entry_ext = tk.Entry(
        frame,
        width=30,
        textvariable=global_config["file_extension"],
    )
    entry_ext.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    # === Checkbutton: Conta righe + Auto refresh === #
    count_lines_var = tk.BooleanVar(value=False)
    auto_refresh_var = tk.BooleanVar(value=True)

    chk_count_lines = tk.Checkbutton(
        frame,
        text="Conta righe",
        variable=count_lines_var,
        bg="white",
    )
    chk_count_lines.grid(row=1, column=2, padx=5, pady=5, sticky="w")

    chk_auto_refresh = tk.Checkbutton(
        frame,
        text="Aggiornamento automatico",
        variable=auto_refresh_var,
        bg="white",
    )
    chk_auto_refresh.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    # === Pulsanti controllo === #
    btn_scan = tk.Button(frame, text="Scan", width=15)
    btn_scan.grid(row=0, column=4, padx=5, pady=5)

    btn_clear = tk.Button(frame, text="Pulisci tabella", width=15)
    btn_clear.grid(row=1, column=4, padx=5, pady=5)

    # === Tabella risultati === #
    tree = ttk.Treeview(
        frame,
        columns=(
            "cartella",
            "num_file",
            "num_righe",
            "elenco_file",
            "ultima_modifica",
            "tempo_trascorso",
        ),
        show="headings",
    )
    tree.heading("cartella", text="Cartella")
    tree.heading("num_file", text="N. File")
    tree.heading("num_righe", text="Righe")
    tree.heading("elenco_file", text="File trovati")
    tree.heading("ultima_modifica", text="Ultima modifica")
    tree.heading("tempo_trascorso", text="Tempo trascorso")

    tree.column("cartella", width=100)
    tree.column("num_file", width=60, anchor="center")
    tree.column("num_righe", width=80, anchor="center")
    tree.column("elenco_file", width=420)
    tree.column("ultima_modifica", width=140)
    tree.column("tempo_trascorso", width=110, anchor="center")

    tree.grid(row=2, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(3, weight=1)
    '''
    # === Nome verifica === #
    lbl_nome_verifica = tk.Label(frame, text="Nome verifica:", bg="white")
    lbl_nome_verifica.grid(row=3, column=0, sticky="w", padx=5, pady=5)

    entry_verifica = tk.Entry(
        frame,
        width=30,
        textvariable=global_config["verifica_name"],
    )
    entry_verifica.grid(row=3, column=1, padx=5, pady=5, sticky="w")
    '''
    # === Pulsante crea copia locale === #
    

    lbl_esito = tk.Label(frame, text="", fg="green", bg="white")
    lbl_esito.grid(row=3, column=1, columnspan=4, sticky="w", padx=5, pady=5)

    def crea_copia():
        nome_verifica = global_config["verifica_name"].get().strip()
        directory_remota = global_config["remote_directory"].get().strip()

        if not nome_verifica or not directory_remota:
            lbl_esito.config(text="⚠️ Inserisci directory remota e nome verifica.")
            return

        destinazione = filedialog.askdirectory(title="Seleziona destinazione")
        if destinazione:
            esito = copy_test_directories(directory_remota, destinazione, nome_verifica)
            lbl_esito.config(text=esito)

    btn_copy = tk.Button(frame, text="Crea copia locale", command=crea_copia, bg='lime', font=( 'bold') )
    btn_copy.grid(row=3, column=0, padx=5, pady=5 )
   

    # === Aggiornamento periodico "a goccia" === #
    auto_job_id = None

    def aggiorna_tabella():
        """
        Aggiorna la tabella leggendo la directory remota e l'estensione/i.
        """
        nonlocal auto_job_id

        path = global_config["remote_directory"].get().strip()
        estensioni = global_config["file_extension"].get().strip()

        for i in tree.get_children():
            tree.delete(i)

        if not path or not os.path.isdir(path):
            auto_job_id = None
            return

        risultati = scan_remote_directory(
            path,
            estensioni,
            count_lines=count_lines_var.get(),
        )

        for nome_dir, num_file, num_righe, files, ultima_mod, age_str in risultati:
            righe_display = num_righe if num_righe is not None else "-"
            tree.insert(
                "",
                "end",
                values=(
                    nome_dir,
                    num_file,
                    righe_display,
                    ", ".join(files),
                    ultima_mod,
                    age_str,
                ),
            )

        if auto_refresh_var.get():
            if auto_job_id is not None:
                try:
                    frame.after_cancel(auto_job_id)
                except Exception:
                    pass
            auto_job_id = frame.after(SCAN_INTERVAL, aggiorna_tabella)
        else:
            auto_job_id = None

    def on_toggle_auto():
        nonlocal auto_job_id

        if auto_refresh_var.get():
            aggiorna_tabella()
        else:
            if auto_job_id is not None:
                try:
                    frame.after_cancel(auto_job_id)
                except Exception:
                    pass
                auto_job_id = None

    chk_auto_refresh.config(command=on_toggle_auto)

    btn_scan.config(command=aggiorna_tabella)
    btn_clear.config(command=lambda: tree.delete(*tree.get_children()))

    if auto_refresh_var.get():
        auto_job_id = frame.after(SCAN_INTERVAL, aggiorna_tabella)

    return frame
