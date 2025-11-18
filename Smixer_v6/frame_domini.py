import os
import csv
import re
import json
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import similarity_ftp
import ftpAgent

YELLOW_BG = "#85187c"


# ======================================================================
# UTILITÀ LOCALI
# ======================================================================

def _sanitize_alunno_tag(raw):
    """
    Normalizza il campo alunno/cognome per generare un tag di ricerca:
      - minuscolo
      - rimozione dominio email
      - rimozione spazi
    """
    if raw is None:
        return ""

    s = str(raw).strip().lower()

    if "@" in s:
        parti = s.split("@", 1)
        s = parti[0]

    s = s.replace(" ", "")
    return s


def _derive_candidate_tags(raw):
    """
    A partire da "cognome" o email genera possibili tag:
      - base
      - combinazioni nome.cognome / cognome.nome
      - solo prima o seconda parte
    """
    base = _sanitize_alunno_tag(raw)
    candidates = []

    if base != "":
        candidates.append(base)

    parts = re.split(r"[._]+", base)

    if len(parts) >= 2:
        p1 = parts[0]
        p2 = parts[1]

        if p1 != "" and p2 != "":
            candidates.append(p1 + "." + p2)
            candidates.append(p2 + "." + p1)
            candidates.append(p1)
            candidates.append(p2)
    elif len(parts) == 1 and parts[0] != "":
        candidates.append(parts[0])

    visti = set()
    ordinati = []

    i = 0
    while i < len(candidates):
        c = candidates[i]
        if c != "" and c not in visti:
            ordinati.append(c)
            visti.add(c)
        i = i + 1

    return ordinati


def _list_test_dirs(base_dir):
    """
    Restituisce l'elenco delle sottocartelle presenti in base_dir.
    """
    out = []

    if not os.path.isdir(base_dir):
        return out

    nomi = os.listdir(base_dir)
    i = 0
    while i < len(nomi):
        nome = nomi[i]
        percorso = os.path.join(base_dir, nome)
        if os.path.isdir(percorso):
            out.append(nome)
        i = i + 1

    return out


def _match_test_dir(test_dirs, alunno_raw):
    """
    Cerca di associare l'alunno a una cartella test esistente.

    Logica (in ordine):
      1) <tag>__testNN
      2) testNN-<tag> oppure testNN_<tag>
      3) qualunque nome che contenga "test" e il tag
    """
    if not test_dirs:
        return ""

    td_low_map = {}
    i = 0
    while i < len(test_dirs):
        d = test_dirs[i]
        td_low_map[d.lower()] = d
        i = i + 1

    candidates = _derive_candidate_tags(alunno_raw)

    # 1) <tag>__testNN
    i = 0
    while i < len(candidates):
        tag = candidates[i]
        prefix = tag + "__test"

        for low_name, original in td_low_map.items():
            if low_name.startswith(prefix):
                return original

        i = i + 1

    # 2) testNN-<tag> oppure testNN_<tag>
    i = 0
    while i < len(candidates):
        tag = candidates[i]
        pattern_dash = "test" + tag
        pattern_underscore = "test" + tag

        for low_name, original in td_low_map.items():
            if low_name.endswith(pattern_dash) or low_name.endswith(pattern_underscore):
                return original

        i = i + 1

    # 3) Fallback permissivo: qualunque nome che contenga "test" e il tag
    i = 0
    while i < len(candidates):
        tag = candidates[i]
        for low_name, original in td_low_map.items():
            if "test" in low_name and tag in low_name:
                return original
        i = i + 1

    return ""


# ======================================================================
# FRAME PRINCIPALE
# ======================================================================

def create_frame_domini(root, global_config):
    """
    Gestione Domini:
      - Crea/carica CSV
      - Autoload CSV se domains_csv_path è valorizzato
      - Associa alunno → cartella test
      - Download FTP (ftpAgent) usando SOLO dati del CSV
      - Analisi somiglianze (similarity_ftp)
      - Finestra riepilogo per tutti gli alunni
    """
    frame = tk.Frame(root, bg=YELLOW_BG)

    update_queue = queue.Queue()

    metrics_by_student_cache = {}
    texts_test_cache = {}
    merged_domain_texts_cache = {}
    students_in_test_cache = []
    students_in_domain_cache = []

    # ==================================================================
    # TABELLA
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

    i = 0
    while i < len(colonne):
        col = colonne[i]
        tree.heading(col, text=col)

        if col == "Alunno":
            tree.column(col, width=140, anchor="center")
        elif col == "Dominio":
            tree.column(col, width=200, anchor="center")
        elif col == "Stato":
            tree.column(col, width=260, anchor="w")
        elif col == "Elenco file":
            tree.column(col, width=320, anchor="w")
        else:
            tree.column(col, width=120, anchor="center")

        i = i + 1

    tree.grid(row=1, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")

    scrollbar_vert = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_vert.set)
    scrollbar_vert.grid(row=1, column=6, sticky="ns")

    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(5, weight=1)

    # ==================================================================
    # LOG
    # ==================================================================
    txt_log = tk.Text(frame, height=8, width=120)
    txt_log.grid(row=3, column=0, columnspan=7, padx=10, pady=5, sticky="ew")

    def log(msg):
        txt_log.insert("end", msg + "\n")
        txt_log.see("end")

    # ------------------------------------------------------------------
    # Stato per riga
    # ------------------------------------------------------------------
    credenziali_by_item = {}   # item_id -> (ftp_user, ftp_pass)
    testdir_by_item = {}       # item_id -> cartella test associata

    # ==================================================================
    # SEZIONE: MODELLO CSV
    # ==================================================================
    def crea_modello_csv():
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

        test_dirs = _list_test_dirs(base_dir)

        cognomi = set()
        i = 0
        while i < len(test_dirs):
            nome = test_dirs[i]
            tag = nome

            if "__test" in nome.lower():
                parti = nome.split("__test", 1)
                tag = parti[0]

            tag_norm = _sanitize_alunno_tag(tag)
            if tag_norm != "":
                cognomi.add(tag_norm)
            i = i + 1

        try:
            with open(percorso_csv, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["cognome", "dominio", "ftp_user", "ftp_password"])

                visti = set()
                cognomi_ordinati = sorted(cognomi)

                j = 0
                while j < len(cognomi_ordinati):
                    c = cognomi_ordinati[j]
                    if c not in visti:
                        writer.writerow([c, "", "", ""])
                        visti.add(c)
                    j = j + 1

            log("Modello CSV creato in: " + percorso_csv)
        except Exception as e:
            messagebox.showerror(
                "Errore",
                "Errore nella creazione del CSV:\n" + str(e),
            )

    # ==================================================================
    # SEZIONE: CARICAMENTO CSV (manuale / automatico)
    # ==================================================================
    def carica_csv(percorso_csv=None):
        """
        Se percorso_csv è None:
          - apre il file dialog per scegliere il CSV.
        Se percorso_csv è una stringa valida:
          - lo usa direttamente (autoload da domains_csv_path o JSON).
        """
        for item in tree.get_children():
            tree.delete(item)

        credenziali_by_item.clear()
        testdir_by_item.clear()

        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_mappa.configure(state="disabled")

        metrics_by_student_cache.clear()
        texts_test_cache.clear()
        merged_domain_texts_cache.clear()
        del students_in_test_cache[:]
        del students_in_domain_cache[:]

        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove.",
            )
            return

        if percorso_csv is None:
            percorso_csv = filedialog.askopenfilename(
                title="Seleziona file CSV con domini",
                filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
            )
            if not percorso_csv:
                return
            log("CSV selezionato manualmente: " + percorso_csv)
        else:
            log("CSV indicato da configurazione: " + str(percorso_csv))

        test_dirs = _list_test_dirs(base_dir)
        log(
            "Trovate {} cartelle (candidate test) nella directory selezionata.".format(
                len(test_dirs)
            )
        )

        try:
            with open(percorso_csv, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                righe = list(reader)
        except Exception as e:
            messagebox.showerror(
                "Errore",
                "Errore nella lettura del CSV:\n" + str(e),
            )
            return

        if not righe:
            messagebox.showwarning(
                "Attenzione",
                "Il CSV selezionato non contiene righe.",
            )
            return

        righe_inserite = 0

        i = 0
        while i < len(righe):
            row = righe[i]

            cognome = row.get("cognome", "")
            if cognome is None:
                cognome = ""
            cognome = str(cognome).strip().lower()

            dominio = row.get("dominio", "")
            if dominio is None:
                dominio = ""
            dominio = dominio.strip()

            ftp_user = row.get("ftp_user", "")
            if ftp_user is None:
                ftp_user = ""
            ftp_user = ftp_user.strip()

            ftp_pass = row.get("ftp_password", "")
            if ftp_pass is None:
                ftp_pass = ""
            ftp_pass = ftp_pass.strip()

            if cognome == "" and dominio == "":
                i = i + 1
                continue

            found_test = _match_test_dir(test_dirs, cognome)

            if found_test != "":
                stato_iniziale = "Test OK"
            else:
                stato_iniziale = "Test non trovato"

            valori = (
                cognome,
                dominio,
                stato_iniziale,
                "0%",
                "0",
                "",
                "0 B",
                "",
            )

            item_id = tree.insert("", "end", values=valori)
            credenziali_by_item[item_id] = (ftp_user, ftp_pass)
            testdir_by_item[item_id] = found_test

            righe_inserite = righe_inserite + 1
            i = i + 1

        log(
            "File CSV '{}' caricato. Righe valide: {}".format(
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
            messagebox.showwarning(
                "Attenzione",
                "Nessuna riga valida trovata nel CSV.",
            )

    def carica_csv_dialog():
        carica_csv(None)

    # ==================================================================
    # SEZIONE: DOWNLOAD FTP
    # ==================================================================
    def scarica_tutti_domini_ftp():
        """
        Prepara i job e avvia ftpAgent.start_batch_download
        usando SOLO i dati del CSV (dominio, ftp_user, ftp_password).
        """
        items = tree.get_children()
        if not items:
            messagebox.showwarning(
                "Attenzione",
                "Nessun dominio in tabella. Carica prima un CSV.",
            )
            return

        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove.",
            )
            return

        jobs = []

        i = 0
        while i < len(items):
            item_id = items[i]
            valori_corr = list(tree.item(item_id, "values"))

            alunno = valori_corr[0]
            dominio = valori_corr[1]
            stato_base = valori_corr[2]

            cred = credenziali_by_item.get(item_id, ("", ""))
            ftp_user = cred[0]
            ftp_pass = cred[1]

            if dominio == "" or ftp_user == "" or ftp_pass == "":
                tree.set(item_id, "Stato", "Dati FTP incompleti")
                i = i + 1
                continue

            job = {
                "item_id": item_id,
                "alunno": alunno,
                "dominio": dominio,
                "stato_base": stato_base,
                "ftp_user": ftp_user,
                "ftp_pass": ftp_pass,
            }
            jobs.append(job)
            i = i + 1

        if not jobs:
            messagebox.showwarning(
                "Attenzione",
                "Nessun job FTP con credenziali complete.",
            )
            return

        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_mappa.configure(state="disabled")

        ftpAgent.start_batch_download(jobs, base_dir, update_queue)

    # ==================================================================
    # SEZIONE: AGGIORNAMENTO DA update_queue
    # ==================================================================
    def process_update_queue():
        """
        Elabora i messaggi provenienti da ftpAgent.
        """
        while True:
            try:
                msg = update_queue.get_nowait()
            except queue.Empty:
                break

            tipo = msg[0]

            if tipo == "log":
                log(msg[1])
            elif tipo == "set":
                item_id = msg[1]
                colonna = msg[2]
                valore = msg[3]
                if item_id in tree.get_children():
                    tree.set(item_id, colonna, valore)
            elif tipo == "fine_download":
                log("=== Download FTP completato ===")
                btn_scarica.configure(state="normal")
                btn_analizza.configure(state="normal")
                btn_mappa.configure(state="normal")

        frame.after(200, process_update_queue)

    # ==================================================================
    # SEZIONE: ANALISI SOMIGLIANZE
    # ==================================================================
    def analizza_somiglianze():
        """
        Costruisce le mappe:
            - tests_dirs:   studente -> cartella test locale
            - domini_dirs:  studente -> cartella dominio scaricato (00_DominiFTP)
            e lancia similarity_ftp.analyze_reuse_by_student.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove.",
            )
            return

        # Cartelle locali con i domini scaricati
        dir_ftp = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp):
            messagebox.showwarning(
                "Attenzione",
                "Nessuna cartella 00_DominiFTP trovata.\nEsegui prima il download dei domini.",
            )
            return

        # ------------------------------------------------------------
        # Costruzione dizionari tests_dirs e domini_dirs
        # chiave: alunno (cognome normalizzato come in tabella)
        # ------------------------------------------------------------
        tests_dirs = {}
        domini_dirs = {}

        items = tree.get_children()
        indice = 0
        while indice < len(items):
            item_id = items[indice]
            valori = list(tree.item(item_id, "values"))

            if len(valori) >= 3:
                alunno = valori[0]
                test_dir_name = testdir_by_item.get(item_id, "")

                if alunno is None:
                    alunno = ""
                alunno = str(alunno).strip().lower()

                if test_dir_name is None:
                    test_dir_name = ""
                test_dir_name = str(test_dir_name).strip()

                # cartella test associata (es. "alberti.gabriel2006__test01")
                if alunno != "" and test_dir_name != "":
                    path_test = os.path.join(base_dir, test_dir_name)
                    if os.path.isdir(path_test):
                        tests_dirs[alunno] = path_test

                # cartella dominio scaricato: 00_DominiFTP/<alunno>
                if alunno != "":
                    path_dom = os.path.join(dir_ftp, alunno)
                    if os.path.isdir(path_dom):
                        domini_dirs[alunno] = path_dom

            indice = indice + 1

        if not tests_dirs:
            messagebox.showwarning(
                "Attenzione",
                "Nessuna cartella test valida trovata.\nControlla le associazioni alunno/test.",
            )
            return

        if not domini_dirs:
            messagebox.showwarning(
                "Attenzione",
                "Nessuna cartella dominio valida trovata in 00_DominiFTP.",
            )
            return

        # Estensioni di interesse per il confronto
        estensioni = [".php", ".html", ".css", ".js"]

        def progress_cb(phase, current, total, name):
            if total <= 0:
                percent = 0
            else:
                percent = int((current * 100) / total)
            log(
                "Progresso {}: {}/{} ({}%) → '{}'".format(
                    str(phase), current, total, percent, name
                )
            )

        log("=== Avvio analisi somiglianze (verifica vs MERGE dominio) ===")

        (
            metrics_by_student,
            students_in_test,
            students_in_domain,
            texts_test,
            merged_domain_texts,
        ) = similarity_ftp.analyze_reuse_by_student(
            tests_dirs,
            domini_dirs,
            estensioni,
            progress_cb,
        )

        # Salvataggio nei cache locali
        metrics_by_student_cache.clear()
        metrics_by_student_cache.update(metrics_by_student)

        texts_test_cache.clear()
        texts_test_cache.update(texts_test)

        merged_domain_texts_cache.clear()
        merged_domain_texts_cache.update(merged_domain_texts)

        del students_in_test_cache[:]
        students_in_test_cache.extend(students_in_test)

        del students_in_domain_cache[:]
        students_in_domain_cache.extend(students_in_domain)

        btn_mappa.configure(state="normal")
        btn_analizza.configure(state="normal")

        log("=== Analisi somiglianze completata ===")


    # ==================================================================
    # SEZIONE: MAPPA SIMILITUDINI
    # ==================================================================
    def mostra_mappa():
        """
        Mostra una finestra con la mappa delle similitudini e comandi avanzati.
        """
        if not metrics_by_student_cache:
            messagebox.showwarning(
                "Attenzione",
                "Nessuna analisi disponibile.\nEsegui prima 'Analizza somiglianze'.",
            )
            return

        top = tk.Toplevel(frame)
        top.title("Mappa similitudini domini")

        cols = ("Studente", "Sim. globale", "Righe condivise", "Chars condivisi", "% su test")
        tv = ttk.Treeview(top, columns=cols, show="headings", height=20)

        i = 0
        while i < len(cols):
            c = cols[i]
            tv.heading(c, text=c)
            if c == "Studente":
                tv.column(c, width=200, anchor="w")
            else:
                tv.column(c, width=120, anchor="center")
            i = i + 1

        tv.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

        scrollbar = ttk.Scrollbar(top, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=4, sticky="ns")

        top.grid_rowconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)

        nomi = sorted(metrics_by_student_cache.keys())

        if not nomi:
            messagebox.showwarning(
                "Attenzione",
                "Nessuna metrica disponibile da visualizzare.",
            )
            top.destroy()
            return

        soglia_avviso = 60.0
        soglia_allerta = 80.0

        i = 0
        while i < len(nomi):
            nome = nomi[i]
            m = metrics_by_student_cache[nome]

            sim_globale = float(m.get("similarity_percent", 0.0))
            shared_lines = int(m.get("shared_lines_count", 0))
            shared_chars = int(m.get("shared_chars_len", 0))
            perc_shared_chars = float(m.get("percent_shared_chars_on_test", 0.0))

            tv.insert(
                "",
                "end",
                values=(
                    nome,
                    "{:.1f}%".format(sim_globale),
                    str(shared_lines),
                    str(shared_chars),
                    "{:.1f}%".format(perc_shared_chars),
                ),
            )
            i = i + 1

        btn_chiudi = tk.Button(top, text="Chiudi", command=top.destroy)
        btn_chiudi.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        btn_heatmap = tk.Button(
            top,
            text="Heatmap globale",
            command=lambda: similarity_ftp.show_heatmap(
                metrics_by_student_cache,
                texts_test_cache,
                merged_domain_texts_cache,
            ),
        )
        btn_heatmap.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    # ==================================================================
    # BOTTONI PRINCIPALI
    # ==================================================================
    btn_modello = tk.Button(frame, text="Crea modello CSV", width=20, command=crea_modello_csv)
    btn_modello.grid(row=0, column=0, padx=6, pady=6, sticky="w")

    btn_carica = tk.Button(frame, text="Carica file domini (CSV)", width=24)
    btn_carica.grid(row=0, column=1, padx=6, pady=6, sticky="w")

    btn_scarica = tk.Button(
        frame,
        text="Scarica tutti i domini via FTP",
        width=24,
        state="disabled",
        command=scarica_tutti_domini_ftp,
    )
    btn_scarica.grid(row=0, column=2, padx=6, pady=6, sticky="w")

    btn_analizza = tk.Button(
        frame,
        text="Analizza somiglianze",
        width=24,
        state="disabled",
        command=analizza_somiglianze,
    )
    btn_analizza.grid(row=0, column=3, padx=6, pady=6, sticky="w")

    btn_mappa = tk.Button(
        frame,
        text="Mostra mappa similitudini",
        width=24,
        state="disabled",
        command=mostra_mappa,
    )
    btn_mappa.grid(row=0, column=4, padx=6, pady=6, sticky="w")

    lbl_peso_totale = tk.Label(frame, text="Totale FTP: 0 B", bg=YELLOW_BG, fg="white")
    lbl_peso_totale.grid(row=0, column=5, padx=10, pady=6, sticky="e")

    btn_carica.configure(command=carica_csv_dialog)

    # ==================================================================
    # AGGIORNAMENTO PERIODICO (QUEUE + PESO FTP)
    # ==================================================================
    def aggiorna_peso_totale_ftp():
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
            j = 0
            while j < len(files):
                percorso_file = os.path.join(radice, files[j])
                try:
                    totale = totale + os.path.getsize(percorso_file)
                except Exception:
                    pass
                j = j + 1

        if totale < 1024:
            testo = "{} B".format(totale)
        else:
            kb = float(totale) / 1024.0
            if kb < 1024:
                testo = "{:.1f} KB".format(kb)
            else:
                mb = kb / 1024.0
                testo = "{:.2f} MB".format(mb)

        lbl_peso_totale.config(text="Totale FTP: " + testo)

    def tick():
        process_update_queue()
        aggiorna_peso_totale_ftp()
        frame.after(1000, tick)

    frame.after(200, tick)

    # ==================================================================
    # AUTOLOAD CSV DALLA CONFIGURAZIONE
    # ==================================================================
    log("Frame domini attivo. In attesa di caricamento CSV...")

    def try_autoload_csv():
        """
        Se nel JSON o in global_config è presente domains_csv_path valido, carica il CSV.
        """
        path_csv = ""

        value = None
        try:
            if "domains_csv_path" in global_config:
                value = global_config["domains_csv_path"]
        except Exception:
            value = None

        if value is not None:
            if hasattr(value, "get"):
                try:
                    value = value.get()
                except Exception:
                    value = str(value)
            if not isinstance(value, str):
                value = str(value)
            tmp = value.strip()
            if tmp != "":
                path_csv = tmp

        base_dir = ""
        try:
            sd = global_config.get("selected_directory")
            if sd is not None and hasattr(sd, "get"):
                base_dir = sd.get().strip()
        except Exception:
            base_dir = ""

        if path_csv == "" and base_dir != "" and os.path.isdir(base_dir):
            possibili = ["SMX.json", "Smx.json", "smx.json", "config.json"]
            idx = 0
            while idx < len(possibili) and path_csv == "":
                nome = possibili[idx]
                json_path = os.path.join(base_dir, nome)
                if os.path.isfile(json_path):
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        candidate = data.get("domains_csv_path", "")
                        if isinstance(candidate, str):
                            candidate = candidate.strip()
                            if candidate != "":
                                path_csv = candidate
                    except Exception:
                        pass
                idx = idx + 1

        if path_csv == "":
            log("Autoload CSV: nessun percorso valido trovato in global_config o JSON.")
            return

        if not os.path.isfile(path_csv):
            log("Autoload CSV: file indicato non trovato: " + path_csv)
            return

        log("Autoload CSV: caricamento automatico di: " + path_csv)
        carica_csv(path_csv)

    frame.after(300, try_autoload_csv)

    return frame
