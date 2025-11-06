import os
import textwrap
from tkinter import messagebox
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Preformatted,
    PageBreak,
    Spacer,
    KeepTogether,
)
from PyPDF2 import PdfReader, PdfWriter


# =============================================================================
#  UTILITÀ GENERALI
# =============================================================================

def wrap_preserve_indent(text: str, width: int) -> str:
    """
    Avvolge il testo riga per riga mantenendo l'indentazione iniziale.

    - `width`: numero massimo di caratteri per riga (inclusa l'indentazione).
    """
    lines = text.splitlines()
    wrapped_lines = []

    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(line)
        else:
            # Conta gli spazi iniziali e li preserva come indentazione
            leading = len(line) - len(line.lstrip())
            indent = line[:leading]
            wrapped = textwrap.fill(
                line,
                width=width,
                initial_indent=indent,
                subsequent_indent=indent,
                drop_whitespace=False,
            )
            wrapped_lines.append(wrapped)

    return "\n".join(wrapped_lines)


def _resolve_base_directory(directory_source) -> str:
    """
    Accetta:
      - una stringa con il path della directory di lavoro
      - oppure un tk.Label con testo tipo 'Directory selezionata: <percorso>'

    Restituisce sempre il path pulito.
    """
    # Caso più semplice: è già una stringa
    if isinstance(directory_source, str):
        return directory_source.strip()

    # In alternativa tentiamo di leggerne il testo (es. Label tkinter)
    try:
        text = directory_source.cget("text")
    except Exception:
        # Fallback: rappresentazione testuale generica
        return str(directory_source).strip()

    # Gestisce il prefisso usato nella vecchia interfaccia
    return text.replace("Directory selezionata:", "").strip()


def _get_mix_output_directory(base_directory: str) -> str:
    """
    Restituisce il percorso alla directory '00_MixOutput' dentro la
    directory base selezionata.
    """
    return os.path.join(base_directory, "00_MixOutput")


def _ensure_mix_directory_exists(output_directory: str) -> bool:
    """
    Verifica l'esistenza della directory 00_MixOutput.
    Restituisce True se esiste, False altrimenti (mostrando un messaggio).
    """
    if not os.path.exists(output_directory):
        messagebox.showwarning(
            "Attenzione",
            "La directory 00_MixOutput non esiste.\n"
            "Esegui prima la fase di mix dei sorgenti.",
        )
        return False
    return True


# =============================================================================
#  FASE DI MIX: CREAZIONE DEI FILE _mix.txt
# =============================================================================

def mix_files(
    lbl_directory,
    entry_prompt,
    entry_extension,
    tree,
    report_text,
    include_prompt: bool,
    include_subdir: bool,
):
    """
    Crea il file di mix per ciascuna subdirectory presente nella tabella (tree)
    e li scrive nella directory 00_MixOutput.

    PARAMETERS (tutti widget Tk esistenti, come nelle versioni precedenti):
      - lbl_directory : Label che contiene il path della directory di lavoro
      - entry_prompt  : Text con l'introduzione (prompt) da anteporre agli elaborati
      - entry_extension : Entry con l'estensione dei file da includere (es. '.cpp')
      - tree          : Treeview con la lista delle sottodirectory (test01, test02, ...)
      - report_text   : Text usato come log degli eventi
      - include_prompt: se True, inserisce il prompt in testa a ciascun file di mix
      - include_subdir: se True, inserisce il nome della subdirectory come intestazione
    """
    base_directory = _resolve_base_directory(lbl_directory)
    prompt_string = entry_prompt.get("1.0", "end").strip()
    extension = entry_extension.get().strip()

    if not base_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
        return

    if not extension:
        messagebox.showwarning("Attenzione", "Specificare l'estensione dei file (es. .cpp).")
        return

    output_directory = _get_mix_output_directory(base_directory)
    os.makedirs(output_directory, exist_ok=True)

    report_text.delete("1.0", "end")

    for item in tree.get_children():
        subdir = tree.item(item, "values")[0]
        mix_result = create_mix_file(
            base_directory,
            subdir,
            prompt_string,
            extension,
            output_directory,
            include_prompt,
            include_subdir,
        )
        report_text.insert("end", mix_result)

    report_text.see("end")


def create_mix_file(
    base_directory: str,
    subdir: str,
    prompt_string: str,
    extension: str,
    output_directory: str,
    include_prompt: bool,
    include_subdir: bool,
) -> str:
    """
    Crea il file di mix per una specifica subdirectory (es. 'test01').

    Struttura dei file _mix.txt generati:
      - eventuale prompt iniziale (se include_prompt == True)
      - eventuale riga con il nome della subdirectory (se include_subdir == True)
      - per ciascun file sorgente trovato:
          ###############################################################
          <nome_file>
          <contenuto del file>
    """
    full_path = os.path.join(base_directory, subdir)
    mix_file_path = os.path.join(output_directory, f"{subdir}_mix.txt")

    try:
        files_to_mix = []
        for root, _dirs, files in os.walk(full_path):
            for file in files:
                if file.endswith(extension):
                    files_to_mix.append(os.path.join(root, file))

        if not files_to_mix:
            return (
                f"Nessun file con estensione {extension} trovato nella "
                f"subdirectory {subdir}. File di mix NON creato.\n"
            )

        with open(mix_file_path, "w", encoding="utf-8") as mix_file:
            if include_prompt and prompt_string:
                mix_file.write(prompt_string + "\n")

            if include_subdir:
                mix_file.write(subdir + "\n\n")

            for file_path in files_to_mix:
                # Proviamo prima UTF-8, se fallisce ripieghiamo su latin-1
                try:
                    with open(file_path, "r", encoding="utf-8") as current_file:
                        content = current_file.read()
                except UnicodeDecodeError:
                    with open(
                        file_path, "r", encoding="latin-1", errors="replace"
                    ) as current_file:
                        content = current_file.read()

                mix_file.write(
                    "###############################################################\n\n"
                )
                mix_file.write(f"{os.path.basename(file_path)}\n{content}\n")

        return (
            f"Mix completato per {subdir}: file con estensione {extension} "
            f"uniti con successo in {os.path.basename(mix_file_path)}.\n"
        )

    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n"


# =============================================================================
#  FASE DI EXPORT: CREAZIONE PDF
# =============================================================================

def create_individual_pdfs(directory_source, report_text):
    """
    Crea un PDF per ciascun file *_mix.txt presente in 00_MixOutput.

    - Ogni elaborato (test01_mix.txt, test02_mix.txt, ...) genera un proprio
      PDF con lo stesso nome base (test01_mix.pdf, ...).
    - Il contenuto viene impaginato in monospazio, con ritorni a capo
      controllati per evitare che le righe vadano fuori margine.

    Questa funzione è pensata per il bottone "Crea PDF multipli" della
    scheda Export.
    """
    base_directory = _resolve_base_directory(directory_source)
    if not base_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
        return

    output_directory = _get_mix_output_directory(base_directory)
    if not _ensure_mix_directory_exists(output_directory):
        return

    report_text.insert("end", f"Creazione PDF multipli dalla directory: {output_directory}\n")

    styles = getSampleStyleSheet()
    monospace_style = ParagraphStyle(
        "Monospace",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=10,
        leading=12,
    )
    max_char_width = 75  # larghezza massima in caratteri

    created_count = 0

    for file_name in sorted(os.listdir(output_directory)):
        if not file_name.endswith("_mix.txt"):
            continue

        txt_path = os.path.join(output_directory, file_name)
        base_name = os.path.splitext(file_name)[0]
        pdf_path = os.path.join(output_directory, f"{base_name}.pdf")

        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(txt_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        # Wrapping del contenuto mantenendo l'indentazione
        wrapped_content = wrap_preserve_indent(content, max_char_width)

        # Rimozione di eventuali righe vuote iniziali/finali "spurie"
        lines = [line for line in wrapped_content.splitlines()]
        cleaned_content = "\n".join(lines)

        story = [Preformatted(cleaned_content, monospace_style)]

        try:
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            doc.build(story)
            created_count += 1
            report_text.insert(
                "end",
                f"Creato PDF: {os.path.basename(pdf_path)}\n",
            )
        except Exception as e:
            report_text.insert(
                "end",
                f"Errore durante la creazione del PDF {pdf_path}: {e}\n",
            )

    if created_count == 0:
        report_text.insert(
            "end",
            "Nessun file *_mix.txt trovato in 00_MixOutput: nessun PDF creato.\n",
        )
    else:
        report_text.insert(
            "end",
            f"Creazione PDF multipli completata. Totale PDF creati: {created_count}\n",
        )

    report_text.see("end")


def merge_all_files(directory_source, report_text):
    """
    Genera un unico PDF finale pensando all'uso con 'PdfMegaMerge' / stampa
    fronte-retro:

      - Usa i PDF individuali generati da create_individual_pdfs()
        (test01_mix.pdf, test02_mix.pdf, ...).
      - Per ogni PDF verifica il numero di pagine:
          * se è dispari, aggiunge una pagina bianca di riempimento
            in modo che ogni elaborato occupi un numero pari di pagine.
      - Tutti i blocchi (eventualmente "pari-ficati") vengono concatenati
        in un unico file:
            00_MEGAmerged_output_final.pdf

    Questa funzione è pensata per il bottone "Per PdfMegaMerge".
    """
    base_directory = _resolve_base_directory(directory_source)
    if not base_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
        return

    output_directory = _get_mix_output_directory(base_directory)
    if not _ensure_mix_directory_exists(output_directory):
        return

    final_pdf_path = os.path.join(output_directory, "00_MEGAmerged_output_final.pdf")

    # Raccolta dei PDF individuali; se non ce ne sono, proviamo a generarli
    pdf_files = sorted(
        [
            os.path.join(output_directory, f)
            for f in os.listdir(output_directory)
            if f.endswith(".pdf") and not f.startswith("00_MEGAmerged_output_final")
        ]
    )

    if not pdf_files:
        # Nessun PDF trovato: proviamo a crearli dai file _mix.txt
        report_text.insert(
            "end",
            "Nessun PDF individuale trovato in 00_MixOutput.\n"
            "Avvio automatico di 'Crea PDF multipli'...\n",
        )
        report_text.see("end")
        create_individual_pdfs(base_directory, report_text)

        # Riscansiona
        pdf_files = sorted(
            [
                os.path.join(output_directory, f)
                for f in os.listdir(output_directory)
                if f.endswith(".pdf") and not f.startswith("00_MEGAmerged_output_final")
            ]
        )

    if not pdf_files:
        report_text.insert(
            "end",
            "Impossibile procedere con il MEGAmerge: nessun PDF da unire.\n",
        )
        report_text.see("end")
        return

    try:
        writer = PdfWriter()

        report_text.insert(
            "end",
            "Inizio creazione del PDF finale con pagine pari per ogni elaborato...\n",
        )

        for pdf_path in pdf_files:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)

            # Aggiunge tutte le pagine dell'elaborato
            for page in reader.pages:
                writer.add_page(page)

            # Se il numero di pagine è dispari, aggiunge una pagina bianca
            if num_pages % 2 == 1 and num_pages > 0:
                first_page = reader.pages[0]
                width = first_page.mediabox.width
                height = first_page.mediabox.height
                writer.add_blank_page(width=width, height=height)
                report_text.insert(
                    "end",
                    f"{os.path.basename(pdf_path)}: {num_pages} pagine -> "
                    f"aggiunta 1 pagina bianca (totale nel blocco: {num_pages + 1}).\n",
                )
            else:
                report_text.insert(
                    "end",
                    f"{os.path.basename(pdf_path)}: {num_pages} pagine (già pari).\n",
                )

        # Scrittura del PDF finale su disco
        with open(final_pdf_path, "wb") as out_f:
            writer.write(out_f)

        report_text.insert(
            "end",
            f"MEGAmerge completato. File PDF finale creato: {final_pdf_path}\n",
        )
        report_text.see("end")

    except Exception as e:
        report_text.insert(
            "end",
            f"Errore durante il merge dei PDF in un unico file: {e}\n",
        )
        report_text.see("end")
