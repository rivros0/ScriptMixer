import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import threading
import queue
from ftplib import FTP
from datetime import datetime

# Nuovo modulo dedicato all'analisi dei contenuti FTP e confronto con verifiche
import similarity_ftp

YELLOW_BG = "#85187c"


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
    - Analisi delle somiglianze e mappa delle similitudini (via similarity_ftp)
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
        bg=YELLOW_BG,
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
        Avvia in parallelo i download FTP per tutte le righe della tabella.
        Aggiornamenti GUI veicolati tramite coda (thread-safe).
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

        # Preparazione job
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
            Thread worker per un singolo dominio: connessione FTP, download, aggiornamenti GUI.
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

            # reset campi di avanzamento
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
                update_queue.put(("log", "❌ Credenziali mancanti per '{}' ({}).".format(alunno, dominio)))
                update_queue.put(("set", item_id, "Stato", "Errore: credenziali mancanti"))
                return

            update_queue.put(("log", "Connessione a {} per '{}'...".format(host, alunno)))

            try:
                ftp = FTP(host, timeout=30, encoding="latin-1")
                ftp.login(user=ftp_user, passwd=ftp_pass)
                update_queue.put(("set", item_id, "Stato", stato_base + " / Login OK"))
                update_queue.put(("log", "✅ Login riuscito su {} per '{}'".format(host, alunno)))
            except Exception as e:
                update_queue.put(("set", item_id, "Stato", "Errore login FTP"))
                update_queue.put(("log", "❌ Errore di connessione/login {} per '{}': {}".format(host, alunno, e)))
                return

            nome_cartella_alunno = alunno if alunno else "sconosciuto"
            dir_ftp_base_local = os.path.join(base_dir, "00_DominiFTP")
            dir_locale_alunno = os.path.join(dir_ftp_base_local, nome_cartella_alunno)
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
                update_queue.put(("set", item_id, "Stato", stato_base + " / Nessun file remoto"))
                update_queue.put(("log", "ℹ Nessun file trovato su {} per '{}'".format(dominio, alunno)))
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
                    cartella_locale_corrente = os.path.join(cartella_locale_corrente, nome_dir)
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

                update_queue.put(("set", item_id, "Avanzamento", "{}%".format(percentuale)))
                update_queue.put(("set", item_id, "N. file", str(conteggio_file)))
                update_queue.put(("set", item_id, "Peso cartella", format_bytes(peso_totale_alunno)))
                update_queue.put(("set", item_id, "Elenco file", ", ".join(elenco_file_preview)))

            try:
                ftp.quit()
            except Exception:
                pass

            if ultima_modifica is not None:
                testo_data = ultima_modifica.strftime("%Y-%m-%d %H:%M")
            else:
                testo_data = "n.d."

            update_queue.put(("set", item_id, "Ultima modifica", testo_data))
            update_queue.put(("set", item_id, "Stato", stato_base + " / Download OK"))
            update_queue.put(("log", "✅ Download completato per '{}' ({}). Ultima modifica remota: {}".format(alunno, dominio, testo_data)))

        # Avvio di tutti i worker in parallelo
        threads = []
        for job in jobs:
            t = threading.Thread(target=worker_job, args=(job,))
            t.daemon = True
            t.start()
            threads.append(t)

        def monitor_thread():
            i = 0
            while i < len(threads):
                threads[i].join()
                i = i + 1
            update_queue.put(("fine_download", None))

        monitor = threading.Thread(target=monitor_thread, daemon=True)
        monitor.start()

    # ==================================================================
    # FUNZIONE: ANALISI DELLE SOMIGLIANZE (USANDO similarity_ftp)
    # ==================================================================
    def analizza_somiglianze():
        """
        Analizza quattro casi e metriche numeriche di riuso:

        1) Verifica contro dominio personale  -> percentuali di riuso (righe condivise / righe verifica)
        2) Verifica contro verifiche compagni -> matrice test_vs_test (per heatmap)
        3) Verifica contro domini compagni    -> matrice test_vs_dom  (per heatmap)
        4) Dominio personale vs domini compagni -> matrice dom_vs_dom (per heatmap)

        Nel log: per ogni alunno con test + dominio, riepilogo numerico del riuso.
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

        # mappe {studente: directory}
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

        # Metriche numeriche di riuso per ogni alunno
        metrics_by_student, students_in_test, students_in_domain, texts_test, texts_domain = similarity_ftp.analyze_reuse_by_student(
            tests_dirs,
            domini_dirs,
            estensioni_ammesse
        )

        # Matrici per heatmap (coerenza con similarity.py)
        similarity_results.clear()

        if len(students_in_test) >= 2:
            matrice_test_test = similarity_ftp.build_similarity_matrix(students_in_test, texts_test)
            similarity_results["test_vs_test"] = {
                "rows": students_in_test,
                "cols": students_in_test,
                "matrix": matrice_test_test,
            }
        else:
            matrice_test_test = None

        if len(students_in_domain) >= 2:
            matrice_dom_dom = similarity_ftp.build_similarity_matrix(students_in_domain, texts_domain)
            similarity_results["dom_vs_dom"] = {
                "rows": students_in_domain,
                "cols": students_in_domain,
                "matrix": matrice_dom_dom,
            }
        else:
            matrice_dom_dom = None

        if len(students_in_test) >= 1 and len(students_in_domain) >= 1:
            matrice_test_dom = similarity_ftp.build_cross_similarity_matrix(
                students_in_test,
                students_in_domain,
                texts_test,
                texts_domain,
            )
            similarity_results["test_vs_dom"] = {
                "rows": students_in_test,
                "cols": students_in_domain,
                "matrix": matrice_test_dom,
            }
        else:
            matrice_test_dom = None

        # Log sintetico per alunno con metriche di riuso
        log("=== Analisi somiglianze (riuso verifica vs dominio personale) ===")
        nomi_metriche = sorted(list(metrics_by_student.keys()))
        if len(nomi_metriche) == 0:
            log("Nessun alunno con verifica e dominio disponibili per il confronto.")
        else:
            soglia_avviso = 60.0
            soglia_allerta = 80.0

            idx = 0
            while idx < len(nomi_metriche):
                nome = nomi_metriche[idx]
                m = metrics_by_student[nome]

                sim_globale = m.get("similarity_percent", 0.0)
                tot_test = m.get("total_lines_test", 0)
                tot_dom = m.get("total_lines_domain", 0)
                condivise = m.get("shared_lines_count", 0)
                reuse_test = m.get("percent_reuse_from_domain_on_test", 0.0)
                overlap_dom = m.get("percent_overlap_on_domain", 0.0)

                log(
                    "{} -> Riuso dal dominio: {:.1f}%  |  Similarità globale: {:.1f}%  |  Righe test: {}  |  Righe dominio: {}  |  Righe condivise: {}  |  Copertura su dominio: {:.1f}%".format(
                        nome, reuse_test, sim_globale, tot_test, tot_dom, condivise, overlap_dom
                    )
                )

                if reuse_test >= soglia_allerta or sim_globale >= soglia_allerta:
                    log("  ⚠ Valore alto: verificare possibile riuso intenso del codice online.")
                elif reuse_test >= soglia_avviso or sim_globale >= soglia_avviso:
                    log("  ℹ Valore moderato: possibile riuso parziale.")

                idx = idx + 1

        if not similarity_results:
            log("Nessuna matrice di similarità calcolabile con i dati correnti.")
            btn_mappa.configure(state="disabled")
        else:
            log("=== Analisi completata. È possibile visualizzare la mappa delle similitudini. ===")
            btn_mappa.configure(state="normal")

    # ==================================================================
    # FUNZIONE: MOSTRA MAPPA DELLE SIMILITUDINI (USANDO similarity_ftp)
    # ==================================================================
    def mostra_mappa():
        if not similarity_results:
            messagebox.showinfo(
                "Informazione",
                "Non ci sono risultati di similarità da visualizzare. Esegui prima l'analisi.",
            )
            return

        parent = frame

        if "test_vs_test" in similarity_results:
            dati = similarity_results["test_vs_test"]
            similarity_ftp.show_heatmap(
                parent,
                "Verifica vs verifiche compagni",
                dati["rows"],
                dati["cols"],
                dati["matrix"],
            )

        if "dom_vs_dom" in similarity_results:
            dati = similarity_results["dom_vs_dom"]
            similarity_ftp.show_heatmap(
                parent,
                "Domini personali vs domini compagni",
                dati["rows"],
                dati["cols"],
                dati["matrix"],
            )

        if "test_vs_dom" in similarity_results:
            dati = similarity_results["test_vs_dom"]
            similarity_ftp.show_heatmap(
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
