import os
import csv
import queue
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Moduli progetto
import similarity_ftp       # analisi/heatmap (merge domini già gestito qui)
import ftpAgent             # tutta la logica FTP è spostata qui


YELLOW_BG = "#85187c"


# ======================================================================
# UTILITÀ LOCALI (solo GUI/logica associazione; nessun download qui)
# ======================================================================

def format_bytes(num_bytes):
    """
    Converte un numero di byte in formato leggibile (B, KB, MB, GB, TB).
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


def _sanitize_alunno_tag(raw):
    """
    Normalizza il campo "alunno/cognome" per generare un tag di ricerca:
      - minuscolo
      - toglie dominio email
      - elimina spazi
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

        if p1 and p2:
            candidates.append(p2 + "." + p1)
            candidates.append(p1 + "." + p2)
            candidates.append(p1)
            candidates.append(p2)
    elif len(parts) == 1 and parts[0] != "":
        candidates.append(parts[0])

    visti = set()
    ordinati = []

    i = 0
    while i < len(candidates):
        c = candidates[i]

        if c and c not in visti:
            ordinati.append(c)
            visti.add(c)

        i = i + 1

    return ordinati


def _list_test_dirs(base_dir):
    """
    Restituisce l'elenco dei nomi delle sottocartelle presenti in base_dir.
    Non filtra su test01..test30 qui (lasciare più flessibile).
    """
    out = []

    if not os.path.isdir(base_dir):
        return out

    for name in os.listdir(base_dir):
        p = os.path.join(base_dir, name)
        if os.path.isdir(p):
            out.append(name)

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

    # 2) testNN- / testNN_
    i = 0
    while i < len(candidates):
        tag = candidates[i]
        pattern_dash = "-" + tag
        pattern_underscore = "_" + tag

        for low_name, original in td_low_map.items():
            if low_name.startswith("test"):
                if low_name.endswith(pattern_dash) or low_name.endswith(pattern_underscore):
                    return original

        i = i + 1

    # 3) fallback permissivo
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
      - Associa alunno → cartella test (nuovo formato + fallback)
      - Avvio download FTP (delegato a ftpAgent)
      - Tabella stato, progress, peso complessivo 00_DominiFTP
      - Analisi somiglianze (via similarity_ftp) + heatmap
      - Autoload del CSV domini (se indicato nel JSON / global_config)
    """
    frame = tk.Frame(root, bg=YELLOW_BG)

    update_queue = queue.Queue()
    similarity_results = {}

    # ------------------------------------------------------------------
    # RIGA 0: pulsanti + peso totale
    # ------------------------------------------------------------------
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

    lbl_peso_totale = tk.Label(frame, text="Totale FTP: 0 B", bg=YELLOW_BG, anchor="e")
    lbl_peso_totale.grid(row=0, column=5, padx=10, pady=6, sticky="e")

    # ------------------------------------------------------------------
    # RIGA 1: tabella
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # RIGHE 2-3: log
    # ------------------------------------------------------------------
    tk.Label(frame, text="Log eventi:", bg=YELLOW_BG).grid(
        row=2, column=0, sticky="w", padx=6, pady=6
    )

    txt_log = tk.Text(frame, height=8, width=120)
    txt_log.grid(row=3, column=0, columnspan=7, padx=10, pady=5, sticky="ew")

    def log(msg):
        txt_log.insert("end", msg + "\n")
        txt_log.see("end")

    # ------------------------------------------------------------------
    # Stato in memoria
    # ------------------------------------------------------------------
    credenziali_by_item = {}   # item_id -> (ftp_user, ftp_pass)
    testdir_by_item = {}       # item_id -> cartella test associata

    # ------------------------------------------------------------------
    # Helper: inferire CSV domini da global_config / directory
    # ------------------------------------------------------------------

    def guess_csv_from_config(base_dir):
        """
        Cerca di individuare automaticamente il file CSV dei domini.
        Strategia:
          1) Scansiona tutti i valori in global_config:
             - se è una stringa che finisce con .csv ⇒ candidata
             - se è una directory ⇒ cerca il CSV più recente dentro
          2) Se ancora niente, cerca CSV direttamente in base_dir.
        Restituisce:
          - path del CSV se trovato
          - stringa vuota se non trova nulla
        """
        candidates = []

        # 1) valori presenti in global_config
        for key, var in global_config.items():
            try:
                value = var
                if hasattr(value, "get"):
                    value = value.get()

                if not isinstance(value, str):
                    continue

                value = value.strip()
                if value == "":
                    continue

                # caso: path CSV
                if value.lower().endswith(".csv"):
                    if os.path.isabs(value):
                        candidates.append(value)
                    else:
                        candidates.append(os.path.join(base_dir, value))
                    continue

                # caso: directory che potrebbe contenere CSV
                if os.path.isdir(value):
                    try:
                        entries = os.listdir(value)
                    except Exception:
                        entries = []

                    inner = []
                    j = 0
                    while j < len(entries):
                        nome = entries[j]
                        if nome.lower().endswith(".csv"):
                            path_csv = os.path.join(value, nome)
                            try:
                                ts = os.path.getmtime(path_csv)
                            except Exception:
                                ts = 0
                            inner.append((ts, path_csv))
                        j = j + 1

                    if len(inner) > 0:
                        inner.sort(reverse=True)
                        candidates.append(inner[0][1])
            except Exception:
                # se qualche chiave dà problemi, la ignoriamo
                pass

        # 2) CSV direttamente in base_dir
        if os.path.isdir(base_dir):
            try:
                voci = os.listdir(base_dir)
            except Exception:
                voci = []

            j = 0
            while j < len(voci):
                nome = voci[j]
                if nome.lower().endswith(".csv"):
                    candidates.append(os.path.join(base_dir, nome))
                j = j + 1

        # normalizza: tiene solo file esistenti, rimuove duplicati
        valid = []
        visti = set()

        i = 0
        while i < len(candidates):
            path = os.path.abspath(candidates[i])
            if os.path.isfile(path):
                if path not in visti:
                    valid.append(path)
                    visti.add(path)
            i = i + 1

        if len(valid) == 0:
            return ""

        # Per ora prendiamo il primo (in futuro: si può aggiungere più logica)
        return valid[0]

    # ------------------------------------------------------------------
    # Crea modello CSV
    # ------------------------------------------------------------------

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

        # Prova a inferire cognomi/tag dalle cartelle locali
        cognomi = []

        if os.path.isdir(base_dir):
            elementi = os.listdir(base_dir)
            j = 0
            while j < len(elementi):
                nome_dir = elementi[j]
                percorso_dir = os.path.join(base_dir, nome_dir)

                if os.path.isdir(percorso_dir) and "test" in nome_dir.lower():
                    if "-" in nome_dir:
                        parti = nome_dir.split("-", 1)
                        if len(parti) == 2:
                            tag = parti[1].strip().lower()
                            if tag:
                                cognomi.append(tag)
                    elif "_" in nome_dir:
                        parti = nome_dir.split("_", 1)
                        if len(parti) == 2:
                            tag = parti[1].strip().lower()
                            if tag:
                                cognomi.append(tag)

                j = j + 1

        try:
            with open(percorso_csv, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["cognome", "dominio", "ftp_user", "ftp_password"])

                inseriti = sorted(set(cognomi))
                k = 0
                while k < len(inseriti):
                    writer.writerow([inseriti[k], "", "", ""])
                    k = k + 1

            log("Modello CSV creato in: " + percorso_csv)

            if len(cognomi) > 0:
                log(
                    "Inseriti automaticamente {} nominativi (da nomi cartella).".format(
                        len(set(cognomi))
                    )
                )
            else:
                log("Nessuna cartella utile trovata: modello creato con sole intestazioni.")
        except Exception as e:
            messagebox.showerror(
                "Errore",
                "Errore nella creazione del modello CSV:\n" + str(e),
            )

    btn_modello.configure(command=crea_modello_csv)

    # ------------------------------------------------------------------
    # Logica di caricamento CSV (estratta in una funzione dedicata)
    # ------------------------------------------------------------------

    def _load_domains_csv(percorso_csv):
        """
        Effettua il vero caricamento del CSV:
          - svuota la tabella
          - popola righe, credenziali_by_item, testdir_by_item
          - abilita il bottone Scarica se ci sono righe valide
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
                "Seleziona prima la directory principale delle prove.",
            )
            return

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
            cognome = cognome.strip().lower()

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
                cognome,          # Alunno/tag
                dominio,          # Dominio
                stato_iniziale,   # Stato
                "0%",             # Avanzamento
                "0",              # N. file
                "",               # Elenco file
                "0 B",            # Peso cartella
                "",               # Ultima modifica
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

    # ------------------------------------------------------------------
    # Carica CSV (manuale, tramite file dialog)
    # ------------------------------------------------------------------

    def carica_csv():
        base_dir = global_config["selected_directory"].get().strip()

        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove.",
            )
            return

        percorso_csv = filedialog.askopenfilename(
            title="Seleziona file CSV con domini",
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
        )

        if not percorso_csv:
            return

        log("CSV selezionato manualmente: " + percorso_csv)
        _load_domains_csv(percorso_csv)

    btn_carica.configure(command=carica_csv)

    # ------------------------------------------------------------------
    # Peso totale 00_DominiFTP
    # ------------------------------------------------------------------

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

        lbl_peso_totale.config(text="Totale FTP: " + format_bytes(totale))

    # ------------------------------------------------------------------
    # Servizio coda (thread-safe GUI)
    # ------------------------------------------------------------------

    def process_update_queue():
        try:
            while True:
                task = update_queue.get_nowait()
                tipo = task[0]

                if tipo == "log":
                    log(task[1])

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

    # ------------------------------------------------------------------
    # Avvio download: delega a ftpAgent
    # ------------------------------------------------------------------

    def scarica_tutti():
        base_dir = global_config["selected_directory"].get().strip()

        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove.",
            )
            return

        items = tree.get_children()

        if not items:
            messagebox.showwarning(
                "Attenzione",
                "Nessun dominio da scaricare. Carica prima il CSV.",
            )
            return

        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_mappa.configure(state="disabled")
        similarity_results.clear()

        # Costruzione jobs (un job per riga)
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

        # Delega completa al modulo esterno
        ftpAgent.start_batch_download(jobs, base_dir, update_queue)

    # ------------------------------------------------------------------
    # Analisi somiglianze (verifica vs MERGE dominio)
    # ------------------------------------------------------------------

    def analizza_somiglianze():
        base_dir = global_config["selected_directory"].get().strip()

        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove.",
            )
            return

        dir_ftp_base = os.path.join(base_dir, "00_DominiFTP")

        if not os.path.isdir(dir_ftp_base):
            messagebox.showwarning(
                "Attenzione",
                "La directory 00_DominiFTP non esiste. Esegui prima il download.",
            )
            return

        tests_dirs = {}
        domini_dirs = {}

        items = tree.get_children()
        i = 0

        while i < len(items):
            item_id = items[i]
            valori = list(tree.item(item_id, "values"))
            alunno = valori[0]

            if alunno:
                nome_cartella_test = testdir_by_item.get(item_id, "")

                if nome_cartella_test:
                    percorso_test = os.path.join(base_dir, nome_cartella_test)
                    if os.path.isdir(percorso_test):
                        tests_dirs[alunno] = percorso_test

                per_dom = os.path.join(dir_ftp_base, alunno)
                if os.path.isdir(per_dom):
                    domini_dirs[alunno] = per_dom

            i = i + 1

        estensioni = (".php", ".html", ".htm", ".css", ".js", ".txt")

        # Callback di progresso per scrivere nel log
        def progress_cb(phase, current, total, name):
            if total <= 0:
                percent = 0
            else:
                percent = int(round((current * 100.0) / float(total)))

            if phase == "read_tests":
                log(
                    "Lettura verifiche: {} / {} ({}%) → '{}'".format(
                        current, total, percent, name
                    )
                )
            elif phase == "merge_domains":
                log(
                    "Merge domini: {} / {} ({}%) → '{}'".format(
                        current, total, percent, name
                    )
                )
            elif phase == "compare":
                log(
                    "Confronto verifica↔dominio: {} / {} ({}%) → '{}'".format(
                        current, total, percent, name
                    )
                )
            else:
                log(
                    "Fase {}: {} / {} ({}%) → '{}'".format(
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

        similarity_results.clear()

        if len(students_in_test) >= 2:
            matrice_test_test = similarity_ftp.build_similarity_matrix(
                students_in_test,
                texts_test,
            )
            similarity_results["test_vs_test"] = {
                "rows": students_in_test,
                "cols": students_in_test,
                "matrix": matrice_test_test,
            }

        if len(students_in_domain) >= 2:
            matrice_dom_dom = similarity_ftp.build_similarity_matrix(
                students_in_domain,
                merged_domain_texts,
            )
            similarity_results["dom_vs_dom"] = {
                "rows": students_in_domain,
                "cols": students_in_domain,
                "matrix": matrice_dom_dom,
            }

        if len(students_in_test) >= 1 and len(students_in_domain) >= 1:
            matrice_test_dom = similarity_ftp.build_cross_similarity_matrix(
                students_in_test,
                students_in_domain,
                texts_test,
                merged_domain_texts,
            )
            similarity_results["test_vs_dom"] = {
                "rows": students_in_test,
                "cols": students_in_domain,
                "matrix": matrice_test_dom,
            }

        log("=== Analisi somiglianze: riepilogo per studente ===")

        nomi = sorted(list(metrics_by_student.keys()))

        if len(nomi) == 0:
            log("Nessun alunno con verifica e dominio disponibili per il confronto.")
        else:
            soglia_avviso = 60.0
            soglia_allerta = 80.0

            i = 0
            while i < len(nomi):
                nome = nomi[i]
                m = metrics_by_student[nome]

                sim_globale = m.get("similarity_percent", 0.0)
                shared_lines = m.get("shared_lines_count", 0)
                shared_chars = m.get("shared_chars_len", 0)
                perc_shared_chars = m.get("percent_shared_chars_on_test", 0.0)
                total_lines_test = m.get("total_lines_test", 0)
                total_chars_test = m.get("total_chars_test", 0)

                log(
                    "{} -> Similarità globale: {:.1f}% | Righe condivise: {} (su {}) | "
                    "Caratteri condivisi: {} | Copertura su verifica: {:.1f}% ({} char)".format(
                        nome,
                        sim_globale,
                        shared_lines,
                        total_lines_test,
                        shared_chars,
                        perc_shared_chars,
                        total_chars_test,
                    )
                )

                if perc_shared_chars >= soglia_allerta or sim_globale >= soglia_allerta:
                    log("  ⚠ Valore alto: verificare possibile riuso intenso del codice online.")
                elif perc_shared_chars >= soglia_avviso or sim_globale >= soglia_avviso:
                    log("  ℹ Valore moderato: possibile riuso parziale.")

                i = i + 1

        if similarity_results:
            btn_mappa.configure(state="normal")
            log("=== Analisi completata. Puoi aprire la mappa delle similitudini. ===")
        else:
            btn_mappa.configure(state="disabled")
            log("Nessuna matrice di similarità calcolabile con i dati correnti.")

    # ------------------------------------------------------------------
    # Mappa similitudini
    # ------------------------------------------------------------------

    def mostra_mappa():
        if not similarity_results:
            messagebox.showinfo(
                "Informazione",
                "Non ci sono risultati da visualizzare. Esegui prima l'analisi.",
            )
            return

        if "test_vs_test" in similarity_results:
            d = similarity_results["test_vs_test"]
            similarity_ftp.show_heatmap(
                frame,
                "Verifica vs verifiche compagni",
                d["rows"],
                d["cols"],
                d["matrix"],
            )

        if "dom_vs_dom" in similarity_results:
            d = similarity_results["dom_vs_dom"]
            similarity_ftp.show_heatmap(
                frame,
                "Domini personali (MERGE) vs domini compagni (MERGE)",
                d["rows"],
                d["cols"],
                d["matrix"],
            )

        if "test_vs_dom" in similarity_results:
            d = similarity_results["test_vs_dom"]
            similarity_ftp.show_heatmap(
                frame,
                "Verifiche vs domini (MERGE)",
                d["rows"],
                d["cols"],
                d["matrix"],
            )

    # ------------------------------------------------------------------
    # Bind pulsanti e avvio servizio coda
    # ------------------------------------------------------------------

    btn_scarica.configure(command=scarica_tutti)
    btn_analizza.configure(command=analizza_somiglianze)
    btn_mappa.configure(command=mostra_mappa)

    def process_update_queue_wrapper():
        process_update_queue()

    frame.after(100, process_update_queue_wrapper)

    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(5, weight=1)

    log("Frame domini attivo. In attesa di caricamento CSV...")

        # ------------------------------------------------------------------
    # AUTOLOAD CSV DOMINI da global_config["domains_csv_path"] o dal JSON
    # ------------------------------------------------------------------
    def try_autoload_csv():
        """
        Se possibile, carica automaticamente il CSV dei domini.

        Priorità:
          1) global_config["domains_csv_path"] (se non vuota)
          2) campo "domains_csv_path" nel file JSON di configurazione
             (es. SMX.json nella directory selezionata)
        """
        path_csv = ""

        # 1) Prova da global_config["domains_csv_path"]
        value = None
        try:
            if "domains_csv_path" in global_config:
                value = global_config["domains_csv_path"]
        except Exception:
            value = None

        if value is not None:
            try:
                if hasattr(value, "get"):
                    value = value.get()
            except Exception:
                value = str(value)

            if not isinstance(value, str):
                value = str(value)

            tmp = value.strip()
            if tmp != "":
                path_csv = tmp

        # 2) Se ancora vuoto, prova a leggere direttamente il JSON nella dir selezionata
        base_dir = ""
        try:
            if "selected_directory" in global_config:
                sd = global_config["selected_directory"]
                if hasattr(sd, "get"):
                    base_dir = sd.get().strip()
                else:
                    base_dir = str(sd).strip()
        except Exception:
            base_dir = ""

        if path_csv == "":
            if base_dir != "" and os.path.isdir(base_dir):
                possibili_nomi = ["SMX.json", "Smx.json", "smx.json", "config.json"]
                i = 0
                while i < len(possibili_nomi) and path_csv == "":
                    nome = possibili_nomi[i]
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
                                    # esce dal ciclo possibili_nomi
                        except Exception:
                            # se qualcosa va storto su questo file, prova il prossimo
                            pass
                    i = i + 1

        # 3) Se non abbiamo trovato nulla, log e stop (nessun errore, resta il caricamento manuale)
        if path_csv == "":
            log("Autoload CSV: nessun percorso valido trovato in global_config o JSON.")
            return

        # 4) Verifica che il file esista
        if not os.path.isfile(path_csv):
            log("Autoload CSV: file indicato non trovato: " + path_csv)
            return

        # 5) Carica effettivamente il CSV
        log("Autoload CSV: caricamento automatico di: " + path_csv)
        carica_csv(path_csv)

    frame.after(300, try_autoload_csv)
    
    return frame
