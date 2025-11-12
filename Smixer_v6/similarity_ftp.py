import os
import difflib
from datetime import datetime

import tkinter as tk
from tkinter import Toplevel, messagebox
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except Exception:
    plt = None
    FigureCanvasTkAgg = None
    HAS_MATPLOTLIB = False


# ======================================================================
# UTILITÀ DI LETTURA E NORMALIZZAZIONE TESTO (FTP / VERIFICHE)
# ======================================================================

def _safe_read_text(file_path):
    """
    Legge un file di testo provando utf-8 e latin-1. In caso di errore usa 'ignore'.
    Ritorna stringa (anche vuota se non leggibile).
    """
    if not os.path.isfile(file_path):
        return ""

    contenuto = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            contenuto = f.read()
        return contenuto
    except Exception:
        pass

    try:
        with open(file_path, "r", encoding="latin-1") as f:
            contenuto = f.read()
        return contenuto
    except Exception:
        pass

    try:
        with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
            contenuto = f.read()
        return contenuto
    except Exception:
        return ""


def _normalize_text_for_code(text):
    """
    Normalizza il testo per confronto:
    - uniforma gli a capo
    - rimuove righe vuote o solo spazi
    - rimuove righe di commento molto comuni (best-effort, non parsing completo)
    - trim spazi iniziali/finali di ogni riga

    NOTA: non altera il case in modo da non perdere semantica nei linguaggi case-sensitive.
    """
    if text is None:
        return ""

    testo = text.replace("\r\n", "\n").replace("\r", "\n")

    righe = testo.split("\n")
    righe_pulite = []

    indice = 0
    while indice < len(righe):
        riga = righe[indice].strip()

        if riga == "":
            indice = indice + 1
            continue

        # Commenti comuni: HTML <!-- --> non è semplice a riga singola;
        # qui escludiamo almeno righe che iniziano con token classici:
        # - // (C/JS/Java/PHP)
        # - #  (shell, python, php)
        # - *  (blocchi in CSS/JS, spesso righe interne /* ... */)
        # - */ (chiusura blocco)
        if riga.startswith("//"):
            indice = indice + 1
            continue

        if riga.startswith("#"):
            indice = indice + 1
            continue

        if riga.startswith("/*"):
            indice = indice + 1
            continue

        if riga.startswith("*"):
            indice = indice + 1
            continue

        if riga.startswith("*/"):
            indice = indice + 1
            continue

        righe_pulite.append(riga)
        indice = indice + 1

    return "\n".join(righe_pulite)


def _text_to_line_set(text, min_len=4):
    """
    Converte un testo normalizzato in un set di righe significative (len >= min_len).
    Serve a stimare rapidamente il riuso (Jaccard-like).
    """
    insieme = set()

    if text is None:
        return insieme

    testo = text
    righe = testo.split("\n")

    indice = 0
    while indice < len(righe):
        r = righe[indice].strip()
        if len(r) >= int(min_len):
            insieme.add(r)
        indice = indice + 1

    return insieme


def read_text_from_directory(directory_path, allowed_extensions):
    """
    Legge ricorsivamente tutti i file con estensione ammessa in una directory
    e concatena i contenuti in un'unica stringa normalizzata.

    Ritorna stringa vuota se la directory non esiste o non contiene file validi.
    """
    if not directory_path:
        return ""

    if not os.path.isdir(directory_path):
        return ""

    parti = []

    for radice, _, files in os.walk(directory_path):
        for nome in files:
            nome_lower = nome.lower()
            estensione_valida = False

            idx = 0
            while idx < len(allowed_extensions):
                ext = allowed_extensions[idx]
                if nome_lower.endswith(ext):
                    estensione_valida = True
                    break
                idx = idx + 1

            if not estensione_valida:
                continue

            percorso = os.path.join(radice, nome)
            contenuto = _safe_read_text(percorso)
            if contenuto is None:
                contenuto = ""

            if contenuto != "":
                parti.append("FILE: " + nome + "\n" + contenuto + "\n")

    testo = "\n".join(parti)
    return _normalize_text_for_code(testo)


# ======================================================================
# METRICHE DI RIUSO TRA VERIFICA LOCALE E DOMINIO PERSONALE
# ======================================================================

def calculate_text_similarity_percent(text1, text2):
    """
    Calcola similarità percentuale globale (0-100) con difflib su stringhe.
    """
    if not text1 and not text2:
        return 100.0

    if not text1 or not text2:
        return 0.0

    matcher = difflib.SequenceMatcher(None, text1, text2)
    ratio = matcher.ratio()
    return ratio * 100.0


def compute_reuse_metrics(test_text, domain_text):
    """
    Calcola un set di metriche numeriche di riuso fra:
    - testo della verifica locale (test_text)
    - testo del dominio personale (domain_text)

    Restituisce un dict con:
    - similarity_percent: similarità globale (difflib, 0-100)
    - total_lines_test
    - total_lines_domain
    - shared_lines_count
    - percent_reuse_from_domain_on_test  = shared_lines_count / total_lines_test   * 100
    - percent_overlap_on_domain          = shared_lines_count / total_lines_domain * 100
    """
    risultato = {}

    testo_test = test_text if test_text is not None else ""
    testo_dom = domain_text if domain_text is not None else ""

    # Similarità globale
    similarity_percent = calculate_text_similarity_percent(testo_test, testo_dom)

    # Stima riuso a righe
    set_test = _text_to_line_set(testo_test, min_len=4)
    set_dom = _text_to_line_set(testo_dom, min_len=4)

    total_test = len(set_test)
    total_dom = len(set_dom)

    shared = 0
    if total_test > 0 and total_dom > 0:
        shared = len(set_test.intersection(set_dom))
    elif total_test == 0 or total_dom == 0:
        shared = 0

    reuse_on_test = 0.0
    if total_test > 0:
        reuse_on_test = (shared * 100.0) / float(total_test)

    overlap_on_domain = 0.0
    if total_dom > 0:
        overlap_on_domain = (shared * 100.0) / float(total_dom)

    risultato["similarity_percent"] = similarity_percent
    risultato["total_lines_test"] = total_test
    risultato["total_lines_domain"] = total_dom
    risultato["shared_lines_count"] = shared
    risultato["percent_reuse_from_domain_on_test"] = reuse_on_test
    risultato["percent_overlap_on_domain"] = overlap_on_domain

    return risultato


def analyze_reuse_by_student(tests_dirs, domini_dirs, allowed_extensions):
    """
    Per ciascun alunno presente in entrambe le mappe (test e dominio),
    calcola le metriche di riuso e restituisce:
        - metrics_by_student: dict[alunno] -> dict metriche (vedi compute_reuse_metrics)
        - students_in_test:   lista ordinata alunni con test valido
        - students_in_domain: lista ordinata alunni con dominio valido
        - texts_test:         dict[alunno] = testo aggregato (normalizzato) della verifica
        - texts_domain:       dict[alunno] = testo aggregato (normalizzato) del dominio
    """
    metrics_by_student = {}
    texts_test = {}
    texts_domain = {}

    # Costruzione testi verifiche
    nomi_test = sorted(list(tests_dirs.keys()))
    i = 0
    while i < len(nomi_test):
        nome = nomi_test[i]
        d = tests_dirs.get(nome)
        testo = read_text_from_directory(d, allowed_extensions)
        if testo.strip() != "":
            texts_test[nome] = testo
        i = i + 1

    # Costruzione testi domini
    nomi_dom = sorted(list(domini_dirs.keys()))
    j = 0
    while j < len(nomi_dom):
        nome = nomi_dom[j]
        d = domini_dirs.get(nome)
        testo = read_text_from_directory(d, allowed_extensions)
        if testo.strip() != "":
            texts_domain[nome] = testo
        j = j + 1

    # Intersezione studenti con entrambi i testi
    studenti = sorted(list(set(texts_test.keys()).intersection(set(texts_domain.keys()))))

    k = 0
    while k < len(studenti):
        nome = studenti[k]
        met = compute_reuse_metrics(texts_test.get(nome, ""), texts_domain.get(nome, ""))
        metrics_by_student[nome] = met
        k = k + 1

    students_in_test = sorted(list(texts_test.keys()))
    students_in_domain = sorted(list(texts_domain.keys()))

    return metrics_by_student, students_in_test, students_in_domain, texts_test, texts_domain


# ======================================================================
# MATRICI E HEATMAP (COERENZA ESTETICA CON similarity.py)
# ======================================================================

def build_similarity_matrix(student_names, texts_by_student):
    """
    Costruisce una matrice di similarità NxN (lista di liste)
    tra tutti i testi degli studenti indicati.
    """
    dimensione = len(student_names)
    matrice = []

    riga_indice = 0
    while riga_indice < dimensione:
        riga = []
        colonna_indice = 0
        while colonna_indice < dimensione:
            nome_i = student_names[riga_indice]
            nome_j = student_names[colonna_indice]

            testo_i = texts_by_student.get(nome_i, "")
            testo_j = texts_by_student.get(nome_j, "")

            valore = calculate_text_similarity_percent(testo_i, testo_j)
            riga.append(valore)

            colonna_indice = colonna_indice + 1
        matrice.append(riga)
        riga_indice = riga_indice + 1

    return matrice


def build_cross_similarity_matrix(row_names, col_names, row_texts, col_texts):
    """
    Costruisce una matrice di similarità len(row_names) x len(col_names)
    tra due insiemi diversi (es. verifiche e domini).
    """
    num_righe = len(row_names)
    num_colonne = len(col_names)
    matrice = []

    riga_indice = 0
    while riga_indice < num_righe:
        riga = []
        colonna_indice = 0
        while colonna_indice < num_colonne:
            nome_riga = row_names[riga_indice]
            nome_colonna = col_names[colonna_indice]

            testo_riga = row_texts.get(nome_riga, "")
            testo_colonna = col_texts.get(nome_colonna, "")

            valore = calculate_text_similarity_percent(testo_riga, testo_colonna)
            riga.append(valore)

            colonna_indice = colonna_indice + 1
        matrice.append(riga)
        riga_indice = riga_indice + 1

    return matrice


def show_heatmap(parent, titolo, row_labels, col_labels, matrix):
    """
    Mostra una matrice di similarità come heatmap in una nuova finestra Tkinter.
    Coerenza estetica con similarity.py.
    """
    if not HAS_MATPLOTLIB:
        messagebox.showerror(
            "Errore",
            "Matplotlib non è disponibile. Installalo per visualizzare la mappa delle similitudini."
        )
        return

    if not row_labels or not col_labels:
        messagebox.showwarning(
            "Attenzione",
            "Non ci sono dati sufficienti per costruire la mappa delle similitudini."
        )
        return

    top = Toplevel(parent)
    top.title(titolo)

    larghezza = 8.0
    altezza = 6.0

    fig, ax = plt.subplots(figsize=(larghezza, altezza))

    # Conversione in float per sicurezza
    dati_numerici = []
    r = 0
    while r < len(matrix):
        riga = matrix[r]
        nuova_riga = []
        c = 0
        while c < len(riga):
            try:
                valore = float(riga[c])
            except Exception:
                valore = 0.0
            nuova_riga.append(valore)
            c = c + 1
        dati_numerici.append(nuova_riga)
        r = r + 1

    cax = ax.imshow(dati_numerici, interpolation="nearest", cmap="viridis", vmin=0.0, vmax=100.0)
    barra = fig.colorbar(cax)
    barra.set_label("Similarità (%)")

    ax.set_xticks(range(len(col_labels)))
    ax.set_yticks(range(len(row_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(row_labels, fontsize=8)

    ax.set_xlabel("Colonna")
    ax.set_ylabel("Riga")
    ax.set_title(titolo)

    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=top)
    canvas.draw()

    widget = canvas.get_tk_widget()
    widget.pack(fill="both", expand=True)

    # Riferimenti per evitare GC
    top._figure = fig
    top._canvas = canvas
