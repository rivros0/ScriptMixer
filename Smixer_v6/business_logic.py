import os
import textwrap
from tkinter import messagebox

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Preformatted

from PyPDF2 import PdfReader, PdfWriter


# =============================================================================
#  FUNZIONI DI SUPPORTO
# =============================================================================


def _normalize_text(content):
    """
    Normalizza il testo rimuovendo caratteri che possono creare problemi nei PDF:
    - sostituisce TAB con 4 spazi;
    - sostituisce spazio non-breakable (\u00a0) con spazio normale.
    """
    if content is None:
        return ""
    text = str(content)
    text = text.replace("\t", "    ")
    text = text.replace("\u00a0", " ")
    return text


def _parse_extensions(ext_value):
    """
    Converte il contenuto del campo estensioni in una lista normalizzata.

    Esempi accettati:
      ".php"
      "php html css"
      ".php, .html, .css"

    Restituisce sempre un elenco del tipo: [".php", ".html", ".css"]
    """
    if ext_value is None:
        return []

    if isinstance(ext_value, list) or isinstance(ext_value, tuple):
        raw_items = []
        i = 0
        while i < len(ext_value):
            raw_items.append(str(ext_value[i]))
            i = i + 1
        joined = " ".join(raw_items)
    else:
        joined = str(ext_value)

    separators = [",", ";"]
    for sep in separators:
        joined = joined.replace(sep, " ")
    parts = joined.split()

    extensions = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if part != "":
            if not part.startswith("."):
                part = "." + part
            extensions.append(part.lower())
        i = i + 1

    # Se l'utente ha lasciato vuoto, per sicurezza ritorna lista vuota
    return extensions


def _extract_directory(arg):
    """
    Prova a ricavare una path di directory da vari tipi di argomento:
    - StringVar → usa .get()
    - Label     → usa .cget("text") ed estrae la parte dopo i due punti, se presenti
    - stringa   → usa direttamente il valore
    """
    if arg is None:
        return ""

    # StringVar o oggetto con .get()
    if hasattr(arg, "get"):
        try:
            value = arg.get()
        except Exception:
            value = str(arg)
        return str(value).strip()

    # Label o simili con .cget("text")
    if hasattr(arg, "cget"):
        try:
            text = arg.cget("text")
        except Exception:
            text = str(arg)
        text = str(text)
        if ":" in text:
            pieces = text.split(":", 1)
            text = pieces[1]
        return text.strip()

    # Fallback: lo tratto come stringa
    return str(arg).strip()


def wrap_preserve_indent(text, width):
    """
    Esegue il wrapping del testo preservando l'indentazione di ogni riga.
    Usato per rendere più leggibile il codice nei PDF.
    """
    if text is None:
        return ""

    lines = str(text).splitlines()
    wrapped_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        leading_spaces = len(line) - len(line.lstrip(" "))
        indent = " " * leading_spaces
        stripped = line.lstrip(" ")
        if stripped == "":
            wrapped_lines.append("")
        else:
            wrapped = textwrap.wrap(stripped, width=width - leading_spaces) or [""]
            j = 0
            while j < len(wrapped):
                wrapped_lines.append(indent + wrapped[j])
                j = j + 1
        i = i + 1

    return "\n".join(wrapped_lines)


# =============================================================================
#  CREAZIONE FILE MIX
# =============================================================================


def mix_files(lbl_or_var_directory,
              entry_prompt,
              entry_extension,
              tree,
              report_text,
              include_prompt,
              include_subdir):
    """
    Funzione di alto livello richiamata dalla scheda Correzione.

    Parametri attesi (compatibile con versioni precedenti):
      - lbl_or_var_directory : Label, StringVar o stringa con la directory di lavoro
      - entry_prompt         : Text widget con il prompt
      - entry_extension      : Entry con estensioni (una o più)
      - tree                 : Treeview con elenco subdirectory test
      - report_text          : Text widget per log
      - include_prompt       : bool, include o meno il prompt nel mix
      - include_subdir       : bool, include o meno il nome della subdir nel mix
    """
    base_dir = _extract_directory(lbl_or_var_directory)

    report_text.delete("1.0", "end")

    if base_dir == "" or not os.path.isdir(base_dir):
        messagebox.showwarning(
            "Attenzione",
            "Directory di lavoro non valida.\nSeleziona una directory dalla GUI."
        )
        return

    prompt_string = entry_prompt.get("1.0", "end").strip()
    extensions_text = entry_extension.get()
    extensions = _parse_extensions(extensions_text)

    if len(extensions) == 0:
        messagebox.showwarning(
            "Attenzione",
            "Specifica almeno una estensione file (es: .php .html .css)."
        )
        return

    output_directory = os.path.join(base_dir, "00_MixOutput")
    os.makedirs(output_directory, exist_ok=True)

    # Svuota il log
    report_text.insert("end", "Inizio creazione dei file di mix...\n")

    # Per ogni riga della tabella (subdirectory testXX)
    items = tree.get_children()
    idx = 0
    while idx < len(items):
        item_id = items[idx]
        values = tree.item(item_id, "values")
        if values and len(values) > 0:
            subdir = str(values[0]).strip()
            if subdir != "" and not subdir.startswith("00"):
                msg, _ = create_mix_file(
                    base_directory=base_dir,
                    subdir=subdir,
                    prompt_string=prompt_string,
                    extensions=extensions,
                    output_directory=output_directory,
                    include_prompt=include_prompt,
                    include_subdir=include_subdir,
                )
                report_text.insert("end", msg)
        idx = idx + 1

    report_text.insert("end", "Creazione dei file di mix completata.\n")
    report_text.see("end")


def create_mix_file(base_directory,
                    subdir,
                    prompt_string,
                    extensions,
                    output_directory,
                    include_prompt,
                    include_subdir):
    """
    Crea il file di mix per una specifica subdirectory (es. test01).

    - Cerca ricorsivamente tutti i file con le estensioni indicate;
    - Ignora qualunque sottocartella che inizi con '00';
    - Scrive un file '<subdir>_mix.txt' nella directory 00_MixOutput.
    """
    if not isinstance(extensions, list) and not isinstance(extensions, tuple):
        extensions = _parse_extensions(extensions)

    normalized_exts = []
    i = 0
    while i < len(extensions):
        ext = str(extensions[i]).strip().lower()
        if ext != "":
            if not ext.startswith("."):
                ext = "." + ext
            normalized_exts.append(ext)
        i = i + 1

    full_path = os.path.join(base_directory, subdir)
    mix_file_path = os.path.join(output_directory, subdir + "_mix.txt")

    try:
        files_to_mix = []

        for root, dirs, files in os.walk(full_path):
            # esclude sottocartelle che iniziano con '00'
            safe_dirs = []
            j = 0
            while j < len(dirs):
                dname = str(dirs[j])
                if not dname.startswith("00"):
                    safe_dirs.append(dname)
                j = j + 1
            dirs[:] = safe_dirs

            k = 0
            while k < len(files):
                file_name = files[k]
                lower_name = file_name.lower()
                match = False

                m = 0
                while m < len(normalized_exts):
                    ext = normalized_exts[m]
                    if lower_name.endswith(ext):
                        match = True
                        break
                    m = m + 1

                if match:
                    files_to_mix.append(os.path.join(root, file_name))
                k = k + 1

        if len(files_to_mix) == 0:
            message = (
                "Nessun file con estensioni "
                + ", ".join(normalized_exts)
                + " trovato nella subdirectory "
                + subdir
                + " (sottocartelle '00*' escluse). File di mix NON creato.\n"
            )
            return message, None

        with open(mix_file_path, "w", encoding="utf-8") as mix_file:
            if include_prompt and prompt_string:
                mix_file.write(_normalize_text(prompt_string) + "\n")

            if include_subdir:
                mix_file.write(subdir + "\n\n")

            z = 0
            while z < len(files_to_mix):
                file_path = files_to_mix[z]
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

                content = _normalize_text(content)

                mix_file.write(
                    "###############################################################\n\n"
                )
                mix_file.write(os.path.basename(file_path) + "\n" + content + "\n")
                z = z + 1

        message = (
            "Mix completato per "
            + subdir
            + ": file con estensioni "
            + ", ".join(normalized_exts)
            + " uniti con successo.\n"
        )
        return message, mix_file_path

    except Exception as exc:
        message = "Errore durante il mix per " + subdir + ": " + str(exc) + "\n"
        return message, None


# =============================================================================
#  CREAZIONE PDF INDIVIDUALI DA *_mix.txt
# =============================================================================


def create_individual_pdfs(base_directory, report_text):
    """
    Crea un PDF per ogni file *_mix.txt presente in 00_MixOutput.

    - Usa un font monospaziato (Courier) per preservare l'indentazione;
    - Ignora qualunque file che inizi con '00';
    - Salva i PDF in 00_Pdf con lo stesso nome base del mix.
    """
    base_dir = _extract_directory(base_directory)
    if base_dir == "" or not os.path.isdir(base_dir):
        messagebox.showwarning(
            "Attenzione",
            "Directory di lavoro non valida per la creazione dei PDF."
        )
        return

    mix_output_directory = os.path.join(base_dir, "00_MixOutput")
    pdf_output_directory = os.path.join(base_dir, "00_Pdf")

    if not os.path.isdir(mix_output_directory):
        messagebox.showwarning(
            "Attenzione",
            "La directory 00_MixOutput non esiste. Esegui prima la fase di mix."
        )
        return

    try:
        os.makedirs(pdf_output_directory, exist_ok=True)
    except Exception as exc:
        messagebox.showerror(
            "Errore",
            "Impossibile creare la directory 00_Pdf:\n" + str(exc)
        )
        return

    styles = getSampleStyleSheet()
    monospace_style = ParagraphStyle(
        "Monospace",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=11,
    )

    max_char_width = 95

    report_text.insert("end", "Inizio creazione dei PDF individuali...\n")
    report_text.see("end")

    created_count = 0

    names = sorted(os.listdir(mix_output_directory))
    i = 0
    while i < len(names):
        file_name = names[i]
        i = i + 1

        if file_name.startswith("00"):
            continue

        if not file_name.endswith("_mix.txt"):
            continue

        mix_path = os.path.join(mix_output_directory, file_name)

        try:
            with open(mix_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(mix_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        content = _normalize_text(content)
        wrapped = wrap_preserve_indent(content, max_char_width)

        pdf_name = os.path.splitext(file_name)[0] + ".pdf"
        pdf_path = os.path.join(pdf_output_directory, pdf_name)

        try:
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = [Preformatted(wrapped, monospace_style)]
            doc.build(story)
            created_count = created_count + 1
            report_text.insert("end", "Creato PDF: " + pdf_name + "\n")
            report_text.see("end")
        except Exception as exc:
            report_text.insert(
                "end",
                "Errore nella creazione del PDF da "
                + file_name
                + ": "
                + str(exc)
                + "\n",
            )
            report_text.see("end")

    report_text.insert(
        "end",
        "Creazione dei PDF individuali completata. Totale PDF creati: "
        + str(created_count)
        + "\n",
    )
    report_text.see("end")


# =============================================================================
#  MEGAMERGE PDF (BACKWARD COMPATIBLE)
# =============================================================================


def merge_all_files(base_directory, report_text,  verifica_name=None):
    """
    Esegue il merge di tutti i PDF presenti in 00_Pdf in un unico file:

      - usa solo i PDF che NON iniziano con '00';
      - per ogni elaborato, assicura un numero PARI di pagine
        aggiungendo una pagina bianca se necessario;
      - salva il risultato come 00_MEGAmerged_output_final.pdf
        all'interno di 00_Pdf.

    Nota: questa funzione viene mantenuta per compatibilità con versioni
    precedenti. La logica è coerente con quella usata nella scheda Export.
    """
    base_dir = _extract_directory(base_directory)
    if base_dir == "" or not os.path.isdir(base_dir):
        messagebox.showwarning(
            "Attenzione",
            "Directory di lavoro non valida per il MEGAmerge."
        )
        return

    pdf_output_directory = os.path.join(base_dir, "00_Pdf")
    if not os.path.isdir(pdf_output_directory):
        messagebox.showwarning(
            "Attenzione",
            "La directory 00_Pdf non esiste. Crea prima i PDF multipli."
        )
        return

    names = sorted(os.listdir(pdf_output_directory))
    pdf_files = []

    i = 0
    while i < len(names):
        file_name = names[i]
        i = i + 1

        if not file_name.lower().endswith(".pdf"):
            continue
        if file_name.startswith("00"):
            # esclude PDF di servizio e merge finali
            continue

        pdf_files.append(os.path.join(pdf_output_directory, file_name))

    if len(pdf_files) == 0:
        messagebox.showwarning(
            "Attenzione",
            "Nessun PDF individuale trovato in 00_Pdf per il MEGAmerge."
        )
        return

    writer = PdfWriter()
    report_text.insert(
        "end",
        "Inizio MEGAmerge con pagine pari per ogni elaborato...\n",
    )
    report_text.see("end")

    idx = 0
    while idx < len(pdf_files):
        path = pdf_files[idx]
        name = os.path.basename(path)
        idx = idx + 1

        try:
            reader = PdfReader(path)
        except Exception as exc:
            report_text.insert(
                "end",
                "Errore lettura PDF '"
                + name
                + "': "
                + str(exc)
                + "\n",
            )
            report_text.see("end")
            continue

        num_pages = len(reader.pages)

        p = 0
        while p < num_pages:
            writer.add_page(reader.pages[p])
            p = p + 1

        if num_pages % 2 != 0 and num_pages > 0:
            first_page = reader.pages[0]
            width = first_page.mediabox.width
            height = first_page.mediabox.height
            writer.add_blank_page(width=width, height=height)
            report_text.insert(
                "end",
                name
                + ": "
                + str(num_pages)
                + " pagine -> aggiunta 1 pagina bianca (totale blocco: "
                + str(num_pages + 1)
                + ").\n",
            )
        else:
            report_text.insert(
                "end",
                name
                + ": "
                + str(num_pages)
                + " pagine (già pari).\n",
            )

        report_text.see("end")

    
    
    # nome verifica pulito
    safe_verifica = ""
    if verifica_name:
        safe_verifica = str(verifica_name).strip()
        for bad in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            safe_verifica = safe_verifica.replace(bad, "_")

    if safe_verifica:
        final_name = f"00_MEGAmerged_{safe_verifica}_ELABORATI.pdf"
    else:
        final_name = "00_MEGAmerged_output_ELABORATI.pdf"

    final_pdf_path = os.path.join(pdf_output_directory, final_name)

    ###
    try:
        with open(final_pdf_path, "wb") as f_out:
            writer.write(f_out)
        report_text.insert(
            "end",
            "MEGAmerge completato. File PDF finale creato:\n"
            + final_pdf_path
            + "\n",
        )
        report_text.see("end")
    except Exception as exc:
        report_text.insert(
            "end",
            "Errore durante la scrittura del PDF finale: "
            + str(exc)
            + "\n",
        )
        report_text.see("end")
