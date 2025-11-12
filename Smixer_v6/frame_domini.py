import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import threading
import queue
from ftplib import FTP
from datetime import datetime
import re

# Modulo dedicato all’analisi verifiche/domìni (non alteriamo similarity.py)
import similarity_ftp

YELLOW_BG = "#85187c"


# ======================================================================
# FUNZIONI DI SUPPORTO
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


def get_versioned_path(percorso_base):
    """
    Applica versionamento incrementale se il file esiste già.
    es: file.ext -> file_v01.ext -> file_v02.ext
    """
    if not os.path.exists(percorso_base):
        return percorso_base
    base, ext = os.path.splitext(percorso_base)
    contatore = 1
    while True:
        candidato = "{}_v{:02d}{}".format(base, contatore, ext)
        if not os.path.exists(candidato):
            return candidato
        contatore = contatore + 1


def _sanitize_alunno_tag(raw):
    """
    Ripulisce il valore 'alunno' dal CSV:
    - minuscolo
    - se è una email usa la parte prima di '@'
    - rimuove spazi
    """
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    if "@" in s:
        s = s.split("@", 1)[0]
    s = s.replace(" ", "")
    return s


def _derive_candidate_tags(raw):
    """
    Da 'nome.cognome', 'cognome.nome', 'cognome' o email -> lista di tag candidati.
    Ordine: base, scambi, singoli.
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

    # Dedup preservando l’ordine
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
    Elenca le directory di primo livello nella cartella selezionata.
    Non impone schema: restituisce tutte le cartelle (ci penserà il matcher).
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
    Trova la cartella test associata all’alunno.
    Schemi supportati (case-insensitive):
      1) <tag>__testNN            (NUOVO FORMATO)
      2) testNN-<tag>  / testNN_<tag>   (STORICI)
      3) fallback permissivo: contiene "test" e il tag
    Dove <tag> è uno dei candidati derivati da _derive_candidate_tags().
    """
    if not test_dirs:
        return ""

    # mappa lower -> originale
    td_low_map = {}
    i = 0
    while i < len(test_dirs):
        d = test_dirs[i]
        td_low_map[d.lower()] = d
        i = i + 1

    candidates = _derive_candidate_tags(alunno_raw)

    # 1) <tag>__test
    i = 0
    while i < len(candidates):
        tag = candidates[i]
        prefix = tag + "__test"
        for low_name, original in td_low_map.items():
            if low_name.startswith(prefix):
                return original
        i = i + 1

    # 2) testNN-<tag>  oppure testNN_<tag>
    i = 0
    while i < len(candidates):
        tag = candidates[i]
        pattern_dash = "-" + tag
        pattern_underscore = "_" + tag
        for low_name, original in td_low_map.items():
            if low_name.startswith("test") and (low_name.endswith(pattern_dash) or low_name.endswith(pattern_underscore)):
                return original
        i = i + 1

    # 3) fallback: contiene "test" e il tag
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
    Gestione Domini Altervista:
      - Crea modello CSV
      - Carica CSV (cognome, dominio, ftp_user, ftp_password)
      - Associa alunno → cartella test (nuovo schema + fallback)
      - Download FTP in parallelo con versionamento e log
      - Tabella stato per ogni alunno
      - Peso complessivo directory 00_DominiFTP
      - Analisi somiglianze + mappa (via similarity_ftp)
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
    tk.Label(frame, text="Log eventi:", bg=YELLOW_BG).grid(row=2, column=0, sticky="w", padx=6, pady=6)

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
            elementi = os.listdir(base_dir)
            j = 0
            while j < len(elementi):
                nome_dir = elementi[j]
                percorso_dir = os.path.join(base_dir, nome_dir)
                if os.path.isdir(percorso_dir) and "test" in nome_dir.lower():
                    # tenta di estrarre parte dopo "-" o "_"
                    if "-" in nome_dir:
                        parti = nome_dir.split("-", 1)
                        if len(parti) == 2:
                            cogn = parti[1].strip().lower()
                            if cogn:
                                cognomi.append(cogn)
                    elif "_" in nome_dir:
                        parti = nome_dir.split("_", 1)
                        if len(parti) == 2:
                            cogn = parti[1].strip().lower()
                            if cogn:
                                cognomi.append(cogn)
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
                log("Inseriti automaticamente {} nominativi candidate dai nomi cartella.".format(len(set(cognomi))))
            else:
                log("Nessuna cartella utile trovata: modello creato con sole intestazioni.")
        except Exception as e:
            messagebox.showerror("Errore", "Errore nella creazione del modello CSV:\n" + str(e))

    btn_modello.configure(command=crea_modello_csv)

    # ------------------------------------------------------------------
    # Carica CSV
    # ------------------------------------------------------------------
    def carica_csv():
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
            messagebox.showwarning("Attenzione", "Seleziona prima la directory principale delle prove.")
            return

        percorso_csv = filedialog.askopenfilename(
            title="Seleziona file CSV con domini",
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")],
        )
        if not percorso_csv:
            return

        test_dirs = _list_test_dirs(base_dir)
        log("Trovate {} cartelle (candidate test) nella directory selezionata.".format(len(test_dirs)))

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

        i = 0
        while i < len(righe):
            row = righe[i]
            cognome = row.get("cognome", "").strip().lower()
            dominio = row.get("dominio", "").strip()
            ftp_user = row.get("ftp_user", "").strip()
            ftp_pass = row.get("ftp_password", "").strip()

            if cognome == "" and dominio == "":
                i = i + 1
                continue

            found_test = _match_test_dir(test_dirs, cognome)
            if found_test != "":
                stato_iniziale = "Test OK"
            else:
                stato_iniziale = "Test non trovato"

            valori = (
                cognome,        # Alunno (tag)
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
            i = i + 1

        log("File CSV '{}' caricato. Righe valide: {}".format(os.path.basename(percorso_csv), righe_inserite))

        if righe_inserite > 0:
            btn_scarica.configure(state="normal")
            log("Bottone download FTP abilitato ({} domini caricati).".format(righe_inserite))
        else:
            btn_scarica.configure(state="disabled")
            messagebox.showwarning("Attenzione", "Nessuna riga valida trovata nel CSV.")

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
    # Loop di servizio per aggiornare la GUI da thread
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
    # Download FTP (parallelo)
    # ------------------------------------------------------------------
    def scarica_tutti():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning("Attenzione", "Seleziona prima la directory principale delle prove.")
            return

        items = tree.get_children()
        if not items:
            messagebox.showwarning("Attenzione", "Nessun dominio da scaricare. Carica prima il CSV.")
            return

        dir_ftp_base = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp_base):
            os.makedirs(dir_ftp_base, exist_ok=True)

        log("=== Inizio download FTP in {} ===".format(dir_ftp_base))
        btn_scarica.configure(state="disabled")
        btn_analizza.configure(state="disabled")
        btn_mappa.configure(state="disabled")
        similarity_results.clear()

        jobs = []
        i = 0
        while i < len(items):
            item_id = items[i]
            valori_corr = list(tree.item(item_id, "values"))
            alunno = valori_corr[0]
            dominio = valori_corr[1]
            stato_base = valori_corr[2]
            ftp_user, ftp_pass = credenziali_by_item.get(item_id, ("", ""))

            jobs.append({
                "item_id": item_id,
                "alunno": alunno,
                "dominio": dominio,
                "stato_base": stato_base,
                "ftp_user": ftp_user,
                "ftp_pass": ftp_pass,
            })
            i = i + 1

        def worker_job(job):
            item_id = job["item_id"]
            alunno = job["alunno"]
            dominio = job["dominio"]
            stato_base = job["stato_base"]
            ftp_user = job["ftp_user"]
            ftp_pass = job["ftp_pass"]

            host = dominio
            if host and not host.startswith("ftp."):
                host = "ftp." + host

            # reset campi
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

            # cartella locale alunno
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
                    j = 0
                    while j < len(nomi):
                        nome = nomi[j]
                        if nome not in (".", ".."):
                            if percorso_remoto in (".", ""):
                                remoto = nome
                            else:
                                remoto = percorso_remoto + "/" + nome
                            lista_file_remoti.append(remoto)
                        j = j + 1
                    return

                k = 0
                while k < len(entries):
                    nome, facts = entries[k]
                    if nome in (".", ".."):
                        k = k + 1
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
                    k = k + 1

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

            m = 0
            while m < len(lista_file_remoti):
                remoto = lista_file_remoti[m]
                parti = remoto.split("/")
                cartella_locale_corrente = dir_locale_alunno

                n = 0
                while n < len(parti) - 1:
                    nome_dir = parti[n]
                    cartella_locale_corrente = os.path.join(cartella_locale_corrente, nome_dir)
                    if not os.path.isdir(cartella_locale_corrente):
                        try:
                            os.makedirs(cartella_locale_corrente, exist_ok=True)
                        except Exception:
                            pass
                    n = n + 1

                nome_file = parti[-1]
                percorso_locale_base = os.path.join(cartella_locale_corrente, nome_file)
                percorso_locale = get_versioned_path(percorso_locale_base)

                try:
                    with open(percorso_locale, "wb") as f_locale:
                        ftp.retrbinary("RETR " + remoto, f_locale.write)
                except Exception:
                    m = m + 1
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

                percentuale = int(round((conteggio_file * 100.0) / float(totale_file)))
                if percentuale > 99 and conteggio_file < totale_file:
                    percentuale = 99

                update_queue.put(("set", item_id, "Avanzamento", str(percentuale) + "%"))
                update_queue.put(("set", item_id, "N. file", str(conteggio_file)))
                update_queue.put(("set", item_id, "Peso cartella", format_bytes(peso_totale_alunno)))
                update_queue.put(("set", item_id, "Elenco file", ", ".join(elenco_file_preview)))

                m = m + 1

            try:
                ftp.quit()
            except Exception:
                pass

            if ultima_modifica is not None:
                testo_data = ultima_modifica.strftime("%Y-%m-%d %H:%M")
            else:
                testo_data = "n.d."

            # Forza 100% a job concluso
            update_queue.put(("set", item_id, "Avanzamento", "100%"))
            update_queue.put(("set", item_id, "Ultima modifica", testo_data))
            update_queue.put(("set", item_id, "Stato", stato_base + " / Download OK"))
            update_queue.put(("log", "✅ Download completato per '{}' ({}). Ultima modifica remota: {}".format(alunno, dominio, testo_data)))

        # Avvio thread
        threads = []
        i = 0
        while i < len(jobs):
            t = threading.Thread(target=worker_job, args=(jobs[i],))
            t.daemon = True
            t.start()
            threads.append(t)
            i = i + 1

        def monitor_thread():
            j = 0
            while j < len(threads):
                threads[j].join()
                j = j + 1
            update_queue.put(("fine_download", None))

        monitor = threading.Thread(target=monitor_thread, daemon=True)
        monitor.start()

    # ------------------------------------------------------------------
    # Analisi somiglianze (similarity_ftp)
    # ------------------------------------------------------------------
    def analizza_somiglianze():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning("Attenzione", "Seleziona prima la directory principale delle prove.")
            return

        dir_ftp_base = os.path.join(base_dir, "00_DominiFTP")
        if not os.path.isdir(dir_ftp_base):
            messagebox.showwarning("Attenzione", "La directory 00_DominiFTP non esiste. Esegui prima il download.")
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
                dir_dominio_alunno = os.path.join(dir_ftp_base, alunno)
                if os.path.isdir(dir_dominio_alunno):
                    domini_dirs[alunno] = dir_dominio_alunno
            i = i + 1

        estensioni = (".php", ".html", ".htm", ".css", ".js", ".txt")

        metrics_by_student, students_in_test, students_in_domain, texts_test, texts_domain = similarity_ftp.analyze_reuse_by_student(
            tests_dirs, domini_dirs, estensioni
        )

        similarity_results.clear()

        if len(students_in_test) >= 2:
            matrice_test_test = similarity_ftp.build_similarity_matrix(students_in_test, texts_test)
            similarity_results["test_vs_test"] = {"rows": students_in_test, "cols": students_in_test, "matrix": matrice_test_test}

        if len(students_in_domain) >= 2:
            matrice_dom_dom = similarity_ftp.build_similarity_matrix(students_in_domain, texts_domain)
            similarity_results["dom_vs_dom"] = {"rows": students_in_domain, "cols": students_in_domain, "matrix": matrice_dom_dom}

        if len(students_in_test) >= 1 and len(students_in_domain) >= 1:
            matrice_test_dom = similarity_ftp.build_cross_similarity_matrix(students_in_test, students_in_domain, texts_test, texts_domain)
            similarity_results["test_vs_dom"] = {"rows": students_in_test, "cols": students_in_domain, "matrix": matrice_test_dom}

        log("=== Analisi somiglianze (riuso verifica vs dominio personale) ===")
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
            messagebox.showinfo("Informazione", "Non ci sono risultati da visualizzare. Esegui prima l'analisi.")
            return

        if "test_vs_test" in similarity_results:
            d = similarity_results["test_vs_test"]
            similarity_ftp.show_heatmap(frame, "Verifica vs verifiche compagni", d["rows"], d["cols"], d["matrix"])

        if "dom_vs_dom" in similarity_results:
            d = similarity_results["dom_vs_dom"]
            similarity_ftp.show_heatmap(frame, "Domini personali vs domini compagni", d["rows"], d["cols"], d["matrix"])

        if "test_vs_dom" in similarity_results:
            d = similarity_results["test_vs_dom"]
            similarity_ftp.show_heatmap(frame, "Verifiche vs domini (di tutti)", d["rows"], d["cols"], d["matrix"])

    # ------------------------------------------------------------------
    # Bind pulsanti e avvio servizio coda
    # ------------------------------------------------------------------
    btn_scarica.configure(command=scarica_tutti)
    btn_analizza.configure(command=analizza_somiglianze)
    btn_mappa.configure(command=mostra_mappa)

    process_update_queue()

    # Layout elastico
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(5, weight=1)

    log("Frame domini attivo. In attesa di caricamento CSV...")
    return frame
