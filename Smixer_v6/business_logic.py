import os
import textwrap
from tkinter import messagebox

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Preformatted

from PyPDF2 import PdfReader, PdfWriter

import utils  # per parse_extensions


# =============================================================================
# UTILITÀ GENERALI
# =============================================================================

def wrap_preserve_indent(text: str, width: int) -> str:
    """
    Va a capo il testo mantenendo l'indentazione iniziale di ogni riga.
    """
    lines = text.splitlines()
    wrapped_lines = []

    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(line)
        else:
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
      - oppure un tk.Label con testo tipo 'Directory selezionata: ...'
      - oppure un oggetto con .get() (es. StringVar)

    Restituisce sempre il path pulito.
    """

    # Caso più semplice: è già una stringa
    if isinstance(directory_source, str):
        return directory_source.strip()

    # Caso: oggetto con .get() (es. StringVar)
    if hasattr(directory_source, "get"):
        try:
            value = directory_source.get()
            return str(value).strip()
        except Exception:
            pass

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
    Directory usata per:
    - contenere i file di mix *_mix.txt
    - (in precedenza) anche i PDF.

    Rimane la directory principale di lavoro per i mix.
    """
    return os.path.join(base_directory, "00_MixOutput")


def _get_pdf_output_directory(base_directory: str) -> str:
    """
    Directory dedicata ai PDF esportati (individuali + finale).
    Tutti i PDF verranno scritti qui.
    """
    return os.path.join(base_directory, "00_Pdf")


def _ensure_mix_directory_exists(output_directory: str) -> bool:
    """
    Verifica l'esistenza della directory 00_MixOutput per i file di mix.
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
# FASE DI MIX
# =============================================================================

def mix_files(
    lbl_directory,
    entry_prompt,
    entry_extension,
    tree,
    report_text,
    include_prompt: bool,
    include_subdir: bool,
) -> None:
    """
    Esegue il MIX dei file sorgente per ogni subdirectory elencata nella tree.

    - lbl_directory: label che contiene la directory di lavoro
    - entry_prompt: text area con l'eventuale prompt da inserire in testa
    - entry_extension: campo estensioni (es. ".cpp" oppure ".php,.html,.css")
    - tree: treeview con le subdirectory (test01, test02, ...)
    - report_text: text area di log
    - include_prompt: se True, aggiunge il prompt in testa al mix
    - include_subdir: se True, aggiunge il nome della subdirectory nel mix
    """
    base_directory = _resolve_base_directory(lbl_directory)
    prompt_string = entry_prompt.get("1.0", "end").strip()
    extension_string = entry_extension.get().strip()

    if not base_directory:
        messagebox.showwarning(
            "Attenzione",
            "Seleziona prima una directory di lavoro.",
        )
        return

    exts = utils.parse_extensions(extension_string)
    if not exts:
        messagebox.showwarning(
            "Attenzione",
            "Specificare almeno una estensione di file (es. .cpp oppure .php,.html,.css).",
        )
        return

    mix_output_directory = _get_mix_output_directory(base_directory)
    os.makedirs(mix_output_directory, exist_ok=True)

    report_text.delete("1.0", "end")
    report_text.insert(
        "end",
        "Avvio fase di MIX.\n"
        "Directory base: " + base_directory + "\n"
        "Estensioni considerate: " + ", ".join(exts) + "\n\n",
    )

    for item in tree.get_children():
        values = list(tree.item(item, "values"))
        subdir = values[0]

        msg, mix_path = create_mix_file(
            base_directory,
            subdir,
            prompt_string,
            exts,
            mix_output_directory,
            include_prompt,
            include_subdir,
        )

        report_text.insert("end", msg)
        report_text.see("end")

        if mix_path:
            # la colonna "mix_file" è l'ultima
            if len(values) < 6:
                values.append(mix_path)
            else:
                values[5] = mix_path
            tree.item(item, values=values)


def create_mix_file(
    base_directory: str,
    subdir: str,
    prompt_string: str,
    extensions,
    output_directory: str,
    include_prompt: bool,
    include_subdir: bool,
) -> tuple[str, str | None]:
    """
    Crea il file di mix per una specifica subdirectory (es. 'test01').

    Restituisce:
      (messaggio_di_log, percorso_mix_file_oppure_None)
    """
    full_path = os.path.join(base_directory, subdir)
    mix_file_path = os.path.join(output_directory, subdir + "_mix.txt")

    try:
        files_to_mix = []

        for root, _dirs, files in os.walk(full_path):
            for file_name in files:
                lower_name = file_name.lower()
                for ext in extensions:
                    if lower_name.endswith(ext):
                        files_to_mix.append(os.path.join(root, file_name))
                        break

        if not files_to_mix:
            message = (
                "Nessun file con estensioni "
                + ", ".join(extensions)
                + " trovato nella subdirectory "
                + subdir
                + ".\nFile di mix NON creato.\n"
            )
            return message, None

        with open(mix_file_path, "w", encoding="utf-8") as mix_file:
            if include_prompt and prompt_string:
                mix_file.write(prompt_string + "\n")

            if include_subdir:
                mix_file.write(subdir + "\n\n")

            for file_path in files_to_mix:
                try:
                    with open(file_path, "r", encoding="utf-8") as current_file:
                        content = current_file.read()
                except UnicodeDecodeError:
                    with open(
                        file_path,
                        "r",
                        encoding="latin-1",
                        errors="replace",
                    ) as current_file:
                        content = current_file.read()

                mix_file.write(
                    "###############################################################\n\n"
                )
                mix_file.write(os.path.basename(file_path) + "\n" + content + "\n")

        message = (
            "Mix completato per "
            + subdir
            + ": file con estensioni "
            + ", ".join(extensions)
            + " uniti con successo in "
            + os.path.basename(mix_file_path)
            + ".\n"
        )
        return message, mix_file_path

    except Exception as exc:
        return "Errore durante il mix per " + subdir + ": " + str(exc) + "\n", None


# =============================================================================
# FASE DI EXPORT (PDF)
# =============================================================================

def create_individual_pdfs(directory_source, report_text) -> None:
    """
    Crea un PDF individuale per ogni file *_mix.txt presente in 00_MixOutput.

    I PDF vengono salvati nella cartella 00_Pdf sotto la directory di lavoro.
    """
    base_directory = _resolve_base_directory(directory_source)

    if not base_directory:
        messagebox.showwarning(
            "Attenzione",
            "Seleziona prima una directory di lavoro.",
        )
        return

    mix_output_directory = _get_mix_output_directory(base_directory)
    if not _ensure_mix_directory_exists(mix_output_directory):
        return

    pdf_output_directory = _get_pdf_output_directory(base_directory)
    os.makedirs(pdf_output_directory, exist_ok=True)

    report_text.insert(
        "end",
        "Creazione PDF multipli.\n"
        "Directory dei file di mix: " + mix_output_directory + "\n"
        "Directory di output PDF: " + pdf_output_directory + "\n",
    )

    styles = getSampleStyleSheet()
    monospace_style = ParagraphStyle(
        "Monospace",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=10,
        leading=12,
    )

    max_char_width = 75
    created_count = 0

    for file_name in sorted(os.listdir(mix_output_directory)):
        if not file_name.endswith("_mix.txt"):
            continue

        txt_path = os.path.join(mix_output_directory, file_name)
        base_name = os.path.splitext(file_name)[0]
        pdf_path = os.path.join(pdf_output_directory, base_name + ".pdf")

        try:
            try:
                with open(txt_path, "r", encoding="utf-8") as file_handle:
                    content = file_handle.read()
            except UnicodeDecodeError:
                with open(
                    txt_path,
                    "r",
                    encoding="latin-1",
                    errors="replace",
                ) as file_handle:
                    content = file_handle.read()

            wrapped_content = wrap_preserve_indent(content, max_char_width)
            lines = wrapped_content.splitlines()
            cleaned_content = "\n".join(lines)

            story = [Preformatted(cleaned_content, monospace_style)]

            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            doc.build(story)

            created_count = created_count + 1
            report_text.insert(
                "end",
                "Creato PDF: " + os.path.basename(pdf_path) + "\n",
            )

        except Exception as exc:
            report_text.insert(
                "end",
                "Errore durante la creazione del PDF "
                + pdf_path
                + ": "
                + str(exc)
                + "\n",
            )

    if created_count == 0:
        report_text.insert(
            "end",
            "Nessun file *_mix.txt trovato in 00_MixOutput: nessun PDF creato.\n",
        )
    else:
        report_text.insert(
            "end",
            "Creazione PDF multipli completata.\n"
            "Totale PDF creati: "
            + str(created_count)
            + "\n",
        )

    report_text.see("end")


def merge_all_files(directory_source, report_text) -> None:
    """
    Crea il PDF unico finale, pronto per PdfMegaMerge / stampa fronte-retro.

    - Se non trova PDF individuali in 00_Pdf, lancia prima create_individual_pdfs().
    - Legge tutti i PDF da 00_Pdf (eccetto il finale stesso).
    - Per ogni elaborato garantisce un numero PARI di pagine
      (se dispari, aggiunge una pagina bianca).
    - Salva il PDF finale in 00_Pdf come 00_MEGAmerged_output_final.pdf.
    """
    base_directory = _resolve_base_directory(directory_source)

    if not base_directory:
        messagebox.showwarning(
            "Attenzione",
            "Seleziona prima una directory di lavoro.",
        )
        return

    mix_output_directory = _get_mix_output_directory(base_directory)
    if not _ensure_mix_directory_exists(mix_output_directory):
        return

    pdf_output_directory = _get_pdf_output_directory(base_directory)
    os.makedirs(pdf_output_directory, exist_ok=True)

    final_pdf_path = os.path.join(
        pdf_output_directory,
        "00_MEGAmerged_output_final.pdf",
    )

    pdf_files = []

    for file_name in sorted(os.listdir(pdf_output_directory)):
        if not file_name.lower().endswith(".pdf"):
            continue
        if file_name.startswith("00_MEGAmerged_output_final"):
            continue

        pdf_files.append(os.path.join(pdf_output_directory, file_name))

    if not pdf_files:
        report_text.insert(
            "end",
            "Nessun PDF individuale trovato in 00_Pdf.\n"
            "Avvio automatico di 'Crea PDF multipli'...\n",
        )
        report_text.see("end")

        create_individual_pdfs(base_directory, report_text)

        pdf_files = []
        for file_name in sorted(os.listdir(pdf_output_directory)):
            if not file_name.lower().endswith(".pdf"):
                continue
            if file_name.startswith("00_MEGAmerged_output_final"):
                continue

            pdf_files.append(os.path.join(pdf_output_directory, file_name))

        if not pdf_files:
            report_text.insert(
                "end",
                "Impossibile procedere con il MEGAmerge: nessun PDF da unire in 00_Pdf.\n",
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

            for page in reader.pages:
                writer.add_page(page)

            if num_pages % 2 == 1 and num_pages > 0:
                first_page = reader.pages[0]
                width = first_page.mediabox.width
                height = first_page.mediabox.height
                writer.add_blank_page(width=width, height=height)

                report_text.insert(
                    "end",
                    os.path.basename(pdf_path)
                    + ": "
                    + str(num_pages)
                    + " pagine -> aggiunta 1 pagina bianca "
                    + "(totale nel blocco: "
                    + str(num_pages + 1)
                    + ").\n",
                )
            else:
                report_text.insert(
                    "end",
                    os.path.basename(pdf_path)
                    + ": "
                    + str(num_pages)
                    + " pagine (già pari).\n",
                )

        with open(final_pdf_path, "wb") as out_file:
            writer.write(out_file)

        report_text.insert(
            "end",
            "MEGAmerge completato.\n"
            "File PDF finale creato in 00_Pdf:\n"
            + final_pdf_path
            + "\n",
        )
        report_text.see("end")

    except Exception as exc:
        report_text.insert(
            "end",
            "Errore durante il merge dei PDF in un unico file: "
            + str(exc)
            + "\n",
        )
        report_text.see("end")
