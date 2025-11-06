import os
import difflib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tkinter as tk
from tkinter import Toplevel, Text, Scrollbar


def _resolve_directory_source(directory_source) -> str:
    """
    Accetta:
      - una stringa con il path della directory
      - oppure una Label tkinter con testo tipo 'Directory selezionata: <percorso>'

    Restituisce il path pulito (stringa). Se non riesce, restituisce stringa vuota.
    """
    # Caso: Label (o widget simile con .cget)
    if hasattr(directory_source, "cget"):
        try:
            text = directory_source.cget("text")
            # gestisce il prefisso usato nella GUI
            path = text.replace("Directory selezionata:", "").strip()
            return path
        except Exception:
            pass

    # Caso: StringVar o oggetto con .get()
    if hasattr(directory_source, "get"):
        try:
            path = directory_source.get()
            return str(path).strip()
        except Exception:
            pass

    # Caso generico: consideriamo sia già una stringa
    return str(directory_source).strip()


def calculate_similarity(file1_path, file2_path):
    """
    Calcola la similarità (%) tra due file di testo usando difflib.SequenceMatcher.
    Restituisce:
      - matcher: oggetto SequenceMatcher
      - similarity: valore percentuale (0-100)
    """
    try:
        # Tenta UTF-8, in fallback latin-1
        try:
            with open(file1_path, "r", encoding="utf-8") as file1:
                content1 = file1.read()
        except UnicodeDecodeError:
            with open(file1_path, "r", encoding="latin-1", errors="replace") as file1:
                content1 = file1.read()

        try:
            with open(file2_path, "r", encoding="utf-8") as file2:
                content2 = file2.read()
        except UnicodeDecodeError:
            with open(file2_path, "r", encoding="latin-1", errors="replace") as file2:
                content2 = file2.read()

        # Normalizza gli a capo
        content1 = content1.replace("\r\n", "\n").replace("\r", "\n")
        content2 = content2.replace("\r\n", "\n").replace("\r", "\n")

        matcher = difflib.SequenceMatcher(None, content1, content2)
        return matcher, matcher.ratio() * 100.0

    except Exception:
        # In caso di errore, restituisce 0 e nessun matcher
        return None, 0.0


def show_similar_fragments(file1, file2, matcher):
    """
    Mostra in una nuova finestra due colonne di testo con i contenuti
    dei due file, a partire dal primo blocco dopo la riga di separazione
    '###############################################################'
    (se presente).
    """
    top = Toplevel()
    top.title(f"Somiglianze tra {os.path.basename(file1)} e {os.path.basename(file2)}")
    top.geometry("1200x800")
    top.resizable(True, True)

    frame1 = tk.Frame(top)
    frame1.grid(row=0, column=0, sticky="nsew")
    frame2 = tk.Frame(top)
    frame2.grid(row=0, column=1, sticky="nsew")

    text1 = Text(frame1, wrap="none", width=60, height=30)
    text1.pack(side="left", fill="both", expand=True)
    text2 = Text(frame2, wrap="none", width=60, height=30)
    text2.pack(side="left", fill="both", expand=True)

    scroll_y = Scrollbar(top, orient="vertical")
    scroll_y.grid(row=0, column=2, sticky="ns")

    text1.config(yscrollcommand=scroll_y.set)
    text2.config(yscrollcommand=scroll_y.set)

    def sync_scroll(*args):
        text1.yview(*args)
        text2.yview(*args)

    scroll_y.config(command=sync_scroll)

    # Recupera le stringhe originali dal matcher
    try:
        content1 = matcher.a
        content2 = matcher.b
    except Exception:
        content1 = ""
        content2 = ""

    # Prova a "tagliare" prima del primo blocco vero dopo le ###, se presenti
    marker = "###############################################################"
    try:
        idx1 = content1.find(marker)
        idx2 = content2.find(marker)
        if idx1 != -1:
            # salta la riga marker e la successiva
            next_newline = content1.find("\n", idx1)
            if next_newline != -1:
                content1 = content1[next_newline + 1 :]
        if idx2 != -1:
            next_newline = content2.find("\n", idx2)
            if next_newline != -1:
                content2 = content2[next_newline + 1 :]
    except Exception:
        # in caso di problemi, usiamo comunque le stringhe intere
        pass

    content1_lines = content1.splitlines()
    content2_lines = content2.splitlines()

    # Allinea il numero di righe
    max_line_count = max(len(content1_lines), len(content2_lines))
    while len(content1_lines) < max_line_count:
        content1_lines.append("")
    while len(content2_lines) < max_line_count:
        content2_lines.append("")

    for line1, line2 in zip(content1_lines, content2_lines):
        text1.insert("end", line1 + "\n")
        text2.insert("end", line2 + "\n")

    top.grid_rowconfigure(0, weight=1)
    top.grid_columnconfigure(0, weight=1)
    top.grid_columnconfigure(1, weight=1)


def plot_similarity_matrix(output_directory, report_text=None):
    """
    Costruisce e mostra una heatmap di similarità tra tutti i file *_mix.txt
    presenti in output_directory.

    - Cliccando su una cella (i, j) diversa dalla diagonale,
      apre una finestra con i frammenti di codice affiancati.

    Restituisce: (files, similarity_matrix)
      - files: lista dei path completi dei file considerati, in ordine
      - similarity_matrix: matrice NxN con i valori percentuali
    """
    files = [
        os.path.join(output_directory, file)
        for file in os.listdir(output_directory)
        if file.endswith("_mix.txt")
    ]
    files.sort()
    num_files = len(files)

    if num_files < 2:
        if report_text is not None:
            report_text.insert(
                "end",
                "Per l'analisi delle similarità servono almeno 2 file *_mix.txt.\n",
            )
            report_text.see("end")
        return files, None

    similarity_matrix = np.zeros((num_files, num_files))
    matchers = [[None for _ in range(num_files)] for _ in range(num_files)]

    # Calcolo delle similarità
    for i in range(num_files):
        for j in range(num_files):
            if i == j:
                similarity_matrix[i, j] = 100.0
            else:
                matcher, similarity = calculate_similarity(files[i], files[j])
                similarity_matrix[i, j] = similarity
                matchers[i][j] = matcher

    def on_click(event):
        if event.inaxes is None:
            return
        try:
            x = int(round(event.xdata))
            y = int(round(event.ydata))
        except Exception:
            return

        if x < 0 or y < 0 or x >= num_files or y >= num_files:
            return

        if x == y:
            # diagonale (file con sé stesso), non facciamo nulla
            return

        matcher = matchers[y][x]  # attenzione: righe = y, colonne = x
        if matcher:
            show_similar_fragments(files[y], files[x], matcher)

    # Plot della matrice
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        similarity_matrix,
        annot=True,
        fmt=".0f",
        cmap="coolwarm",
        xticklabels=[os.path.basename(f) for f in files],
        yticklabels=[os.path.basename(f) for f in files],
        ax=ax,
    )
    plt.title("Matrice di Similarità tra i file di output")
    plt.xlabel("File di Output")
    plt.ylabel("File di Output")
    plt.xticks(rotation=45, ha="right")

    fig.tight_layout()
    fig.canvas.mpl_connect("button_press_event", on_click)
    plt.show()

    if report_text is not None:
        report_text.insert(
            "end",
            "Matrice di similarità calcolata e visualizzata.\n"
            "Clicca su una cella (non diagonale) per vedere i frammenti di codice.\n",
        )
        report_text.see("end")

    return files, similarity_matrix


def analyze_similarities(directory_source, report_text):
    """
    Funzione chiamata dalla GUI (frame_correzione).

    - `directory_source` può essere:
        * una Label con testo 'Directory selezionata: <percorso>'
        * una stringa con il path base
    - Usa la sottocartella '00_MixOutput' e analizza i file *_mix.txt.
    """
    base_directory = _resolve_directory_source(directory_source)

    if not base_directory:
        report_text.insert(
            "end",
            "Nessuna directory selezionata per l'analisi delle similarità.\n",
        )
        report_text.see("end")
        return

    output_directory = os.path.join(base_directory, "00_MixOutput")

    if not os.path.exists(output_directory):
        report_text.insert(
            "end",
            f"La directory 00_MixOutput non esiste in:\n{base_directory}\n"
            "Esegui prima la fase di mix per generare i file *_mix.txt.\n",
        )
        report_text.see("end")
        return

    report_text.insert(
        "end",
        f"Analisi similarità sui file *_mix.txt in: {output_directory}\n",
    )
    report_text.see("end")

    files, matrix = plot_similarity_matrix(output_directory, report_text)

    if matrix is not None:
        # Piccolo riepilogo su eventuali similarità alte
        try:
            n = len(files)
            sospetti = []
            for i in range(n):
                for j in range(i + 1, n):
                    if matrix[i, j] >= 80.0:  # soglia "sospetto"
                        sospetti.append(
                            (os.path.basename(files[i]), os.path.basename(files[j]), matrix[i, j])
                        )

            if sospetti:
                report_text.insert(
                    "end",
                    "\nCoppie con similarità >= 80% (possibile copia):\n",
                )
                for f1, f2, sim in sospetti:
                    report_text.insert(
                        "end",
                        f" - {f1} <> {f2}: {sim:.0f}%\n",
                    )
            else:
                report_text.insert(
                    "end",
                    "\nNessuna coppia supera la soglia di similarità del 80%.\n",
                )
            report_text.see("end")
        except Exception:
            # se qualcosa va storto, non blocchiamo l'uso principale
            pass
