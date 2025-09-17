import os
import json
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox


# === FUNZIONI DI SCANSIONE GENERICHE === #

def update_directory_listing(directory, entry_extension, report_text):
    """Aggiorna la lista dei file trovati in tutte le sottocartelle."""
    report_text.delete("1.0", "end")
    file_extension = entry_extension.get().strip()
    if file_extension and not file_extension.startswith('.'):
        file_extension = f".{file_extension}"

    for root, dirs, files in os.walk(directory):
        for file in files:
            if not file_extension or file.endswith(file_extension):
                file_path = os.path.join(root, file)
                report_text.insert("end", f"{file_path}\n")


def update_subdirectories_list(selected_directory, tree, entry_extension):
    """Popola la treeview con info sulle sottocartelle."""
    subdirectories = [d for d in os.listdir(selected_directory)
                      if os.path.isdir(os.path.join(selected_directory, d))]
    subdirectories.sort()
    tree.delete(*tree.get_children())
    for subdir in subdirectories:
        check_directory_content(selected_directory, subdir, tree, entry_extension)


def check_directory_content(base_directory, subdir, tree, entry_extension):
    """Conta cartelle, file e file con estensione specificata in una sottocartella."""
    full_path = os.path.join(base_directory, subdir)
    num_folders, num_files, num_extension_files, extension_files = count_directory_content(full_path, entry_extension)
    mix_file_path = os.path.join(base_directory, "00_MixOutput", f"{subdir}_mix.txt")
    button_text = "CopiaInClipboard" if os.path.exists(mix_file_path) else "-----"

    tree.insert("", "end",
                values=(subdir, num_folders, num_files, num_extension_files, ", ".join(extension_files), button_text))


def count_directory_content(directory, entry_extension):
    """Conta cartelle, file e file con l'estensione indicata."""
    num_folders = 0
    num_files = 0
    num_extension_files = 0
    extension_files = []

    ext = entry_extension.get().strip()
    if ext and not ext.startswith('.'):
        ext = f".{ext}"

    for root, dirs, files in os.walk(directory):
        num_folders += len(dirs)
        num_files += len(files)
        current_extension_files = [f for f in files if not ext or f.endswith(ext)]
        num_extension_files += len(current_extension_files)
        extension_files += current_extension_files

    return num_folders, num_files, num_extension_files, extension_files


# === SCANSIONE SPECIFICA PER CARTELLE TEST === #

def scan_test_directories(base_path, extension=""):
    """
    Scansiona tutte le cartelle testXX sotto base_path.
    Ritorna lista di tuple (nome_cartella, numero_file, elenco_file, ultima_modifica).
    """
    risultati = []

    if not os.path.isdir(base_path):
        return risultati

    for nome_dir in sorted(os.listdir(base_path)):
        full_path = os.path.join(base_path, nome_dir)
        if not os.path.isdir(full_path):
            continue
        if not nome_dir.lower().startswith("test"):
            continue

        tutti_file = []
        for root_dir, dirs, files in os.walk(full_path):
            for f in files:
                if not extension or f.endswith(extension):
                    tutti_file.append(os.path.join(root_dir, f))

        if not tutti_file:
            continue

        num_file = len(tutti_file)
        nomi_file = [os.path.basename(f) for f in tutti_file]

        ultima_mod_time = max(os.path.getmtime(f) for f in tutti_file)
        ultima_mod = datetime.datetime.fromtimestamp(ultima_mod_time).strftime("%Y-%m-%d %H:%M:%S")

        risultati.append((nome_dir, num_file, nomi_file, ultima_mod))

    return risultati


# === FUNZIONI PER CONFIGURAZIONE === #

def salva_configurazione(config):
    """Salva la configurazione in un file JSON."""
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Salva configurazione"
    )
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Salvataggio riuscito", f"Configurazione salvata in {file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")


def carica_configurazione():
    """Carica la configurazione da un file JSON."""
    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")],
        title="Carica configurazione"
    )
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {e}")
    return None


# === FUNZIONE APERTURA DIRECTORY === #

def open_selected_directory(lbl_directory):
    """Apre la directory selezionata nel file manager."""
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    if os.path.exists(selected_directory):
        try:
            if os.name == 'nt':  # Windows
                os.startfile(selected_directory)
            elif os.name == 'posix':
                if sys.platform == 'darwin':  # macOS
                    os.system(f'open "{selected_directory}"')
                else:  # Linux
                    os.system(f'xdg-open "{selected_directory}"')
        except Exception as e:
            messagebox.showerror("Errore", f"Non è stato possibile aprire la directory:\n{str(e)}")
    else:
        messagebox.showwarning("Attenzione", "Nessuna directory valida selezionata.")
