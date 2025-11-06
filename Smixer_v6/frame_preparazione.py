import os
import shutil

import tkinter as tk
from tkinter import filedialog, messagebox, Scrollbar

import data_handler

YELLOW_BG = "#fff5cc"


def create_frame_preparazione(root, global_config):
    """
    Frame modalità PREPARAZIONE.

    Serve per:
      - scegliere la directory remota che contiene le cartelle test01..test30
      - scansionare lo stato delle cartelle test
      - creare una copia locale (su Desktop, in una cartella timestampata)
      - distribuire un file in tutte le cartelle test
      - opzionalmente cancellare le cartelle test sulla directory remota

    Usa:
      - global_config["remote_directory"]     : directory remota (server)
      - global_config["selected_directory"]   : ultima directory locale creata
      - report_text                           : log degli eventi
    """
    frame = tk.Frame(root, bg=YELLOW_BG)

    # ======================================================================
    #  RIGA 0: DIRECTORY REMOTA
    # ======================================================================
    lbl_remote = tk.Label(
        frame,
        text="Directory remota (contiene test01..test30):",
        bg=YELLOW_BG,
    )
    lbl_remote.grid(row=0, column=0, sticky="w", padx=8, pady=8)

    entry_remote = tk.Entry(
        frame,
        width=80,
        textvariable=global_config["remote_directory"],
    )
    entry_remote.grid(row=0, column=1, columnspan=3, sticky="ew", padx=8, pady=8)

    def choose_remote_dir():
        d = filedialog.askdirectory(
            title="Seleziona directory remota (contenente le cartelle test01..test30)"
        )
        if d:
            global_config["remote_directory"].set(d)

    btn_choose_remote = tk.Button(
        frame,
        text="Scegli…",
        command=choose_remote_dir,
        bg="white",
    )
    btn_choose_remote.grid(row=0, column=4, padx=8, pady=8, sticky="ew")

    # ======================================================================
    #  RIGA 1: PULSANTI OPERATIVI
    # ======================================================================
    def do_scan_tests():
        """
        Scansiona le cartelle test01..test30 sulla directory remota
        e scrive il risultato nel log.
        """
        remote_dir = global_config["remote_directory"].get().strip()
        if not remote_dir:
            messagebox.showwarning(
                "Attenzione",
                "Imposta prima la directory remota (contente le cartelle testXX).",
            )
            return
        data_handler.scan_test_folders(remote_dir, report_text)

    btn_scan = tk.Button(
        frame,
        text="Scansiona cartelle test",
        command=do_scan_tests,
        bg="white",
    )
    btn_scan.grid(row=1, column=0, padx=8, pady=4, sticky="ew")

    # Label per mostrare l'ultima directory locale creata
    lbl_local_dir = tk.Label(
        frame,
        text="Ultima directory locale creata: (nessuna)",
        anchor="w",
        bg=YELLOW_BG,
    )
    lbl_local_dir.grid(row=2, column=0, columnspan=5, sticky="ew", padx=8, pady=4)

    def do_create_local_copy():
        """
        Crea una copia locale di test01..test30 sul Desktop in una cartella
        timestampata, aggiorna il log e imposta:
          - global_config["selected_directory"]
          - lbl_local_dir
        """
        remote_dir = global_config["remote_directory"].get().strip()
        if not remote_dir:
            messagebox.showwarning(
                "Attenzione",
                "Imposta prima la directory remota (contente le cartelle testXX).",
            )
            return

        # Usiamo create_local_copy di data_handler.
        # I parametri update_* non servono in questo frame, quindi passiamo lambda.
        new_dir = data_handler.create_local_copy(
            remote_dir,
            report_text,
            lbl_local_dir,           # verrà impostato a "Directory selezionata: ..."
            lambda *_: None,         # update_directory_listing_func
            lambda *_: None,         # update_subdirectories_list_func
        )

        if new_dir:
            # Aggiorna la directory selezionata globale (usata da Correzione/Export)
            global_config["selected_directory"].set(new_dir)
            # Sovrascrive il testo della label in modo più descrittivo
            lbl_local_dir.config(
                text=f"Ultima directory locale creata: {new_dir}"
            )
            report_text.insert(
                "end",
                "Directory locale impostata per la correzione/export.\n",
            )
            report_text.see("end")

    btn_create_copy = tk.Button(
        frame,
        text="Crea copia locale (Desktop)",
        command=do_create_local_copy,
        bg="white",
    )
    btn_create_copy.grid(row=1, column=1, padx=8, pady=4, sticky="ew")

    def do_distribute_file():
        """
        Chiede un file e lo copia in tutte le cartelle test01..test30
        presenti nella directory remota.
        """
        remote_dir = global_config["remote_directory"].get().strip()
        if not remote_dir:
            messagebox.showwarning(
                "Attenzione",
                "Imposta prima la directory remota (contente le cartelle testXX).",
            )
            return

        file_path = filedialog.askopenfilename(
            title="Seleziona il file da distribuire nelle cartelle test"
        )
        if not file_path:
            return

        file_name = os.path.basename(file_path)
        copied_count = 0

        for folder_name, folder_path in data_handler._iter_test_folders(remote_dir):
            if os.path.isdir(folder_path):
                dest_path = os.path.join(folder_path, file_name)
                try:
                    shutil.copy2(file_path, dest_path)
                    copied_count += 1
                except Exception as e:
                    report_text.insert(
                        "end",
                        f"Errore nel copiare {file_name} in {folder_name}: {e}\n",
                    )

        if copied_count == 0:
            msg = (
                "Nessuna cartella test01–test30 trovata nella directory remota.\n"
                "File NON distribuito."
            )
        else:
            msg = (
                f"File '{file_name}' distribuito in {copied_count} cartelle test.\n"
            )

        report_text.insert("end", msg + "\n")
        report_text.see("end")

    btn_distribute = tk.Button(
        frame,
        text="Distribuisci file nelle cartelle test",
        command=do_distribute_file,
        bg="white",
    )
    btn_distribute.grid(row=1, column=2, padx=8, pady=4, sticky="ew")

    def do_clear_remote():
        """
        Cancella i contenuti delle cartelle test01..test30 sulla directory remota.
        Chiede tre conferme (gestite da data_handler.clear_test_folders).
        """
        remote_dir = global_config["remote_directory"].get().strip()
        if not remote_dir:
            messagebox.showwarning(
                "Attenzione",
                "Imposta prima la directory remota (contente le cartelle testXX).",
            )
            return

        data_handler.clear_test_folders(remote_dir, report_text)

    btn_clear_remote = tk.Button(
        frame,
        text="Cancella cartelle test remote",
        command=do_clear_remote,
        bg="red",
        fg="white",
        activebackground="#ff6666",
        activeforeground="white",
    )
    btn_clear_remote.grid(row=1, column=3, padx=8, pady=4, sticky="ew")

    def open_remote_dir():
        """
        Apre la directory remota nel file manager di sistema.
        """
        remote_dir = global_config["remote_directory"].get().strip()
        if not remote_dir:
            messagebox.showwarning(
                "Attenzione",
                "Imposta prima la directory remota.",
            )
            return
        data_handler.open_selected_directory(remote_dir)

    btn_open_remote = tk.Button(
        frame,
        text="Apri directory remota",
        command=open_remote_dir,
        bg="white",
    )
    btn_open_remote.grid(row=1, column=4, padx=8, pady=4, sticky="ew")

    # ======================================================================
    #  LOG / REPORT
    # ======================================================================
    lbl_report = tk.Label(frame, text="Log / Report:", bg=YELLOW_BG)
    lbl_report.grid(row=3, column=0, sticky="nw", padx=8, pady=4)

    report_text = tk.Text(
        frame,
        width=100,
        height=15,
        bg="#fffbe6",  # leggermente diverso per contrasto
    )
    report_text.grid(
        row=4,
        column=0,
        columnspan=5,
        sticky="nsew",
        padx=8,
        pady=4,
    )

    scrollbar = Scrollbar(frame, orient="vertical", command=report_text.yview)
    scrollbar.grid(row=4, column=5, sticky="ns", pady=4)
    report_text.config(yscrollcommand=scrollbar.set)

    # Rende il log espandibile
    frame.rowconfigure(4, weight=1)
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(2, weight=1)
    frame.columnconfigure(3, weight=1)

    # Messaggio iniziale nel log
    report_text.insert(
        "end",
        "Modalità Preparazione pronta.\n"
        "- Imposta la directory remota con le cartelle test01..test30.\n"
        "- Usa 'Scansiona cartelle test' per verificare la presenza dei file.\n"
        "- Usa 'Crea copia locale (Desktop)' per creare una copia delle cartelle test.\n"
        "- Usa 'Distribuisci file nelle cartelle test' per copiare un file in tutte le cartelle test.\n"
        "- Dopo la copia, la directory locale verrà impostata come directory di lavoro\n"
        "  per le schede Correzione ed Export.\n"
        "- Usa 'Cancella cartelle test remote' SOLO dopo aver verificato di avere la copia locale.\n",
    )
    report_text.see("end")

    # Se abbiamo già una directory remota in config, aggiornala nell'entry
    if global_config["remote_directory"].get().strip():
        entry_remote.icursor("end")

    # Se abbiamo già una directory selezionata (locale), riflettila nella label
    if global_config["selected_directory"].get().strip():
        lbl_local_dir.config(
            text=f"Ultima directory locale creata: {global_config['selected_directory'].get().strip()}"
        )

    return frame
