import os
from datetime import datetime

import data_handler  # per riutilizzare la logica su test01..test30


# =============================================================================
#  UTILITÀ PER LA SCHEDA "CORREZIONE"
# =============================================================================

def update_directory_listing(directory, entry_extension, report_text):
    """
    Popola la text-area di report con l'elenco dei file trovati nella directory
    (ricerca ricorsiva), filtrando per estensione.

    - directory: path di partenza
    - entry_extension: widget (Entry / StringVar) con l'estensione (.cpp, .java, ...)
    - report_text: widget Text dove scrivere la lista dei file
    """
    report_text.delete("1.0", "end")

    if not directory or not os.path.isdir(directory):
        report_text.insert("end", "Directory non valida o inesistente.\n")
        return

    file_extension = entry_extension.get().strip() if hasattr(entry_extension, "get") else str(entry_extension).strip()
    if file_extension != "" and not file_extension.startswith("."):
        file_extension = f".{file_extension}"

    report_text.insert("end", f"Scansione di:\n  {directory}\n")
    if file_extension:
        report_text.insert("end", f"Filtro estensione: {file_extension}\n\n")
    else:
        report_text.insert("end", "Nessun filtro di estensione applicato.\n\n")

    for root, _dirs, files in os.walk(directory):
        for file in files:
            if file_extension == "" or file.endswith(file_extension):
                file_path = os.path.join(root, file)
                report_text.insert("end", f"{file_path}\n")

    report_text.see("end")


def count_directory_content(directory, entry_extension):
    """
    Conta:
      - quante sottocartelle
      - quanti file totali
      - quanti file con la specifica estensione
      - l'elenco dei file con quella estensione

    Restituisce: (num_folders, num_files, num_extension_files, extension_files)
    """
    num_folders = 0
    num_files = 0
    num_extension_files = 0
    extension_files = []

    ext = entry_extension.get().strip() if hasattr(entry_extension, "get") else str(entry_extension).strip()
    if ext and not ext.startswith("."):
        ext = "." + ext

    for _root, dirs, files in os.walk(directory):
        num_folders += len(dirs)
        num_files += len(files)
        if ext:
            current_extension_files = [f for f in files if f.endswith(ext)]
        else:
            current_extension_files = list(files)
        num_extension_files += len(current_extension_files)
        extension_files += current_extension_files

    return num_folders, num_files, num_extension_files, extension_files


def check_directory_content(base_directory, subdir, tree, entry_extension):
    """
    Calcola le statistiche sulla sottocartella `subdir` e inserisce una riga
    nella Treeview.

    La Treeview nella scheda Correzione si aspetta 5 colonne:
      (subdirectory, num_folders, num_files, num_extension_files, extension_files)
    """
    full_path = os.path.join(base_directory, subdir)
    num_folders, num_files, num_extension_files, extension_files = count_directory_content(
        full_path, entry_extension
    )

    tree.insert(
        "",
        "end",
        values=(
            subdir,
            num_folders,
            num_files,
            num_extension_files,
            ", ".join(extension_files),
        ),
    )


def update_subdirectories_list(selected_directory, tree, entry_extension):
    """
    Elenca le sottodirectory immediate di `selected_directory`, le ordina
    alfabeticamente e per ciascuna calcola le statistiche inserendole
    nella Treeview.
    """
    if not selected_directory or not os.path.isdir(selected_directory):
        tree.delete(*tree.get_children())
        return

    subdirectories = [
        d
        for d in os.listdir(selected_directory)
        if os.path.isdir(os.path.join(selected_directory, d))
    ]
    subdirectories.sort()

    tree.delete(*tree.get_children())
    for subdir in subdirectories:
        check_directory_content(selected_directory, subdir, tree, entry_extension)


# =============================================================================
#  UTILITÀ PER LA SCHEDA "LIVE"
# =============================================================================

def scan_remote_directory(remote_directory, extension, count_lines=False):
    """
    Scansiona la directory remota alla ricerca delle sole cartelle test01..test30
    (come definito in data_handler), e per ciascuna restituisce:

      (nome_cartella, num_file_con_estensione, num_righe_totali, elenco_file, ultima_modifica_str)

    - remote_directory: path della radice che contiene le cartelle testXX
    - extension: estensione da filtrare (es. ".cpp"); se vuota, conta tutti i file
    - count_lines: se True, somma il numero di righe dei file trovati

    Ritorna una lista di tuple ordinate per nome_cartella.
    """
    results = []

    if not remote_directory or not os.path.isdir(remote_directory):
        return results

    ext = extension.strip()
    if ext and not ext.startswith("."):
        ext = "." + ext

    for folder_name, folder_path in data_handler._iter_test_folders(remote_directory):
        if not os.path.isdir(folder_path):
            # cartella mancante: non la mostriamo nella tabella Live
            continue

        files_found = []
        total_lines = 0
        last_mod = None

        for root, _dirs, files in os.walk(folder_path):
            for f in files:
                if not ext or f.endswith(ext):
                    files_found.append(f)
                    file_path = os.path.join(root, f)

                    # aggiorna last_mod
                    mtime = os.path.getmtime(file_path)
                    if last_mod is None or mtime > last_mod:
                        last_mod = mtime

                    # conteggio righe opzionale
                    if count_lines:
                        try:
                            # tentiamo UTF-8, altrimenti latin-1
                            try:
                                with open(file_path, "r", encoding="utf-8") as fh:
                                    lines = fh.readlines()
                            except UnicodeDecodeError:
                                with open(file_path, "r", encoding="latin-1", errors="replace") as fh:
                                    lines = fh.readlines()
                            total_lines += len(lines)
                        except Exception:
                            # se qualcosa va storto su un file, lo ignoriamo per il conteggio
                            pass

        num_file = len(files_found)
        files_found.sort()

        if last_mod is not None:
            last_mod_str = datetime.fromtimestamp(last_mod).strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_mod_str = "-"

        num_lines_value = total_lines if count_lines else None

        results.append((folder_name, num_file, num_lines_value, files_found, last_mod_str))

    # Ordina per nome cartella (test01, test02, ...)
    results.sort(key=lambda x: x[0])
    return results


def copy_test_directories(remote_directory, destination_root, nome_verifica):
    """
    Copia SOLO le cartelle test01..test30 esistenti da `remote_directory`
    dentro una nuova cartella creata sotto `destination_root`.

    La nuova cartella avrà nome:
        YYYYMMDD_HH-MM_<nome_verifica>

    Restituisce una stringa di esito (da mostrare nella label della scheda Live).
    """
    nome_verifica = (nome_verifica or "").strip()
    if not nome_verifica:
        return "⚠️ Nome verifica mancante."

    if not remote_directory or not os.path.isdir(remote_directory):
        return "⚠️ Directory remota non valida."

    if not destination_root or not os.path.isdir(destination_root):
        return "⚠️ Directory di destinazione non valida."

    timestamp = datetime.now().strftime("%Y%m%d_%H-%M")
    dest_base = os.path.join(destination_root, f"{timestamp}_{nome_verifica}")
    os.makedirs(dest_base, exist_ok=True)

    # Riutilizziamo la logica di data_handler per copiare SOLO test01..test30
    copied = data_handler._copy_test_folders(remote_directory, dest_base, report_text=None)

    if not copied:
        return f"⚠️ Nessuna cartella test01–test30 trovata in {remote_directory}."

    return f"✅ Copiate {len(copied)} cartelle di test in {dest_base}."


# =============================================================================
#  WRAPPER DI COMPATIBILITÀ (per vecchio codice che usava utils)
# =============================================================================

def choose_directory(lbl_directory, update_directory_listing_func, update_subdirectories_list_func):
    """
    Wrapper di compatibilità: delega a data_handler.choose_directory.

    Usato nelle versioni precedenti della scheda Correzione.
    """
    data_handler.choose_directory(lbl_directory, update_directory_listing_func, update_subdirectories_list_func)


def open_selected_directory(selected_directory):
    """
    Wrapper di compatibilità: delega a data_handler.open_selected_directory.

    Accetta stringa, Label o StringVar, come in data_handler.
    """
    data_handler.open_selected_directory(selected_directory)
