import os
import textwrap
from tkinter import messagebox

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Preformatted,
)
from PyPDF2 import PdfReader, PdfWriter

import utils  # per parse_extensions


# =============================================================================
#  UTILITÀ GENERALI
# =============================================================================

def wrap_preserve_indent(text: str, width: int) -> str:
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
    if isinstance(directory_source, str):
        return directory_source.strip()

    try:
        text = directory_source.cget("text")
    except Exception:
        return str(directory_source).strip()

    return text.replace("Directory selezionata:", "").strip()


def _get_mix_output_directory(base_directory: str) -> str:
    return os.path.join(base_directory, "00_MixOutput")


def _ensure_mix_directory_exists(output_directory: str) -> bool:
    if not os.path.exists(output_directory):
        messagebox.showwarning(
            "Attenzione",
            "La directory 00_MixOutput non esiste.\n"
            "Esegui prima la fase di mix dei sorgenti.",
        )
        return False
    return True


# =============================================================================
#  FASE DI MIX
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
    base_directory = _resolve_base_directory(lbl_directory)
    prompt_string = entry_prompt.get("1.0", "end").strip()
    extension_string = entry_extension.get().strip()

    if not base_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
        return

    exts = utils.parse_extensions(extension_string)

    if not exts:
        messagebox.showwarning(
            "Attenzione",
            "Specificare almeno una estensione di file (es. .cpp oppure .php,.html,.css).",
        )
        return

    output_directory = _get_mix_output_directory(base_directory)
    os.makedirs(output_directory, exist_ok=True)

    report_text.delete("1.0", "end")
    report_text.insert(
        "end",
        "Avvio fase di MIX.\n"
        f"Directory base: {base_directory}\n"
        f"Estensioni considerate: {', '.join(exts)}\n\n",
    )

    # per ogni riga della tree (subdirectory)
    for item in tree.get_children():
        values = list(tree.item(item, "values"))
        subdir = values[0]

        msg, mix_path = create_mix_file(
            base_directory,
            subdir,
            prompt_string,
            exts,
            output_directory,
            include_prompt,
            include_subdir,
        )
        report_text.insert("end", msg)
        report_text.see("end")

        # se abbiamo creato il mix, aggiorniamo la colonna "mix_file"
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

    Restituisce: (messaggio_log, percorso_mix_file_oppure_None)
    """
    full_path = os.path.join(base_directory, subdir)
    mix_file_path = os.path.join(output_directory, f"{subdir}_mix.txt")

    try:
        files_to_mix = []
        for root, _dirs, files in os.walk(full_path):
            for file in files:
                fname = file.lower()
                if any(fname.endswith(ext) for ext in extensions):
                    files_to_mix.append(os.path.join(root, file))

        if not files_to_mix:
            return (
                f"Nessun file con estensioni {', '.join(extensions)} trovato nella "
                f"subdirectory {subdir}. File di mix NON creato.\n",
                None,
            )

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
                mix_file.write(f"{os.path.basename(file_path)}\n{content}\n")

        return (
            f"Mix completato per {subdir}: file con estensioni "
            f"{', '.join(extensions)} uniti con successo in "
            f"{os.path.basename(mix_file_path)}.\n",
            mix_file_path,
        )

    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n", None


# =============================================================================
#  FASE DI EXPORT (PDF) - invariata
# =============================================================================

def create_individual_pdfs(directory_source, report_text):
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

    max_char_width = 75
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

        wrapped_content = wrap_preserve_indent(content, max_char_width)
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
            f"Creazione PDF multipli completata.\nTotale PDF creati: {created_count}\n",
        )

    report_text.see("end")


def merge_all_files(directory_source, report_text):
    base_directory = _resolve_base_directory(directory_source)
    if not base_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
        return

    output_directory = _get_mix_output_directory(base_directory)
    if not _ensure_mix_directory_exists(output_directory):
        return

    final_pdf_path = os.path.join(output_directory, "00_MEGAmerged_output_final.pdf")

    pdf_files = sorted(
        [
            os.path.join(output_directory, f)
            for f in os.listdir(output_directory)
            if f.endswith(".pdf")
            and not f.startswith("00_MEGAmerged_output_final")
        ]
    )

    if not pdf_files:
        report_text.insert(
            "end",
            "Nessun PDF individuale trovato in 00_MixOutput.\n"
            "Avvio automatico di 'Crea PDF multipli'...\n",
        )
        report_text.see("end")

        create_individual_pdfs(base_directory, report_text)

        pdf_files = sorted(
            [
                os.path.join(output_directory, f)
                for f in os.listdir(output_directory)
                if f.endswith(".pdf")
                and not f.startswith("00_MEGAmerged_output_final")
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

            for page in reader.pages:
                writer.add_page(page)

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

        with open(final_pdf_path, "wb") as out_f:
            writer.write(out_f)

        report_text.insert(
            "end",
            f"MEGAmerge completato.\nFile PDF finale creato: {final_pdf_path}\n",
        )
        report_text.see("end")

    except Exception as e:
        report_text.insert(
            "end",
            f"Errore durante il merge dei PDF in un unico file: {e}\n",
        )
        report_text.see("end")
