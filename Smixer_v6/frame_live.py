import os
import tkinter as tk
from tkinter import filedialog, ttk

from utils import scan_remote_directory, copy_test_directories

SCAN_INTERVAL = 30000  # 30 secondi


def create_frame_live(root, global_config):
    """
    Frame modalità LIVE.

    Usa:
      - global_config["remote_directory"] : directory remota con le cartelle testXX
      - global_config["file_extension"]   : estensione dei file (es. .cpp)
      - global_config["verifica_name"]    : nome della verifica
    """
    frame = tk.Frame(root, bg="white")

    # === Directory Remota === #
    lbl_remote = tk.Label(frame, text="Directory remota:", bg="white")
    lbl_remote.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    entry_remote = tk.Entry(
        frame,
        width=80,
        textvariable=global_config["remote_directory"],  # legata alla config globale
    )
    entry_remote.grid(row=0, column=1, padx=5, pady=5, columnspan=3, sticky="ew")

    # (se ti va, qui si potrebbe in futuro aggiungere un pulsante "Scegli…")

    # === Estensione === #
    lbl_ext = tk.Label(frame, text="Estensione file (es: .cpp):", bg="white")
    lbl_ext.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    entry_ext = tk.Entry(
        frame,
        width=20,
        textvariable=global_config["file_extension"],  # usa la stessa estensione globale
    )
    entry_ext.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    # === Pulsanti controllo === #
    btn_scan = tk.Button(frame, text="Scan", width=15)
    btn_scan.grid(row=0, column=4, padx=5, pady=5)

    btn_clear = tk.Button(frame, text="Pulisci tabella", width=15)
    btn_clear.grid(row=1, column=4, padx=5, pady=5)

    # === Tabella risultati === #
    tree = ttk.Treeview(
        frame,
        columns=("cartella", "num_file", "elenco_file", "ultima_modifica"),
        show="headings",
    )
    tree.heading("cartella", text="Cartella")
    tree.heading("num_file", text="N. File")
    tree.heading("elenco_file", text="File trovati")
    tree.heading("ultima_modifica", text="Ultima modifica")

    tree.column("cartella", width=150)
    tree.column("num_file", width=60, anchor="center")
    tree.column("elenco_file", width=500)
    tree.column("ultima_modifica", width=140)

    tree.grid(row=2, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(3, weight=1)

    # === Nome verifica === #
    lbl_nome_verifica = tk.Label(frame, text="Nome verifica:", bg="white")
    lbl_nome_verifica.grid(row=3, column=0, sticky="w", padx=5, pady=5)

    entry_verifica = tk.Entry(
        frame,
        width=30,
        textvariable=global_config["verifica_name"],  # condiviso con la barra in alto
    )
    entry_verifica.grid(row=3, column=1, padx=5, pady=5, sticky="w")

    # === Pulsante crea copia locale === #
    lbl_esito = tk.Label(frame, text="", fg="green", bg="white")
    lbl_esito.grid(row=3, column=3, columnspan=2, sticky="w", padx=5, pady=5)

    def crea_copia():
        """
        Crea una copia locale delle sole cartelle test01..test30
        dalla directory remota alla destinazione scelta.
        """
        nome_verifica = global_config["verifica_name"].get().strip()
        directory_remota = global_config["remote_directory"].get().strip()

        if not nome_verifica or not directory_remota:
            lbl_esito.config(text="⚠️ Inserisci directory remota e nome verifica.")
            return

        destinazione = filedialog.askdirectory(title="Seleziona destinazione")
        if destinazione:
            esito = copy_test_directories(directory_remota, destinazione, nome_verifica)
            lbl_esito.config(text=esito)

    btn_copy = tk.Button(frame, text="Crea copia locale", command=crea_copia)
    btn_copy.grid(row=3, column=2, padx=5, pady=5)

    # === Funzione di aggiornamento periodico === #
    def aggiorna_tabella():
        """
        Aggiorna la tabella leggendo la directory remota e l'estensione
        da global_config e mostrando SOLO le cartelle test01..test30.
        """
        path = global_config["remote_directory"].get().strip()
        estensione = global_config["file_extension"].get().strip()

        if not path or not os.path.isdir(path):
            # se la directory non è valida, non schedula niente di nuovo
            return

        # Pulisce la tabella
        for i in tree.get_children():
            tree.delete(i)

        risultati = scan_remote_directory(path, estensione)

        for nome_dir, num_file, files, ultima_mod in risultati:
            tree.insert(
                "",
                "end",
                values=(nome_dir, num_file, ", ".join(files), ultima_mod),
            )

        # Riprogramma il prossimo aggiornamento
        frame.after(SCAN_INTERVAL, aggiorna_tabella)

    # Collega i pulsanti
    btn_scan.config(command=aggiorna_tabella)
    btn_clear.config(command=lambda: tree.delete(*tree.get_children()))

    # Avvia scansione automatica (se la directory è già impostata)
    frame.after(SCAN_INTERVAL, aggiorna_tabella)

    return frame
