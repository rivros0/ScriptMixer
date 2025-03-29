import os
import textwrap
import io
from tkinter import messagebox
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Preformatted,
    PageBreak,
    Spacer,
    KeepTogether
)
from PyPDF2 import PdfReader, PdfWriter

# Array globale per salvare i marker: ogni elemento è una tupla (marker_text, subdir)
markers = []

def wrap_preserve_indent(text, width):
    """
    Avvolge il testo riga per riga mantenendo l'indentazione.
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
                drop_whitespace=False
            )
            wrapped_lines.append(wrapped)
    return "\n".join(wrapped_lines)

def mix_files(lbl_directory, entry_prompt, entry_extension, tree, report_text, include_prompt, include_subdir):
    """
    Crea il file di mix per ciascuna subdirectory e li scrive su disco.
    Durante la creazione viene utilizzata la stringa della subdirectory come marker,
    che viene salvato nell'array globale markers.
    """
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    prompt_string = entry_prompt.get("1.0", "end").strip()
    extension = entry_extension.get()
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    os.makedirs(output_directory, exist_ok=True)
    report_text.delete("1.0", "end")
    global markers
    markers = []
    for item in tree.get_children():
        subdir = tree.item(item, "values")[0]
        mix_result = create_mix_file(selected_directory, subdir, prompt_string, extension, output_directory, include_prompt, include_subdir)
        report_text.insert("end", mix_result)

def create_mix_file(base_directory, subdir, prompt_string, extension, output_directory, include_prompt, include_subdir):
    """
    Crea il file di mix per una specifica subdirectory.
    In questo esempio, usiamo il nome della subdirectory come marker.
    """
    full_path = os.path.join(base_directory, subdir)
    mix_file_path = os.path.join(output_directory, f"{subdir}_mix.txt")
    try:
        files_to_mix = []
        for root, dirs, files in os.walk(full_path):
            for file in files:
                if file.endswith(extension):
                    files_to_mix.append(os.path.join(root, file))
        if not files_to_mix:
            return f"Nessun file con estensione {extension} trovato nella subdirectory {subdir}. File di mix non creato.\n"
        with open(mix_file_path, "w", encoding="utf-8") as mix_file:
            if include_prompt:
                mix_file.write(prompt_string + "\n")
            if include_subdir:
                mix_file.write(subdir + "\n\n")
            for file_path in files_to_mix:
                try:
                    with open(file_path, "r", encoding="utf-8") as current_file:
                        content = current_file.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1", errors="replace") as current_file:
                        content = current_file.read()
                mix_file.write("###############################################################\n\n")
                mix_file.write(f"{os.path.basename(file_path)}\n{content}\n")
        # Usa il nome della subdirectory come marker
        global markers
        markers.append((subdir, subdir))
        return f"Mix completato per {subdir}: file con estensione {extension} uniti con successo.\n"
    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n"

def merge_all_files(lbl_directory, report_text):
    """
    Genera un PDF finale in cui ogni blocco (contenuto di un file _mix.txt) viene
    esteso a un numero pari di pagine.
    """
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    final_pdf_path = os.path.join(output_directory, "00_MEGAmerged_output_final.pdf")
    
    if not os.path.exists(output_directory):
        messagebox.showwarning("Attenzione", "La directory 00_MixOutput non esiste. Esegui prima la fase di mix.")
        return

    try:
        styles = getSampleStyleSheet()
        monospace_style = ParagraphStyle(
            'Monospace',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=10,
            leading=12
        )
        max_char_width = 75
        
        # Imposta l'altezza disponibile in una pagina. 
        # Si assume che i margini di default siano 72 pt in alto e 72 pt in basso.
        available_height = A4[1] - 144
        
        story = []
        # Per ciascun file _mix.txt, costruiamo il blocco
        for file_name in sorted(os.listdir(output_directory)):
            if file_name.endswith("_mix.txt"):
                file_path = os.path.join(output_directory, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                wrapped_content = wrap_preserve_indent(content, max_char_width)
                # Rimuovi righe vuote iniziali e finali
                lines = [line for line in wrapped_content.splitlines() if line.strip() != ""]
                cleaned_content = "\n".join(lines)
                num_lines = len(lines)
                block_height = num_lines * monospace_style.leading
                pages = block_height // available_height
                if block_height % available_height > 0:
                    pages += 1
                extra_space = 0
                if pages % 2 != 0:
                    remainder = block_height % available_height
                    extra_space = available_height - remainder if remainder > 0 else available_height
                block_flowables = []
                block_flowables.append(Preformatted(cleaned_content, monospace_style))
                if extra_space > 0:
                    block_flowables.append(Spacer(1, extra_space))
                block_flowables.append(PageBreak())
                story.append(KeepTogether(block_flowables))

        final_doc = SimpleDocTemplate(final_pdf_path, pagesize=A4)
        final_doc.build(story)
        
        report_text.insert("end", f"Merge completato. File PDF finale creato: {final_pdf_path}\n")
        report_text.see("end")
    except Exception as e:
        report_text.insert("end", f"Errore durante il merge dei file in PDF: {str(e)}\n")
        report_text.see("end")
