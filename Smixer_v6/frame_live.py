import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import utils
import datetime

SCAN_INTERVAL = 30  # secondi


def create_frame_live(root, global_config):
    frame = tk.Frame(root, bg="lightblue")  # sfondo azzurro

    # === Directory Remota === #
    lbl_remote = tk.Label(frame, text="Directory remota:", bg="lightblue")
    lbl_remote.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    entry_remote = tk.Entry(frame, width=80, textvariable=global_config["remote_directory"])
    entry_remote.grid(row=0, column=1, padx=5, pady=5, columnspan=3)

    def scegli_directory():
        directory = filedialog.askdirectory(title="Seleziona directory remota")
        if directory:
            global_config["remote_directory"].set(directory)

    btn_choose_dir = tk.Button(frame, text="Scegli...", command=scegli_directory)
    btn_choose_dir.grid(row=0, column=4, padx=5, pady=5)

    # === Estensione === #
    lbl_ext = tk.Label(frame, text="Estensione file (es: .cpp):", bg="lightblue")
    lbl_ext.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    entry_ext = tk.Entry(frame, width=20, textvariable=global_config["file_extension"])
    entry_ext.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    # === Pulsanti controllo + Timer === #
    btn_scan = tk.Button(frame, text="Scan", width=15)
    btn_scan.grid(row=1, column=4, padx=5)

    lbl_timer = tk.Label(frame, text=f"Prossima scansione tra {SCAN_INTERVAL}s", fg="blue", bg="lightblue")
    lbl_timer.grid(row=1, column=5, padx=10, sticky="w")

    btn_clear = tk.Button(frame, text="Pulisci tabella", width=15, command=lambda: tree.delete(*tree.get_children()))
    btn_clear.grid(row=1, column=3, padx=5)

    # === Tabella risultati === #
    tree = ttk.Treeview(
        frame,
        columns=("cartella", "num_file", "elenco_file", "ultima_modifica", "tempo_trascorso"),
        show="headings"
    )
    tree.heading("cartella", text="Cartella")
    tree.heading("num_file", text="N. File")
    tree.heading("elenco_file", text="File trovati")
    tree.heading("ultima_modifica", text="Ultima modifica")
    tree.heading("tempo_trascorso", text="Tempo trascorso")

    tree.column("cartella", width=200)
    tree.column("num_file", width=70, anchor="center")
    tree.column("elenco_file", width=400)
    tree.column("ultima_modifica", width=160, anchor="center")
    tree.column("tempo_trascorso", width=140, anchor="center")

    tree.grid(row=2, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")

    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(3, weight=1)

    # === Nome verifica === #
    lbl_nome_verifica = tk.Label(frame, text="Nome verifica:", bg="lightblue")
    lbl_nome_verifica.grid(row=3, column=0, sticky="w", padx=5)
    entry_verifica = tk.Entry(frame, width=30, textvariable=global_config["verifica_name"])
    entry_verifica.grid(row=3, column=1, padx=5, pady=5, sticky="w")

    # === Pulsante crea copia locale === #
    def crea_copia():
        nome_verifica = global_config["verifica_name"].get().strip()
        directory_remota = global_config["remote_directory"].get().strip()
        if not nome_verifica or not directory_remota:
            lbl_esito.config(text="⚠️ Inserisci tutti i dati richiesti.", fg="red", bg="lightblue")
            return
        destinazione = filedialog.askdirectory(title="Seleziona destinazione")
        if destinazione:
            try:
                # Nome directory = timestamp + nome verifica
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                new_dir_name = f"{timestamp}_{nome_verifica}"
                new_dir = os.path.join(destinazione, new_dir_name)
                os.makedirs(new_dir, exist_ok=True)

                # Copia ricorsiva di TUTTI i file
                for root_dir, dirs, files in os.walk(directory_remota):
                    rel_path = os.path.relpath(root_dir, directory_remota)
                    dest_dir = os.path.join(new_dir, rel_path)
                    os.makedirs(dest_dir, exist_ok=True)
                    for file in files:
                        src_file = os.path.join(root_dir, file)
                        dest_file = os.path.join(dest_dir, file)
                        try:
                            with open(src_file, "rb") as fsrc, open(dest_file, "wb") as fdst:
                                fdst.write(fsrc.read())
                        except Exception as e:
                            print(f"Errore copiando {src_file}: {e}")

                # Aggiorna timestamp globale
                global_config["last_copy_timestamp"].set(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

                # Aggiorna label ed esito
                lbl_esito.config(text=f"Copia completata in {new_dir}", fg="green", bg="lightblue")
                messagebox.showinfo("Copia completata", f"I file sono stati copiati in:\n{new_dir}")

            except Exception as e:
                lbl_esito.config(text=f"Errore: {e}", fg="red", bg="lightblue")

    btn_copy = tk.Button(frame, text="Crea copia locale", command=crea_copia)
    btn_copy.grid(row=3, column=2, padx=5)

    lbl_esito = tk.Label(frame, text="", fg="green", bg="lightblue")
    lbl_esito.grid(row=3, column=3, columnspan=2, sticky="w")

    # === Funzione di aggiornamento periodico con timer === #
    countdown = {"value": SCAN_INTERVAL}

    def aggiorna_timer():
        if countdown["value"] > 0:
            lbl_timer.config(text=f"Prossima scansione tra {countdown['value']}s")
            countdown["value"] -= 1
            frame.after(1000, aggiorna_timer)
        else:
            aggiorna_tabella()

    def aggiorna_tabella():
        path = global_config["remote_directory"].get().strip()
        estensione = global_config["file_extension"].get().strip()
        if not path or not os.path.isdir(path):
            countdown["value"] = SCAN_INTERVAL
            aggiorna_timer()
            return

        tree.delete(*tree.get_children())
        risultati = utils.scan_test_directories(path, estensione)

        for nome_dir, num_file, files, ultima_mod in risultati:
            tempo_trascorso = ""
            if ultima_mod:
                try:
                    ultima_dt = datetime.datetime.strptime(ultima_mod, "%Y-%m-%d %H:%M:%S")
                    diff = datetime.datetime.now() - ultima_dt
                    minuti, secondi = divmod(int(diff.total_seconds()), 60)
                    if minuti > 0:
                        tempo_trascorso = f"{minuti}m {secondi}s"
                    else:
                        tempo_trascorso = f"{secondi}s"
                except Exception:
                    tempo_trascorso = "?"

            tree.insert("", "end", values=(nome_dir, num_file, ", ".join(files), ultima_mod, tempo_trascorso))

        # reset timer
        countdown["value"] = SCAN_INTERVAL
        aggiorna_timer()

    # Collega al bottone scan
    btn_scan.config(command=aggiorna_tabella)

    # Avvia scansione automatica con timer
    aggiorna_tabella()

    return frame
