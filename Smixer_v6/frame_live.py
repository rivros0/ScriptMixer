import os
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import utils
import datetime

SCAN_INTERVAL_BASE = 30   # s tra un ciclo e il successivo (se tutto ok)
SCAN_INTERVAL_MAX  = 120  # s massimo con backoff

def create_frame_live(root, global_config):
    frame = tk.Frame(root, bg="lightblue")

    # --- Riga 0: directory remota ---
    tk.Label(frame, text="Directory remota:", bg="lightblue").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    tk.Entry(frame, width=80, textvariable=global_config["remote_directory"]).grid(row=0, column=1, padx=5, pady=5, columnspan=3)

    def scegli_directory():
        directory = filedialog.askdirectory(title="Seleziona directory remota")
        if directory:
            global_config["remote_directory"].set(directory)

    tk.Button(frame, text="Scegli...", command=scegli_directory).grid(row=0, column=4, padx=5, pady=5)

    # --- Opzioni ---
    enable_loc = tk.BooleanVar(value=True)       # Conta linee
    enable_autoscan = tk.BooleanVar(value=True)  # Auto-scan a cicli

    # --- Riga 1: estensione + controlli ---
    tk.Label(frame, text="Estensione file (es: .cpp):", bg="lightblue").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    tk.Entry(frame, width=12, textvariable=global_config["file_extension"]).grid(row=1, column=1, padx=5, pady=5, sticky="w")

    chk_loc = tk.Checkbutton(frame, text="Conta linee", variable=enable_loc, bg="lightblue")
    chk_loc.grid(row=1, column=2, padx=5, pady=5, sticky="w")

    chk_autoscan = tk.Checkbutton(frame, text="Auto-scan", variable=enable_autoscan, bg="lightblue")
    chk_autoscan.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    btn_scan = tk.Button(frame, text="Scan", width=12)
    btn_scan.grid(row=1, column=4, padx=5, pady=5)

    lbl_timer = tk.Label(frame, text=f"In attesa…", fg="blue", bg="lightblue")
    lbl_timer.grid(row=1, column=5, padx=10, sticky="w")

    # --- Tabella ---
    tree = ttk.Treeview(
        frame,
        columns=("cartella", "num_file", "linee_totali", "elenco_file", "ultima_modifica", "tempo_trascorso"),
        show="headings"
    )
    for col, text, w, anchor in (
        ("cartella", "Cartella", 180, "w"),
        ("num_file", "N. File", 70, "center"),
        ("linee_totali", "Linee (tot)", 100, "e"),
        ("elenco_file", "File trovati", 380, "w"),
        ("ultima_modifica", "Ultima modifica", 160, "center"),
        ("tempo_trascorso", "Tempo trascorso", 120, "center"),
    ):
        tree.heading(col, text=text)
        tree.column(col, width=w, anchor=anchor)
    tree.grid(row=2, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")

    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(3, weight=1)

    # --- Riga 3: copia locale + esito ---
    tk.Label(frame, text="Nome verifica:", bg="lightblue").grid(row=3, column=0, sticky="w", padx=5)
    tk.Entry(frame, width=30, textvariable=global_config["verifica_name"]).grid(row=3, column=1, padx=5, pady=5, sticky="w")

    lbl_esito = tk.Label(frame, text="", fg="green", bg="lightblue")
    lbl_esito.grid(row=3, column=3, columnspan=2, sticky="w")

    def crea_copia():
        nome_verifica = global_config["verifica_name"].get().strip()
        directory_remota = global_config["remote_directory"].get().strip()
        if not nome_verifica or not directory_remota:
            lbl_esito.config(text="⚠️ Inserisci tutti i dati richiesti.", fg="red", bg="lightblue")
            return
        destinazione = filedialog.askdirectory(title="Seleziona destinazione")
        if destinazione:
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                new_dir_name = f"{timestamp}_{nome_verifica}"
                new_dir = os.path.join(destinazione, new_dir_name)
                os.makedirs(new_dir, exist_ok=True)

                # Copia SOLO test01...test30 (blindato)
                for i in range(1, 31):
                    nome_dir = f"test{str(i).zfill(2)}"
                    src_dir = os.path.join(directory_remota, nome_dir)
                    dest_dir = os.path.join(new_dir, nome_dir)
                    if os.path.isdir(src_dir):
                        os.makedirs(dest_dir, exist_ok=True)
                        for root_dir, dirs, files in os.walk(src_dir):
                            rel_path = os.path.relpath(root_dir, src_dir)
                            final_dest = os.path.join(dest_dir, rel_path)
                            os.makedirs(final_dest, exist_ok=True)
                            for file in files:
                                src_file = os.path.join(root_dir, file)
                                dest_file = os.path.join(final_dest, file)
                                try:
                                    with open(src_file, "rb") as fsrc, open(dest_file, "wb") as fdst:
                                        fdst.write(fsrc.read())
                                except Exception as e:
                                    print(f"Errore copiando {src_file}: {e}")

                lbl_esito.config(text=f"Copia completata in {new_dir}", fg="green", bg="lightblue")
                messagebox.showinfo("Copia completata", f"I file sono stati copiati in:\n{new_dir}")
            except Exception as e:
                lbl_esito.config(text=f"Errore: {e}", fg="red", bg="lightblue")

    tk.Button(frame, text="Crea copia locale", command=crea_copia).grid(row=3, column=2, padx=5)

    # ====== Stato per scansione progressiva ====== #
    scan_interval = {"value": SCAN_INTERVAL_BASE}
    failure_streak = {"value": 0}

    countdown = {"value": SCAN_INTERVAL_BASE}   # tempo tra cicli (quando non si sta scansionando)
    timer_id = {"after": None}                  # singolo timer
    tick_id = {"after": None}                   # tick 1/sec durante la scansione progressiva

    scan_state = {
        "active": False,
        "start_time": 0.0,
        "names": [],      # lista cartelle da elaborare
        "index": 0,       # indice corrente
        "path": "",       # base path
        "ext": "",        # estensione normalizzata (.cpp ecc.)
    }

    def stop_timer():
        if timer_id["after"] is not None:
            try: frame.after_cancel(timer_id["after"])
            except Exception: pass
            timer_id["after"] = None

    def stop_tick():
        if tick_id["after"] is not None:
            try: frame.after_cancel(tick_id["after"])
            except Exception: pass
            tick_id["after"] = None

    def start_timer():
        """(Ri)avvia il conto alla rovescia tra un ciclo e il successivo."""
        stop_timer()
        if not enable_autoscan.get():
            lbl_timer.config(text="Auto-scan OFF")
            return
        countdown["value"] = scan_interval["value"]
        lbl_timer.config(text=f"Prossimo ciclo tra {countdown['value']}s")
        timer_id["after"] = frame.after(1000, countdown_tick)

    def countdown_tick():
        if not enable_autoscan.get():
            stop_timer()
            lbl_timer.config(text="Auto-scan OFF")
            return
        countdown["value"] -= 1
        if countdown["value"] > 0:
            lbl_timer.config(text=f"Prossimo ciclo tra {countdown['value']}s")
            timer_id["after"] = frame.after(1000, countdown_tick)
        else:
            stop_timer()
            begin_scan_cycle()

    def begin_scan_cycle():
        """Prepara una scansione progressiva (una cartella al secondo)."""
        stop_timer()
        stop_tick()

        base = global_config["remote_directory"].get().strip()
        if not base or not os.path.isdir(base):
            lbl_timer.config(text="Percorso non valido")
            if enable_autoscan.get():
                # aumenta un po' l'intervallo e riprova
                scan_interval["value"] = min(SCAN_INTERVAL_MAX, scan_interval["value"] + 15)
                start_timer()
            return

        ext = global_config["file_extension"].get().strip()
        if ext and not ext.startswith("."):
            ext = "." + ext

        # prepara elenco cartelle test presenti (senza camminare i file)
        names = utils.list_test_dir_names(base, root_prefix="test*")

        # reset tabella
        tree.delete(*tree.get_children())
        # inserisci placeholder per stabilizzare l'UI
        for name in names:
            tree.insert("", "end", iid=name, values=(name, "…", "…", "…", "…", "…"))

        scan_state.update({
            "active": True,
            "start_time": time.time(),
            "names": names,
            "index": 0,
            "path": base,
            "ext": ext,
        })
        lbl_timer.config(text=f"Scansione in corso… (0/{len(names)})")
        process_next_dir()  # parte subito la prima

    def process_next_dir():
        """Elabora una cartella e pianifica la successiva tra 1 secondo."""
        stop_tick()  # evita doppi tick
        if not scan_state["active"]:
            return

        names = scan_state["names"]
        i = scan_state["index"]
        total = len(names)

        # Fine?
        if i >= total:
            end_scan_cycle()
            return

        base = scan_state["path"]
        ext  = scan_state["ext"]
        name = names[i]

        try:
            (nm, num_file, files, ultima_mod, total_loc) = utils.dir_summary(
                base, name, extension=ext, with_loc=bool(enable_loc.get())
            )

            # calcolo tempo trascorso dall'ultima mod
            import datetime as _dt
            tempo_trascorso = ""
            if ultima_mod:
                try:
                    ultima_dt = _dt.datetime.strptime(ultima_mod, "%Y-%m-%d %H:%M:%S")
                    diff = utils.now_ts() - ultima_dt
                    m, s = divmod(int(diff.total_seconds()), 60)
                    tempo_trascorso = f"{m}m {s}s" if m > 0 else f"{s}s"
                except Exception:
                    tempo_trascorso = "?"

            # aggiorna/crea riga
            values = (
                nm,
                num_file,
                (total_loc if enable_loc.get() else "–"),
                ", ".join(files),
                ultima_mod,
                tempo_trascorso
            )
            if tree.exists(nm):
                tree.item(nm, values=values)
            else:
                tree.insert("", "end", iid=nm, values=values)

        except Exception as e:
            # in caso di errore, mostra qualcosa e continua
            if tree.exists(name):
                tree.item(name, values=(name, "ERR", "–", "(errore lettura)", "", ""))
            else:
                tree.insert("", "end", iid=name, values=(name, "ERR", "–", "(errore lettura)", "", ""))

        # avanzamento
        scan_state["index"] = i + 1
        lbl_timer.config(text=f"Scansione in corso… ({scan_state['index']}/{total})")

        # pianifica la prossima cartella tra 1 secondo, se ancora attivo
        if scan_state["active"]:
            tick_id["after"] = frame.after(1000, process_next_dir)

    def end_scan_cycle():
        """Chiusura del ciclo progressivo + backoff + (eventuale) avvio countdown prossimo ciclo."""
        stop_tick()
        scan_state["active"] = False
        duration = time.time() - scan_state["start_time"]

        # Backoff semplice: se >5s o ci sono state eccezioni visibili (difficile da contare qui),
        # aumentiamo l'intervallo, altrimenti riduciamo gradualmente verso la base.
        if duration > 5 * max(1, len(scan_state["names"])):  # durata media >5s/cartella: rete pesante
            scan_interval["value"] = min(SCAN_INTERVAL_MAX, int(scan_interval["value"] * 1.5))
        else:
            # alleggeriamo fino alla base
            if scan_interval["value"] > SCAN_INTERVAL_BASE:
                scan_interval["value"] = max(SCAN_INTERVAL_BASE, scan_interval["value"] - 15)

        lbl_timer.config(text=f"Ciclo completato in {int(duration)}s • Prossimo in {scan_interval['value']}s")

        if enable_autoscan.get():
            start_timer()
        else:
            lbl_timer.config(text="Auto-scan OFF")

    # --- Handlers UI ---
    def on_toggle_autoscan():
        if enable_autoscan.get():
            # se si riattiva mentre una scansione è già in corso, non fare nulla: prosegue a goccia
            if not scan_state["active"]:
                start_timer()
        else:
            # disattiva tutto
            stop_timer()
            stop_tick()
            scan_state["active"] = False
            lbl_timer.config(text="Auto-scan OFF")

    chk_autoscan.config(command=on_toggle_autoscan)

    def manual_scan():
        """Avvia subito un ciclo progressivo; interrompe timer/eventuali cicli in corso."""
        stop_timer()
        stop_tick()
        scan_state["active"] = False
        begin_scan_cycle()

    btn_scan.config(command=manual_scan)

    # avvio iniziale: parte un ciclo subito, poi countdown in base alle impostazioni
    manual_scan()
    return frame
