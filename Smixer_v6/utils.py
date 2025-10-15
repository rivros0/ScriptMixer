import os
import json
import sys
import datetime
import fnmatch
import tkinter as tk
from tkinter import filedialog, messagebox
import fnmatch
import datetime as _dt

# --- helpers ---

def _iter_test_dirs(base_path):
    """Generator: test01..test30 (solo se esistono)."""
    for i in range(1, 31):
        name = f"test{str(i).zfill(2)}"
        full = os.path.join(base_path, name)
        if os.path.isdir(full):
            yield name, full

def _filter_by_root_prefix(names, root_prefix):
    """
    Filtra i nomi in base a un pattern glob (es. 'test*').
    Per sicurezza, se il pattern NON inizia con 'test', non restituiamo nulla.
    """
    root_prefix = (root_prefix or "test*").strip()
    if not root_prefix.lower().startswith("test"):
        return []
    return [n for n in names if fnmatch.fnmatch(n, root_prefix)]

# === FUNZIONI DI SCANSIONE (SOLO test01..test30) === #

def update_directory_listing(directory, entry_extension, report_text):
    """Elenca file SOLO in test01..test30 (ricorsivo)."""
    report_text.delete("1.0", "end")
    file_extension = entry_extension.get().strip()
    if file_extension and not file_extension.startswith('.'):
        file_extension = f".{file_extension}"

    for name, base in _iter_test_dirs(directory):
        for root, dirs, files in os.walk(base):
            for file in files:
                if not file_extension or file.endswith(file_extension):
                    file_path = os.path.join(root, file)
                    report_text.insert("end", f"{file_path}\n")

def update_subdirectories_list(selected_directory, tree, entry_extension):
    """Popola la treeview SOLO per test01..test30."""
    tree.delete(*tree.get_children())
    for name, _ in _iter_test_dirs(selected_directory):
        check_directory_content(selected_directory, name, tree, entry_extension)

def check_directory_content(base_directory, subdir, tree, entry_extension):
    """Conta cartelle/file in una sottocartella testXX e abilita 'CopiaInClipboard' se esiste _mix.txt."""
    full_path = os.path.join(base_directory, subdir)
    num_folders = num_files = num_extension_files = 0
    extension_files = []

    ext = entry_extension.get().strip()
    if ext and not ext.startswith('.'):
        ext = f".{ext}"

    if os.path.isdir(full_path):
        for root, dirs, files in os.walk(full_path):
            num_folders += len(dirs)
            num_files += len(files)
            current_extension_files = [f for f in files if not ext or f.endswith(ext)]
            num_extension_files += len(current_extension_files)
            extension_files += current_extension_files

    mix_file_path = os.path.join(base_directory, "00_MixOutput", f"{subdir}_mix.txt")
    button_text = "CopiaInClipboard" if os.path.exists(mix_file_path) else "-----"

    tree.insert(
        "", "end",
        values=(subdir, num_folders, num_files, num_extension_files, ", ".join(extension_files), button_text)
    )

def scan_test_directories(base_path, extension="", root_prefix="test*"):
    """
    Restituisce sempre fino alle 30 cartelle test01..test30 (se esistono),
    filtrate per 'root_prefix' (glob, default 'test*').
    Ritorna lista di tuple: (nome_cartella, numero_file, elenco_file, ultima_modifica_str).
    """
    risultati = []
    if not os.path.isdir(base_path):
        return risultati

    names = [name for name, _ in _iter_test_dirs(base_path)]
    names = _filter_by_root_prefix(names, root_prefix)

    for name in names:
        full_path = os.path.join(base_path, name)
        tutti_file = []
        if os.path.isdir(full_path):
            for root_dir, dirs, files in os.walk(full_path):
                for f in files:
                    if not extension or f.endswith(extension):
                        tutti_file.append(os.path.join(root_dir, f))

        num_file = len(tutti_file)
        nomi_file = [os.path.basename(f) for f in tutti_file]

        ultima_mod = ""
        if tutti_file:
            ultima_mod_time = max(os.path.getmtime(f) for f in tutti_file)
            ultima_mod = datetime.datetime.fromtimestamp(ultima_mod_time).strftime("%Y-%m-%d %H:%M:%S")

        risultati.append((name, num_file, nomi_file, ultima_mod))
    return risultati

# === Salva/Carica config: invariati rispetto alla tua base === #
def salva_configurazione(config):
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

def open_selected_directory(lbl_directory):
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    if os.path.exists(selected_directory):
        try:
            if os.name == 'nt':
                os.startfile(selected_directory)
            elif os.name == 'posix':
                if sys.platform == 'darwin':
                    os.system(f'open "{selected_directory}"')
                else:
                    os.system(f'xdg-open "{selected_directory}"')
        except Exception as e:
            messagebox.showerror("Errore", f"Non è stato possibile aprire la directory:\n{str(e)}")
    else:
        messagebox.showwarning("Attenzione", "Nessuna directory valida selezionata.")

# ----- Calcolo linee di codice (per Live) -----

def _count_lines_in_file(file_path: str) -> int:
    """Conta le linee di un file di testo in modo robusto."""
    try:
        # Lettura testuale con fallback sugli errori
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def _total_loc_in_dir(full_path: str, extension: str = "") -> int:
    """Somma le linee di tutti i file (eventualmente filtrati per estensione) nella dir."""
    total = 0
    for root_dir, _, files in os.walk(full_path):
        for f in files:
            if not extension or f.endswith(extension):
                total += _count_lines_in_file(os.path.join(root_dir, f))
    return total

def scan_test_directories_with_loc(base_path, extension: str = "", root_prefix: str = "test*"):
    """
    Come scan_test_directories ma aggiunge il campo 'total_loc' (linee totali).
    Ritorna: (name, num_file, nomi_file, ultima_mod, total_loc)
    """
    risultati_base = scan_test_directories(base_path, extension=extension, root_prefix=root_prefix)
    risultati = []
    for (name, num_file, nomi_file, ultima_mod) in risultati_base:
        full_path = os.path.join(base_path, name)
        total_loc = _total_loc_in_dir(full_path, extension=extension)
        risultati.append((name, num_file, nomi_file, ultima_mod, total_loc))
    return risultati


def list_test_dir_names(base_path: str, root_prefix: str = "test*"):
    """Ritorna la lista delle sottocartelle testXX presenti (filtrate per glob, di default test*)."""
    if not os.path.isdir(base_path):
        return []
    names = []
    for i in range(1, 31):
        name = f"test{str(i).zfill(2)}"
        if fnmatch.fnmatch(name, root_prefix):
            full = os.path.join(base_path, name)
            if os.path.isdir(full):
                names.append(name)
    return names

def dir_summary(base_path: str, name: str, extension: str = "", with_loc: bool = True):
    """
    Calcola i dati per UNA sola cartella testXX:
    ritorna (name, num_file, nomi_file, ultima_mod_str, total_loc)
    """
    full_path = os.path.join(base_path, name)
    tutti_file = []
    total_loc = 0
    if os.path.isdir(full_path):
        for root_dir, dirs, files in os.walk(full_path):
            for f in files:
                if not extension or f.endswith(extension):
                    fp = os.path.join(root_dir, f)
                    tutti_file.append(fp)
                    if with_loc:
                        # riusa la funzione robusta già presente
                        try:
                            total_loc += _count_lines_in_file(fp)
                        except Exception:
                            pass
    num_file = len(tutti_file)
    nomi_file = [os.path.basename(f) for f in tutti_file]
    ultima_mod = ""
    if tutti_file:
        try:
            t = max(os.path.getmtime(f) for f in tutti_file)
            ultima_mod = _dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ultima_mod = ""
    return (name, num_file, nomi_file, ultima_mod, total_loc)

def now_ts():
    return _dt.datetime.now()