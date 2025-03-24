import os
from tkinter import messagebox

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
                mix_file.write("###############################################################" + "\n\n")
            if include_subdir:
                mix_file.write(subdir + "\n\n")
                mix_file.write("###############################################################" + "\n\n")
            for file_path in files_to_mix:
                with open(file_path, "r", encoding="utf-8") as current_file:
                    mix_file.write(f"{os.path.basename(file_path)}\n{current_file.read()}\n")
        return f"Mix completato per {subdir}: file con estensione {extension} uniti con successo.\n"
    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n"

def merge_all_files(lbl_directory, report_text):
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    merged_file_path = os.path.join(output_directory, "00_MEGAmerged_output.txt")
    if not os.path.exists(output_directory):
        messagebox.showwarning("Attenzione", "La directory 00_MixOutput non esiste. Esegui prima la fase di mix.")
        return
    try:
        with open(merged_file_path, "w", encoding="utf-8") as merged_file:
            for file_name in sorted(os.listdir(output_directory)):
                if file_name.endswith("_mix.txt"):
                    file_path = os.path.join(output_directory, file_name)
                    with open(file_path, "r", encoding="utf-8") as f:
                        merged_file.write(f.read())
                        merged_file.write("\n\f\n")
        report_text.insert("end", f"Merge completato. File creato: {merged_file_path}\n")
    except Exception as e:
        report_text.insert("end", f"Errore durante il merge dei file: {str(e)}\n")
