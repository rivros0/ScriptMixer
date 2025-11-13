import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import queue
import re

import similarity_ftp
import ftpAgent


YELLOW_BG = "#85187c"


# ======================================================================
# UTILITÀ LOCALI
# ======================================================================

def format_bytes(num_bytes):
    """
    Converte byte in stringa leggibile (B, KB, MB, GB, TB).
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
    Normalizza il campo "alunno/cognome" per generare tag di ricerca.
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
    A partire da "cognome" o indirizzo email genera vari tag candidati:
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
            candidates.append(p2 + "." + p1)
            candidates.append(p1 + "." + p2)
            candidates.append(p1)
            candidates.append(p2)
    elif len(parts) == 1:
        if parts[0] != "":
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

    # 2) testNN-<tag> / testNN_<tag>
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

    # 3) Fallback più permissivo: qualsiasi nome con "test" e tag
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
    Frame per la gestione dei domini Altervista degli studenti:
      - modello/caricamento CSV
      - download FTP (delegato a ftpAgent)
      - analisi somiglianze (delegata a similarity_ftp)
      - riepilogo e comparazioni avanzate on-demand
    """
    frame = tk.Frame(root, bg=YELLOW_BG)
    update_queue = queue.Queue()

    metrics_by_student_cache = {}
    texts_test_cache = {}
    merged_domain_texts_cache = {}
    students_in_test_cache = []
    students_in_domain_cache = []

    # ------------------------------------------------------------------
    # RIGA 0: pulsanti + peso complessivo FTP
    # ------------------------------------------------------------------
    btn_modello = tk.Button(frame, text="Crea modello CSV", width=18)
    btn_modello.grid(row=0, column=0, padx=6, pady=6, sticky="w")

    btn_carica = tk.Button(frame, text="Carica file domini (CSV)", width=24)
    btn_carica.grid(row=0, column=1, padx=6, pady=6, sticky="w")

    btn_scarica = tk.Button(frame, text="Scarica tutti i domini via FTP", width=24, state="disabled")
    btn_scarica.grid(row=0, column=2, padx=6, pady=6, sticky="w")

    btn_analizza = tk.Button(frame, text="Analizza somiglianze", width=24, state="disabled")
    btn_analizza.grid(row=0, column=3, padx=6, pady=6, sticky="w")

    btn_riepilogo = tk.Button(frame, text="Mostra riepilogo similitudini", width=28, state="disabled")
    btn_riepilogo.grid(row=0, column=4, padx=6, pady=6, sticky="w")

    lbl_peso_totale = tk.Label(frame, text="Totale FTP: 0 B", bg=YELLOW_BG, fg="white", anchor="e")
    lbl_peso_totale.grid(row=0, column=5, padx=10, pady=6, sticky="e")

    # ------------------------------------------------------------------
    # RIGA 1: tabella domini
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
            tree.column(col, width=220, anchor="center")
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
    tk.Label(frame, text="Log eventi:", bg=YELLOW_BG, fg="white").grid(
        row=2, column=0, sticky="w", padx=6, pady=6
    )

    txt_log = tk.Text(frame, height=8, width=120, bg="black", fg="white")
    txt_log.grid(row=3, column=0, columnspan=7, padx=10, pady=5, sticky="ew")

    def log(msg):
        txt_log.insert("end", msg + "\n")
        txt_log.see("end")

    # ------------------------------------------------------------------
    # Stato in memoria (per riga tabella)
    # ------------------------------------------------------------------
    credenziali_by_item = {}
    testdir_by_item = {}

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

        cognomi = []
        if os.path.isdir(base_dir):
            nomi = os.listdir(base_dir)
            i = 0
            while i < len(nomi):
                nome_dir = nomi[i]
                percorso_dir = os.path.join(base_dir, nome_dir)
                if os.path.isdir(percorso_dir) and "test" in nome_dir.lower():
                    if "-" in nome_dir:
                        parti = nome_dir.split("-", 1)
                        if len(parti) == 2:
                            tag = parti[1].strip().lower()
                            if tag != "":
                                cognomi.append(tag)
                    elif "_" in nome_dir:
                        parti = nome_dir.split("_", 1)
                        if len(parti) == 2:
                            tag = parti[1].strip().lower()
                            if tag != "":
                                cognomi.append(tag)
                i = i + 1

        try:
            with open(percorso_csv, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["cognome", "dominio", "ftp_user", "ftp_password"])
                inseriti = sorted(set(cognomi))
                i = 0
                while i < len(inseriti):
                    writer.writerow([inseriti[i], "", "", ""])
                    i = i + 1
            log("Modello CSV creato in: " + percorso_csv)
            if len(cognomi) > 0:
                log(
                    "Inseriti automaticamente {} nominativi (da nomi cartella).".format(
                        len(set(cognomi))
                    )
                )
            else:
                log("Nessuna cartella utile trovata: modello con sole intestazioni.")
        except Exception as e:
            messagebox.showerror(
                "Errore",
                "Errore nella creazione del modello CSV:\n" + str(e)
            )

    btn_modello.configure(command=crea_modello_csv)

    # ------------------------------------------------------------------
    # Carica CSV
    # ------------------------------------------------------------------
    def carica_csv():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove."
            )
            return

        percorso_csv = filedialog.askopenfilename(
            title="Seleziona file CSV con domini",
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
        )
        if not percorso_csv:
            return

        # pulizia tabella e stato
        for item in tree.get_children():
            tree.delete(item)
        credenziali_by_item.clear()
        testdir_by_item.clear()

        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_riepilogo.configure(state="disabled")

        metrics_by_student_cache.clear()
        texts_test_cache.clear()
        merged_domain_texts_cache.clear()
        del students_in_test_cache[:]
        del students_in_domain_cache[:]

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
                "Errore nella lettura del CSV:\n" + str(e)
            )
            return

        if not righe:
            messagebox.showwarning(
                "Attenzione",
                "Il CSV selezionato non contiene righe."
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
                righe_inserite
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
                "Nessuna riga valida trovata nel CSV."
            )

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
            i = 0
            while i < len(files):
                percorso_file = os.path.join(radice, files[i])
                try:
                    totale = totale + os.path.getsize(percorso_file)
                except Exception:
                    pass
                i = i + 1

        lbl_peso_totale.config(text="Totale FTP: " + format_bytes(totale))

    # ------------------------------------------------------------------
    # Servizio coda aggiornamenti (da ftpAgent)
    # ------------------------------------------------------------------
    def process_update_queue():
        try:
            while True:
                task = update_queue.get_nowait()
                tipo = task[0]

                if tipo == "log":
                    msg = task[1]
                    log(msg)

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
    # Avvio download FTP
    # ------------------------------------------------------------------
    def scarica_tutti():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove."
            )
            return

        items = tree.get_children()
        if not items:
            messagebox.showwarning(
                "Attenzione",
                "Nessun dominio da scaricare. Carica prima il CSV."
            )
            return

        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_riepilogo.configure(state="disabled")

        metrics_by_student_cache.clear()
        texts_test_cache.clear()
        merged_domain_texts_cache.clear()
        del students_in_test_cache[:]
        del students_in_domain_cache[:]

        jobs = []
        i = 0
        while i < len(items):
            item_id = items[i]
            valori_corr = list(tree.item(item_id, "values"))
            alunno = valori_corr[0]
            dominio = valori_corr[1]
            stato_base = valori_corr[2]
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
            i = i + 1

        ftpAgent.start_batch_download(jobs, base_dir, update_queue)

    btn_scarica.configure(command=scarica_tutti)

    # ------------------------------------------------------------------
    # Analisi somiglianze (verifica vs MERGE dominio)
    # ------------------------------------------------------------------
    def analizza_somiglianze():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima la directory principale delle prove."
            )
            return

        dir_ftp_base = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp_base):
            messagebox.showwarning(
                "Attenzione",
                "La directory 00_DominiFTP non esiste. Esegui prima il download."
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

            if alunno != "":
                nome_cartella_test = testdir_by_item.get(item_id, "")
                if nome_cartella_test != "":
                    percorso_test = os.path.join(base_dir, nome_cartella_test)
                    if os.path.isdir(percorso_test):
                        tests_dirs[alunno] = percorso_test

                percorso_dom = os.path.join(dir_ftp_base, alunno)
                if os.path.isdir(percorso_dom):
                    domini_dirs[alunno] = percorso_dom

            i = i + 1

        estensioni = (".php", ".html", ".htm", ".css", ".js", ".txt")

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

        metrics_by_student, students_in_test, students_in_domain, texts_test, merged_domain_texts = similarity_ftp.analyze_reuse_by_student(
            tests_dirs,
            domini_dirs,
            estensioni,
            progress_cb,
        )

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

        log("=== Analisi somiglianze: riepilogo per studente ===")
        nomi = sorted(list(metrics_by_student.keys()))
        if len(nomi) == 0:
            log("Nessun alunno con verifica e dominio disponibili per il confronto.")
            btn_riepilogo.configure(state="disabled")
        else:
            soglia_avviso = 60.0
            soglia_allerta = 80.0

            i = 0
            while i < len(nomi):
                nome = nomi[i]
                m = metrics_by_student[nome]
                sim_globale = float(m.get("similarity_percent", 0.0))
                shared_lines = int(m.get("shared_lines_count", 0))
                shared_chars = int(m.get("shared_chars_len", 0))
                perc_shared_chars = float(m.get("percent_shared_chars_on_test", 0.0))
                total_lines_test = int(m.get("total_lines_test", 0))
                total_chars_test = int(m.get("total_chars_test", 0))

                log(
                    "{} -> Similarità globale: {:.1f}%  |  Righe condivise: {} (su {})  |  Caratteri condivisi: {}  |  Copertura su verifica: {:.1f}% ({} char)".format(
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

            btn_riepilogo.configure(state="normal")
            log(
                "=== Analisi completata. Apri il riepilogo per consultare i dettagli e le comparazioni avanzate on-demand. ==="
            )

    btn_analizza.configure(command=analizza_somiglianze)

    # ------------------------------------------------------------------
    # Riepilogo similitudini (tabella) + comparazioni avanzate
    # ------------------------------------------------------------------
    def apri_comparazioni_avanzate(alunno):
        """
        Finestra con tre elenchi:
          - Test ↔ Test
          - Test ↔ Domini
          - Dominio ↔ Domini
        con colorazione rosso/blu in funzione della similarità.
        """
        if len(students_in_test_cache) == 0 and len(students_in_domain_cache) == 0:
            messagebox.showwarning(
                "Attenzione",
                "Esegui prima l'analisi per generare i dati di confronto."
            )
            return

        top = tk.Toplevel(frame)
        top.title("Comparazioni avanzate per: " + str(alunno))

        nota = tk.Label(
            top,
            text="Valori in percentuale. Cromia: blu=bassa, arancio=media, rosso=alta similarità.",
            fg="black",
        )
        nota.grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=6)

        def crea_tv_con_colori(parent, titolo):
            group = tk.LabelFrame(parent, text=titolo)
            tv = ttk.Treeview(group, columns=("Confronto", "Similarità %"), show="headings", height=14)
            tv.heading("Confronto", text="Confronto")
            tv.heading("Similarità %", text="Similarità %")
            tv.column("Confronto", width=280, anchor="w")
            tv.column("Similarità %", width=120, anchor="center")
            sb = ttk.Scrollbar(group, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=sb.set)
            tv.grid(row=0, column=0, sticky="nsew")
            sb.grid(row=0, column=1, sticky="ns")
            group.grid_rowconfigure(0, weight=1)
            group.grid_columnconfigure(0, weight=1)
            tv.tag_configure("low", foreground="blue")
            tv.tag_configure("mid", foreground="#cc7a00")
            tv.tag_configure("high", foreground="red")
            return group, tv

        grp_tvt, tv_tvt = crea_tv_con_colori(
            top,
            "Test ↔ Test ({} vs altri test)".format(alunno),
        )
        grp_tvt.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")

        grp_tvd, tv_tvd = crea_tv_con_colori(
            top,
            "Test ↔ Domini (test di {} vs merge domini)".format(alunno),
        )
        grp_tvd.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")

        grp_dvd, tv_dvd = crea_tv_con_colori(
            top,
            "Dominio ↔ Domini (merge dominio di {} vs merge domini)".format(alunno),
        )
        grp_dvd.grid(row=1, column=2, padx=8, pady=8, sticky="nsew")

        # Test ↔ Test
        if alunno in texts_test_cache:
            base_text = texts_test_cache.get(alunno, "")
            i = 0
            while i < len(students_in_test_cache):
                other = students_in_test_cache[i]
                t_other = texts_test_cache.get(other, "")
                val = similarity_ftp.calculate_text_similarity_percent(base_text, t_other)

                tag = ""
                if val >= 80.0:
                    tag = "high"
                elif val >= 60.0:
                    tag = "mid"
                else:
                    if val <= 30.0:
                        tag = "low"

                tv_tvt.insert(
                    "",
                    "end",
                    values=(alunno + " ↔ " + other, "{:.1f}".format(val)),
                    tags=(tag,),
                )
                i = i + 1
        else:
            tv_tvt.insert("", "end", values=("Nessun test per " + alunno, "-"))

        # Test ↔ Domini
        if alunno in texts_test_cache:
            base_text = texts_test_cache.get(alunno, "")
            i = 0
            while i < len(students_in_domain_cache):
                other = students_in_domain_cache[i]
                d_other = merged_domain_texts_cache.get(other, "")
                val = similarity_ftp.calculate_text_similarity_percent(base_text, d_other)

                tag = ""
                if val >= 80.0:
                    tag = "high"
                elif val >= 60.0:
                    tag = "mid"
                else:
                    if val <= 30.0:
                        tag = "low"

                tv_tvd.insert(
                    "",
                    "end",
                    values=(alunno + " (test) ↔ " + other + " (dom)", "{:.1f}".format(val)),
                    tags=(tag,),
                )
                i = i + 1
        else:
            tv_tvd.insert("", "end", values=("Nessun test per " + alunno, "-"))

        # Dominio ↔ Domini
        if alunno in merged_domain_texts_cache:
            base_dom = merged_domain_texts_cache.get(alunno, "")
            i = 0
            while i < len(students_in_domain_cache):
                other = students_in_domain_cache[i]
                d_other = merged_domain_texts_cache.get(other, "")
                val = similarity_ftp.calculate_text_similarity_percent(base_dom, d_other)

                tag = ""
                if val >= 80.0:
                    tag = "high"
                elif val >= 60.0:
                    tag = "mid"
                else:
                    if val <= 30.0:
                        tag = "low"

                tv_dvd.insert(
                    "",
                    "end",
                    values=(alunno + " (dom) ↔ " + other + " (dom)", "{:.1f}".format(val)),
                    tags=(tag,),
                )
                i = i + 1
        else:
            tv_dvd.insert("", "end", values=("Nessun dominio per " + alunno, "-"))

        top.grid_rowconfigure(1, weight=1)
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=1)

    def mostra_riepilogo():
        if len(metrics_by_student_cache) == 0:
            messagebox.showinfo(
                "Informazione",
                "Non ci sono risultati da visualizzare. Esegui prima l'analisi."
            )
            return

        top = tk.Toplevel(frame)
        top.title("Riepilogo similitudini (verifica ↔ MERGE dominio)")

        cols = (
            "Alunno",
            "Similarità globale %",
            "Righe condivise",
            "Caratteri condivisi",
            "Copertura su verifica %",
            "Righe test",
            "Caratteri test",
        )
        tv = ttk.Treeview(top, columns=cols, show="headings", height=20)

        i = 0
        while i < len(cols):
            c = cols[i]
            tv.heading(c, text=c)
            if c == "Alunno":
                tv.column(c, width=180, anchor="w")
            else:
                tv.column(c, width=160, anchor="center")
            i = i + 1

        sb = ttk.Scrollbar(top, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        tv.tag_configure("low", foreground="blue")
        tv.tag_configure("mid", foreground="#cc7a00")
        tv.tag_configure("high", foreground="red")

        nomi = sorted(list(metrics_by_student_cache.keys()))
        i = 0
        while i < len(nomi):
            nome = nomi[i]
            m = metrics_by_student_cache[nome]
            sim_globale = float(m.get("similarity_percent", 0.0))
            shared_lines = int(m.get("shared_lines_count", 0))
            shared_chars = int(m.get("shared_chars_len", 0))
            perc_shared_chars = float(m.get("percent_shared_chars_on_test", 0.0))
            total_lines_test = int(m.get("total_lines_test", 0))
            total_chars_test = int(m.get("total_chars_test", 0))

            tag = ""
            if sim_globale >= 80.0 or perc_shared_chars >= 80.0:
                tag = "high"
            elif sim_globale >= 60.0 or perc_shared_chars >= 60.0:
                tag = "mid"
            else:
                if sim_globale <= 30.0 and perc_shared_chars <= 30.0:
                    tag = "low"

            values = (
                nome,
                "{:.1f}".format(sim_globale),
                str(shared_lines),
                str(shared_chars),
                "{:.1f}".format(perc_shared_chars),
                str(total_lines_test),
                str(total_chars_test),
            )
            tv.insert("", "end", values=values, tags=(tag,))
            i = i + 1

        def on_double_click(event):
            item_id = tv.identify_row(event.y)
            if item_id == "":
                return
            vals = tv.item(item_id, "values")
            if not vals:
                return
            selected = vals[0]
            apri_comparazioni_avanzate(selected)

        tv.bind("<Double-1>", on_double_click)

        legenda = tk.Label(
            top,
            text="Legenda: blu = bassa similarità, arancio = media, rosso = alta. Doppio clic su un alunno per aprire le comparazioni.",
            fg="black",
        )
        legenda.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=6)

        top.grid_rowconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)

    btn_riepilogo.configure(command=mostra_riepilogo)

    # ------------------------------------------------------------------
    # Avvio del servizio di coda e layout della frame
    # ------------------------------------------------------------------
    def process_update_queue_wrapper():
        process_update_queue()

    frame.after(100, process_update_queue_wrapper)

    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(5, weight=1)

    log("Frame domini attivo. In attesa di caricamento CSV...")
    return frame
