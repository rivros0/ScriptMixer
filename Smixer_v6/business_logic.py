import os
import textwrap
from tkinter import messagebox
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Preformatted, PageBreak

def mix_files(lbl_directory, entry_prompt, entry_extension, tree, report_text, include_prompt, include_subdir):
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    prompt_string = entry_prompt.get("1.0", "end").strip()
    extension = entry_extension.get()
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    os.makedirs(output_directory, exist_ok=True)
    report_text.delete("1.0", "end")
    for item in tree.get_children():
        subdir = tree.item(item, "values")[0]
        mix_result = create_mix_file(selected_directory, subdir, prompt_string, extension, output_directory, include_prompt, include_subdir)
        report_text.insert("end", mix_result)

def create_mix_file(base_directory, subdir, prompt_string, extension, output_directory, include_prompt, include_subdir):
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
                    # Se la lettura in utf-8 fallisce, utilizza latin-1 con sostituzione degli errori
                    with open(file_path, "r", encoding="latin-1", errors="replace") as current_file:
                        content = current_file.read()
                mix_file.write("###############################################################" + "\n\n")
                mix_file.write(f"{os.path.basename(file_path)}\n{content}\n")
        return f"Mix completato per {subdir}: file con estensione {extension} uniti con successo.\n"
    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n"



def wrap_preserve_indent(text, width):
    """
    Per ogni riga del testo, se la lunghezza supera 'width', la riga viene spezzata
    mantenendo l'indentazione originale.
    """
    lines = text.splitlines()
    wrapped_lines = []
    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(line)
        else:
            # Recupera gli spazi iniziali (indentazione)
            leading = len(line) - len(line.lstrip())
            indent = line[:leading]
            wrapped = textwrap.fill(line, width=width, initial_indent=indent, subsequent_indent=indent, drop_whitespace=False)
            wrapped_lines.append(wrapped)
    return "\n".join(wrapped_lines)

def merge_all_files(lbl_directory, report_text):
    """
    Genera un file PDF contenente il merge dei file di mix.
    Ogni file viene letto, le righe troppo lunghe vengono avvolte tramite wrap_preserve_indent,
    il contenuto viene inserito come blocco Preformatted (che mantiene indentazioni e spaziatura)
    e viene inserita una interruzione di pagina dopo ogni file.
    """
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    merged_pdf_path = os.path.join(output_directory, "00_MEGAmerged_output.pdf")
    
    if not os.path.exists(output_directory):
        messagebox.showwarning("Attenzione", "La directory 00_MixOutput non esiste. Esegui prima la fase di mix.")
        return

    try:
        doc = SimpleDocTemplate(merged_pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        # Definisce uno stile monospace per garantire l'uniformità delle indentazioni
        monospace_style = ParagraphStyle('Monospace', parent=styles['Normal'], fontName='Courier', fontSize=10, leading=12)
        story = []
        
        # Imposta il numero massimo di caratteri per riga (questo valore può essere adattato)
        max_char_width = 75
        
        for file_name in sorted(os.listdir(output_directory)):
            if file_name.endswith("_mix.txt"):
                file_path = os.path.join(output_directory, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Applica il wrapping per evitare il troncamento delle righe
                wrapped_content = wrap_preserve_indent(content, max_char_width)
                story.append(Preformatted(wrapped_content, monospace_style))
                story.append(PageBreak())
        
        doc.build(story)
        report_text.insert("end", f"Merge completato. File PDF creato: {merged_pdf_path}\n")
    except Exception as e:
        report_text.insert("end", f"Errore durante il merge dei file in PDF: {str(e)}\n")
