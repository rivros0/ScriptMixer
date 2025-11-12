import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import threading
import queue
from ftplib import FTP
from datetime import datetime

import similarity

YELLOW_BG = "#5d0066"


def format_bytes(num_bytes):
    """
    Converte un numero di byte in una stringa leggibile (B, KB, MB, GB, ...).
    """
    unita = ["B", "KB", "MB", "GB", "TB"]
    valore = float(num_bytes)
    indice = 0

    while valore >= 1024.0 and indice < len(unita) - 1:
        valore = valore / 1024.0
        indice = indice + 1

    if indice == 0:
        return str(int(valore)) + " " + unita[indice]

    return "{:.1f} {}".format(valore, unita[indice])


def get_versioned_path(percorso_base):
    """
    Restituisce un percorso libero applicando un versionamento incrementale.
    Se il file non esiste usa il nome originale.
    Se esiste:
        nome.ext -> nome_v01.ext, poi nome_v02.ext, ecc.
    """
    if not os.path.exists(percorso_base):
        return percorso_base

    base, ext = os.path.splitext(percorso_base)
    contatore = 1

    while True:
        nuovo_percorso = "{}_v{:02d}{}".format(base, contatore, ext)
        if not os.path.exists(nuovo_percorso):
            return nuovo_percorso
        contatore = contatore + 1


def create_frame_domini(root, global_config):
    """
    Frame per la gestione dei domini Altervista:
    - Creazione modello CSV
    - Caricamento CSV (cognome, dominio, ftp_user, ftp_password)
    - Associazione cognome -> cartella testXX-cognome
    - Download FTP (in parallelo) con versionamento dei file
    - Tabella riepilogativa:
        Nome alunno, dominio, stato, avanzamento, numero file,
        elenco file, peso complessivo cartella, ultima modifica
    - Label in alto a destra con peso complessivo di 00_DominiFTP
    - Analisi delle somiglianze e mappa delle similitudini
    """
    frame = tk.Frame(root, bg=YELLOW_BG)

    # ==================================================================
    # CODA PER AGGIORNAMENTI GUI (usata dai thread worker)
    # ==================================================================
    update_queue = queue.Queue()

    # Risultati analisi similarità (riempiti da "Analizza somiglianze")
    similarity_results = {}

    # ==================================================================
    # RIGA 0: PULSANTI COMANDI + LABEL PESO TOTALE FTP
    # ==================================================================
    btn_modello = tk.Button(frame, text="Crea modello CSV", width=18)
    btn_modello.grid(row=0, column=0, padx=6, pady=6, sticky="w")

    btn_carica = tk.Button(frame, text="Carica file domini (CSV)", width=24)
    btn_carica.grid(row=0, column=1, padx=6, pady=6, sticky="w")

    btn_scarica = tk.Button(frame, text="Scarica tutti i domini via FTP", width=24, state="disabled")
    btn_scarica.grid(row=0, column=2, padx=6, pady=6, sticky="w")

    btn_analizza = tk.Button(frame, text="Analizza somiglianze", width=24, state="disabled")
    btn_analizza.grid(row=0, column=3, padx=6, pady=6, sticky="w")

    btn_mappa = tk.Button(frame, text="Mostra mappa similitudini", width=24, state="disabled")
    btn_mappa.grid(row=0, column=4, padx=6, pady=6, sticky="w")

    lbl_peso_totale = tk.Label(
        frame,
        text="Totale FTP: 0 B",
        bg='white',
        anchor="e",
    )
    lbl_peso_totale.grid(row=0, column=5, padx=10, pady=6, sticky="e")

    # ==================================================================
    # RIGA 1: TABELLA PRINCIPALE
    # ==================================================================
    colonne = (
        "Alunno",
        "Dominio",
        "Stato",
        "Avanzamento",
        "N. file",
        "Elenco file",
        "Peso cartella",
        "Ultima modifica",
    )

    tree = ttk.Treeview(frame, columns=colonne, show="headings", height=18)

    for col in colonne:
        tree.heading(col, text=col)

        if col == "Alunno":
            tree.column(col, width=120, anchor="center")
        elif col == "Dominio":
            tree.column(col, width=180, anchor="center")
        elif col == "Stato":
            tree.column(col, width=220, anchor="w")
        elif col == "Elenco file":
            tree.column(col, width=260, anchor="w")
        else:
            tree.column(col, width=120, anchor="center")

    tree.grid(row=1, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")

    scrollbar_vert = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_vert.set)
    scrollbar_vert.grid(row=1, column=6, sticky="ns")

    # ==================================================================
    # RIGHE 2-3: AREA LOG
    # ==================================================================
    tk.Label(frame, text="Log eventi:", bg=YELLOW_BG).grid(row=2, column=0, sticky="w", padx=6, pady=6)

    txt_log = tk.Text(frame, height=8, width=120)
    txt_log.grid(row=3, column=0, columnspan=7, padx=10, pady=5, sticky="ew")

    def log(messaggio):
        """
        Scrive un messaggio nel riquadro log.
        Da usare solo nel thread principale o tramite update_queue.
        """
        txt_log.insert("end", messaggio + "\n")
        txt_log.see("end")

    # ==================================================================
    # STRUTTURE DATI IN MEMORIA
    # ==================================================================
    credenziali_by_item = {}   # item_id -> (ftp_user, ftp_pass)
    testdir_by_item = {}       # item_id -> cartella test associata

    # ==================================================================
    # FUNZIONE: CREA MODELLO CSV
    # ==================================================================
    def crea_modello_csv():
        """
        Crea un file CSV con intestazioni:
            cognome, dominio, ftp_user, ftp_password

        Se la directory selezionata contiene cartelle testXX-cognome,
        estrae automaticamente i cognomi.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if os.path.isdir(base_dir):
            initial_dir = base_dir
        else:
            initial_dir = os.getcwd()

        percorso_csv = filedialog.asksaveasfilename(
            title="Salva modello CSV",
            defaultextension=".csv",
            initialdir=initial_dir,
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
        )

        if not percorso_csv:
            return

        cognomi = []

        if os.path.isdir(base_dir):
            elementi = os.listdir(base_dir)
            for nome_dir in elementi:
                percorso_dir = os.path.join(base_dir, nome_dir)
                if os.path.isdir(percorso_dir) and nome_dir.lower().startswith("test"):
                    parti = nome_dir.split("-", 1)
                    if len(parti) == 2:
                        cognome = parti[1].strip().lower()
                        if cognome:
                            cognomi.append(cognome)

        try:
            with open(percorso_csv, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["cognome", "dominio", "ftp_user", "ftp_password"])

                insieme_cognomi = sorted(set(cognomi))
                for cognome in insieme_cognomi:
                    writer.writerow([cognome, "", "", ""])

            log("Modello CSV creato in: " + percorso_csv)
            if cognomi:
                log(
                    "Inseriti automaticamente {} cognomi dalle cartelle test.".format(
                        len(set(cognomi))
                    )
                )
            else:
                log("Nessuna cartella test trovata: modello creato solo con intestazioni.")
        except Exception as e:
            messagebox.showerror("Errore", "Errore nella creazione del modello CSV:\n" + str(e))

    btn_modello.configure(command=crea_modello_csv)

    # ==================================================================
    # FUNZIONE: CARICA CSV
    # ==================================================================
    def carica_csv():
        """
        Carica un CSV con colonne:
            cognome, dominio, ftp_user, ftp_password

        Popola la tabella con:
            Alunno, Dominio, Stato iniziale (Test OK / Test non trovato),
            Avanzamento=0%, N. file=0, Elenco file vuoto,
            Peso=0 B, Ultima modifica vuota.

        Le password NON vengono mostrate, ma vengono salvate in memoria
        in 'credenziali_by_item'.
        """
        for item in tree.get_children():
            tree.delete(item)
        credenziali_by_item.clear()
        testdir_by_item.clear()
        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_mappa.configure(state="disabled")
        similarity_results.clear()

        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove (cartelle testXX).",
            )
            return

        percorso_csv = filedialog.askopenfilename(
            title="Seleziona file CSV con domini",
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
        )

        if not percorso_csv:
            return

        test_dirs = []
        for nome_dir in os.listdir(base_dir):
            percorso_dir = os.path.join(base_dir, nome_dir)
            if os.path.isdir(percorso_dir) and nome_dir.lower().startswith("test"):
                test_dirs.append(nome_dir)

        log("Trovate {} cartelle test nella directory selezionata.".format(len(test_dirs)))

        try:
            with open(percorso_csv, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                righe = list(reader)
        except Exception as e:
            messagebox.showerror("Errore", "Errore nella lettura del CSV:\n" + str(e))
            return

        if not righe:
            messagebox.showwarning("Attenzione", "Il CSV selezionato non contiene righe.")
            return

        righe_inserite = 0

        for row in righe:
            cognome = row.get("cognome", "").strip().lower()
            dominio = row.get("dominio", "").strip()
            ftp_user = row.get("ftp_user", "").strip()
            ftp_pass = row.get("ftp_password", "").strip()

            if not cognome and not dominio:
                continue

            found_test = ""
            stato_iniziale = "Test non trovato"

            for td in test_dirs:
                if td.lower().endswith(cognome):
                    found_test = td
                    stato_iniziale = "Test OK"
                    break

            valori = (
                cognome,        # Alunno
                dominio,        # Dominio
                stato_iniziale, # Stato
                "0%",           # Avanzamento
                "0",            # N. file
                "",             # Elenco file
                "0 B",          # Peso cartella
                "",             # Ultima modifica
            )

            item_id = tree.insert("", "end", values=valori)
            credenziali_by_item[item_id] = (ftp_user, ftp_pass)
            testdir_by_item[item_id] = found_test
            righe_inserite = righe_inserite + 1

        log(
            "File CSV '{}' caricato correttamente. Righe valide: {}".format(
                os.path.basename(percorso_csv),
                righe_inserite,
            )
        )

        if righe_inserite > 0:
            btn_scarica.configure(state="normal")
            log(
                "Bottone download FTP abilitato ({} domini caricati).".format(
                    righe_inserite
                )
            )
        else:
            btn_scarica.configure(state="disabled")
            messagebox.showwarning("Attenzione", "Nessuna riga valida trovata nel CSV.")

    btn_carica.configure(command=carica_csv)

    # ==================================================================
    # FUNZIONE: RICALCOLO PESO TOTALE DIRECTORY 00_DominiFTP
    # ==================================================================
    def aggiorna_peso_totale_ftp():
        """
        Calcola il peso complessivo della directory 00_DominiFTP
        e aggiorna la label in alto a destra.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            lbl_peso_totale.config(text="Totale FTP: 0 B")
            return

        dir_ftp = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp):
            lbl_peso_totale.config(text="Totale FTP: 0 B")
            return

        totale = 0
        for radice, _, files in os.walk(dir_ftp):
            for nome_file in files:
                percorso_file = os.path.join(radice, nome_file)
                try:
                    totale = totale + os.path.getsize(percorso_file)
                except Exception:
                    pass

        lbl_peso_totale.config(text="Totale FTP: " + format_bytes(totale))

    # ==================================================================
    # FUNZIONE: PROCESSO CENTRALE CHE LEGGE LA CODA E AGGIORNA LA GUI
    # ==================================================================
    def process_update_queue():
        """
        Legge gli aggiornamenti dalla coda e li applica alla GUI.
        Viene richiamata periodicamente tramite after().
        """
        try:
            while True:
                task = update_queue.get_nowait()
                tipo = task[0]

                if tipo == "log":
                    messaggio = task[1]
                    log(messaggio)

                elif tipo == "set":
                    item_id = task[1]
                    colonna = task[2]
                    valore = task[3]
                    try:
                        tree.set(item_id, colonna, valore)
                    except Exception:
                        pass

                elif tipo == "fine_download":
                    aggiorna_peso_totale_ftp()
                    log("=== Download FTP completato ===")
                    btn_scarica.configure(state="normal")
                    btn_analizza.configure(state="normal")
        except queue.Empty:
            pass

        frame.after(100, process_update_queue)

    # ==================================================================
    # FUNZIONE: DOWNLOAD FTP DI TUTTI I DOMINI (IN PARALLELO)
    # ==================================================================
    def scarica_tutti():
        """
        Per ogni riga in tabella:
        - prepara un job con i dati necessari
        - lancia un thread worker per ciascun job (in parallelo)
        - i thread lavorano sull'FTP e mandano gli aggiornamenti GUI sulla coda
        - un thread "monitor" attende la fine di tutti i worker e manda
          in coda l'evento "fine_download".
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove (cartelle testXX).",
            )
            return

        items = tree.get_children()
        if not items:
            messagebox.showwarning(
                "Attenzione",
                "Nessun dominio da scaricare. Carica prima il CSV.",
            )
            return

        dir_ftp_base = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp_base):
            os.makedirs(dir_ftp_base, exist_ok=True)

        log("=== Inizio download FTP in {} ===".format(dir_ftp_base))
        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_mappa.configure(state="disabled")
        similarity_results.clear()

        # prepara lista di job (lettura dei dati SOLO nel main thread)
        jobs = []
        for item_id in items:
            valori_correnti = list(tree.item(item_id, "values"))
            alunno = valori_correnti[0]
            dominio = valori_correnti[1]
            stato_base = valori_correnti[2]
            ftp_user, ftp_pass = credenziali_by_item.get(item_id, ("", ""))

            job = {
                "item_id": item_id,
                "alunno": alunno,
                "dominio": dominio,
                "stato_base": stato_base,
                "ftp_user": ftp_user,
                "ftp_pass": ftp_pass,
            }
            jobs.append(job)

        def worker_job(job):
            """
            Thread worker per un singolo dominio.
            Fa TUTTO il lavoro di FTP e invia aggiornamenti alla GUI
            tramite la coda 'update_queue'.
            """
            item_id = job["item_id"]
            alunno = job["alunno"]
            dominio = job["dominio"]
            stato_base = job["stato_base"]
            ftp_user = job["ftp_user"]
            ftp_pass = job["ftp_pass"]

            host = dominio
            if host and not host.startswith("ftp."):
                host = "ftp." + host

            # reset campi di avanzamento (tramite coda)
            update_queue.put(("set", item_id, "Stato", stato_base + " / Connessione FTP..."))
            update_queue.put(("set", item_id, "Avanzamento", "0%"))
            update_queue.put(("set", item_id, "N. file", "0"))
            update_queue.put(("set", item_id, "Elenco file", ""))
            update_queue.put(("set", item_id, "Peso cartella", "0 B"))
            update_queue.put(("set", item_id, "Ultima modifica", ""))

            if not dominio:
                update_queue.put(("log", "❌ Nessun dominio specificato per '{}'.".format(alunno)))
                update_queue.put(("set", item_id, "Stato", "Errore: dominio mancante"))
                return

            if not ftp_user or not ftp_pass:
                update_queue.put(
                    (
                        "log",
                        "❌ Credenziali mancanti per '{}' ({}).".format(alunno, dominio),
                    )
                )
                update_queue.put(("set", item_id, "Stato", "Errore: credenziali mancanti"))
                return

            update_queue.put(("log", "Connessione a {} per '{}'...".format(host, alunno)))

            try:
                ftp = FTP(host, timeout=30, encoding="latin-1")
                ftp.login(user=ftp_user, passwd=ftp_pass)
                update_queue.put(("set", item_id, "Stato", stato_base + " / Login OK"))
                update_queue.put(
                    (
                        "log",
                        "✅ Login riuscito su {} per '{}'".format(
                            host,
                            alunno,
                        ),
                    )
                )
            except Exception as e:
                update_queue.put(("set", item_id, "Stato", "Errore login FTP"))
                update_queue.put(
                    (
                        "log",
                        "❌ Errore di connessione/login {} per '{}': {}".format(
                            host,
                            alunno,
                            e,
                        ),
                    )
                )
                return

            nome_cartella_alunno = alunno if alunno else "sconosciuto"
            dir_locale_alunno = os.path.join(dir_ftp_base, nome_cartella_alunno)
            if not os.path.isdir(dir_locale_alunno):
                try:
                    os.makedirs(dir_locale_alunno, exist_ok=True)
                except Exception:
                    pass

            lista_file_remoti = []
            ultima_modifica = None

            def collect_files(percorso_remoto):
                nonlocal ultima_modifica

                try:
                    entries = list(ftp.mlsd(percorso_remoto))
                except Exception:
                    try:
                        ftp.cwd(percorso_remoto)
                        nomi = ftp.nlst()
                    except Exception:
                        return
                    for nome in nomi:
                        if nome not in (".", ".."):
                            if percorso_remoto in (".", ""):
                                remoto = nome
                            else:
                                remoto = percorso_remoto + "/" + nome
                            lista_file_remoti.append(remoto)
                    return

                for nome, facts in entries:
                    if nome in (".", ".."):
                        continue

                    tipo = facts.get("type", "")
                    if percorso_remoto in (".", ""):
                        remoto = nome
                    else:
                        remoto = percorso_remoto + "/" + nome

                    if tipo == "dir":
                        collect_files(remoto)
                    else:
                        lista_file_remoti.append(remoto)
                        modify = facts.get("modify")
                        if modify:
                            try:
                                data = datetime.strptime(modify, "%Y%m%d%H%M%S")
                                if ultima_modifica is None or data > ultima_modifica:
                                    ultima_modifica = data
                            except Exception:
                                pass

            collect_files(".")

            totale_file = len(lista_file_remoti)
            if totale_file == 0:
                update_queue.put(
                    (
                        "set",
                        item_id,
                        "Stato",
                        stato_base + " / Nessun file remoto",
                    )
                )
                update_queue.put(
                    (
                        "log",
                        "ℹ Nessun file trovato su {} per '{}'".format(
                            dominio,
                            alunno,
                        ),
                    )
                )
                try:
                    ftp.quit()
                except Exception:
                    pass
                return

            conteggio_file = 0
            peso_totale_alunno = 0
            elenco_file_preview = []

            for remoto in lista_file_remoti:
                parti = remoto.split("/")
                cartella_locale_corrente = dir_locale_alunno

                for nome_dir in parti[:-1]:
                    cartella_locale_corrente = os.path.join(
                        cartella_locale_corrente,
                        nome_dir,
                    )
                    if not os.path.isdir(cartella_locale_corrente):
                        try:
                            os.makedirs(cartella_locale_corrente, exist_ok=True)
                        except Exception:
                            pass

                nome_file = parti[-1]
                percorso_locale_base = os.path.join(cartella_locale_corrente, nome_file)
                percorso_locale = get_versioned_path(percorso_locale_base)

                try:
                    with open(percorso_locale, "wb") as f_locale:
                        ftp.retrbinary("RETR " + remoto, f_locale.write)
                except Exception:
                    continue

                try:
                    dimensione = os.path.getsize(percorso_locale)
                    peso_totale_alunno = peso_totale_alunno + dimensione
                except Exception:
                    pass

                conteggio_file = conteggio_file + 1

                if len(elenco_file_preview) < 10:
                    elenco_file_preview.append(os.path.basename(percorso_locale))
                elif len(elenco_file_preview) == 10:
                    elenco_file_preview.append("...")

                percentuale = int((conteggio_file * 100) / float(totale_file))

                update_queue.put(
                    ("set", item_id, "Avanzamento", "{}%".format(percentuale))
                )
                update_queue.put(("set", item_id, "N. file", str(conteggio_file)))
                update_queue.put(
                    (
                        "set",
                        item_id,
                        "Peso cartella",
                        format_bytes(peso_totale_alunno),
                    )
                )
                update_queue.put(
                    (
                        "set",
                        item_id,
                        "Elenco file",
                        ", ".join(elenco_file_preview),
                    )
                )

            try:
                ftp.quit()
            except Exception:
                pass

            if ultima_modifica is not None:
                testo_data = ultima_modifica.strftime("%Y-%m-%d %H:%M")
            else:
                testo_data = "n.d."

            update_queue.put(( "set", item_id, "Ultima modifica", testo_data))
            update_queue.put(
                (
                    "set",
                    item_id,
                    "Stato",
                    stato_base + " / Download OK",
                )
            )
            update_queue.put(
                (
                    "log",
                    "✅ Download completato per '{}' ({}). Ultima modifica remota: {}".format(
                        alunno,
                        dominio,
                        testo_data,
                    ),
                )
            )

        # avvio di tutti i worker in parallelo
        threads = []
        for job in jobs:
            t = threading.Thread(target=worker_job, args=(job,))
            t.daemon = True
            t.start()
            threads.append(t)

        def monitor_thread():
            indice = 0
            while indice < len(threads):
                threads[indice].join()
                indice = indice + 1
            update_queue.put(("fine_download", None))

        monitor = threading.Thread(target=monitor_thread, daemon=True)
        monitor.start()

    # ==================================================================
    # FUNZIONE: ANALISI DELLE SOMIGLIANZE
    # ==================================================================
    def analizza_somiglianze():
        """
        Analizza le somiglianze secondo i casi richiesti:

        1) Verifica contro dominio personale
        2) Verifica contro verifiche dei compagni
        3) Verifica contro domini dei compagni
        4) Dominio personale contro domini dei compagni

        I risultati vengono riassunti nel log e salvati in 'similarity_results'
        per la visualizzazione della mappa.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove (cartelle testXX).",
            )
            return

        dir_ftp_base = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp_base):
            messagebox.showwarning(
                "Attenzione",
                "La directory 00_DominiFTP non esiste. Esegui prima il download dai domini.",
            )
            return

        # Costruzione delle mappe {studente: directory_verifica} e {studente: directory_dominio}
        tests_dirs = {}
        domini_dirs = {}

        for item_id in tree.get_children():
            valori = list(tree.item(item_id, "values"))
            alunno = valori[0]

            if not alunno:
                continue

            nome_cartella_test = testdir_by_item.get(item_id, "")
            if nome_cartella_test:
                percorso_test = os.path.join(base_dir, nome_cartella_test)
                if os.path.isdir(percorso_test):
                    tests_dirs[alunno] = percorso_test

            dir_dominio_alunno = os.path.join(dir_ftp_base, alunno)
            if os.path.isdir(dir_dominio_alunno):
                domini_dirs[alunno] = dir_dominio_alunno

        estensioni_ammesse = (".php", ".html", ".htm", ".css", ".js", ".txt")

        studenti_test, testi_test = similarity.build_texts_from_directories(
            tests_dirs,
            estensioni_ammesse,
        )
        studenti_domini, testi_domini = similarity.build_texts_from_directories(
            domini_dirs,
            estensioni_ammesse,
        )

        similarity_results.clear()

        if len(studenti_test) >= 2:
            matrice_test_test = similarity.build_similarity_matrix(studenti_test, testi_test)
            similarity_results["test_vs_test"] = {
                "rows": studenti_test,
                "cols": studenti_test,
                "matrix": matrice_test_test,
            }
        else:
            matrice_test_test = None

        if len(studenti_domini) >= 2:
            matrice_dom_dom = similarity.build_similarity_matrix(studenti_domini, testi_domini)
            similarity_results["dom_vs_dom"] = {
                "rows": studenti_domini,
                "cols": studenti_domini,
                "matrix": matrice_dom_dom,
            }
        else:
            matrice_dom_dom = None

        if len(studenti_test) >= 1 and len(studenti_domini) >= 1:
            matrice_test_dom = similarity.build_cross_similarity_matrix(
                studenti_test,
                studenti_domini,
                testi_test,
                testi_domini,
            )
            similarity_results["test_vs_dom"] = {
                "rows": studenti_test,
                "cols": studenti_domini,
                "matrix": matrice_test_dom,
            }
        else:
            matrice_test_dom = None

        log("=== Analisi somiglianze avviata ===")

        soglia_alta = 80.0
        soglia_media = 60.0

        # Report sintetico per ogni studente
        for nome in sorted(set(list(studenti_test) + list(studenti_domini))):
            descrizioni = []

            # 1) Verifica contro dominio personale
            valore_personale = None
            if matrice_test_dom is not None and nome in studenti_test and nome in studenti_domini:
                indice_test = studenti_test.index(nome)
                indice_dom = studenti_domini.index(nome)
                valore_personale = matrice_test_dom[indice_test][indice_dom]
                descrizioni.append(
                    "V vs Dom pers: {:.1f}%".format(valore_personale)
                )

            # 2) Verifica contro verifiche dei compagni
            if matrice_test_test is not None and nome in studenti_test:
                indice = studenti_test.index(nome)
                miglior = 0.0
                miglior_nome = ""

                indice_compagno = 0
                while indice_compagno < len(studenti_test):
                    if indice_compagno != indice:
                        valore = matrice_test_test[indice][indice_compagno]
                        if valore > miglior:
                            miglior = valore
                            miglior_nome = studenti_test[indice_compagno]
                    indice_compagno = indice_compagno + 1

                if miglior_nome:
                    descrizioni.append(
                        "V vs V comp: {:.1f}% con {}".format(miglior, miglior_nome)
                    )

            # 3) Verifica contro domini dei compagni
            if matrice_test_dom is not None and nome in studenti_test:
                indice = studenti_test.index(nome)
                miglior = 0.0
                miglior_nome = ""

                indice_compagno = 0
                while indice_compagno < len(studenti_domini):
                    nome_dom = studenti_domini[indice_compagno]
                    if nome_dom != nome:
                        valore = matrice_test_dom[indice][indice_compagno]
                        if valore > miglior:
                            miglior = valore
                            miglior_nome = nome_dom
                    indice_compagno = indice_compagno + 1

                if miglior_nome:
                    descrizioni.append(
                        "V vs Dom comp: {:.1f}% con dominio {}".format(
                            miglior,
                            miglior_nome,
                        )
                    )

            # 4) Dominio personale contro domini dei compagni
            if matrice_dom_dom is not None and nome in studenti_domini:
                indice = studenti_domini.index(nome)
                miglior = 0.0
                miglior_nome = ""

                indice_compagno = 0
                while indice_compagno < len(studenti_domini):
                    if indice_compagno != indice:
                        valore = matrice_dom_dom[indice][indice_compagno]
                        if valore > miglior:
                            miglior = valore
                            miglior_nome = studenti_domini[indice_compagno]
                    indice_compagno = indice_compagno + 1

                if miglior_nome:
                    descrizioni.append(
                        "Dom vs Dom comp: {:.1f}% con {}".format(
                            miglior,
                            miglior_nome,
                        )
                    )

            if not descrizioni:
                continue

            riga = nome + " -> " + " | ".join(descrizioni)
            log(riga)

            if valore_personale is not None:
                if valore_personale >= soglia_alta:
                    log("  ⚠ Verifica molto simile al dominio personale (possibile riuso intenso del codice online).")
                elif valore_personale >= soglia_media:
                    log("  ℹ Verifica moderatamente simile al dominio personale (riuso parziale del codice online possibile).")

        if not similarity_results:
            log("Nessuna matrice di similarità calcolabile con i dati correnti.")
            btn_mappa.configure(state="disabled")
        else:
            log("=== Analisi somiglianze completata ===")
            btn_mappa.configure(state="normal")

    # ==================================================================
    # FUNZIONE: MOSTRA MAPPA DELLE SIMILITUDINI
    # ==================================================================
    def mostra_mappa():
        """
        Mostra una o più heatmap delle matrici calcolate in 'analizza_somiglianze'.
        """
        if not similarity_results:
            messagebox.showinfo(
                "Informazione",
                "Non ci sono risultati di similarità da visualizzare. Esegui prima l'analisi.",
            )
            return

        parent = frame

        if "test_vs_test" in similarity_results:
            dati = similarity_results["test_vs_test"]
            similarity.show_heatmap(
                parent,
                "Verifica vs verifiche compagni",
                dati["rows"],
                dati["cols"],
                dati["matrix"],
            )

        if "dom_vs_dom" in similarity_results:
            dati = similarity_results["dom_vs_dom"]
            similarity.show_heatmap(
                parent,
                "Domini personali vs domini compagni",
                dati["rows"],
                dati["cols"],
                dati["matrix"],
            )

        if "test_vs_dom" in similarity_results:
            dati = similarity_results["test_vs_dom"]
            similarity.show_heatmap(
                parent,
                "Verifiche vs domini (di tutti)",
                dati["rows"],
                dati["cols"],
                dati["matrix"],
            )

    # ==================================================================
    # COLLEGAMENTO PULSANTI
    # ==================================================================
    btn_scarica.configure(command=scarica_tutti)
    btn_analizza.configure(command=analizza_somiglianze)
    btn_mappa.configure(command=mostra_mappa)

    # ==================================================================
    # AVVIO DEL PROCESSORE DELLA CODA DI AGGIORNAMENTI
    # ==================================================================
    process_update_queue()

    # ==================================================================
    # LAYOUT ELASTICO DELLA FRAME
    # ==================================================================
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(5, weight=1)

    log("Frame domini attivo. In attesa di caricamento CSV...")

    return frame
