import os
import shutil
import sys
from tkinter import filedialog, messagebox
from datetime import datetime, timezone

# Limiti delle cartelle test gestite dall'applicazione
TEST_MIN = 1
TEST_MAX = 30


def _iter_test_folders(base_directory):
    """
    Generatore di coppie (nome_cartella, percorso_assoluto) per test01..test30.
    Serve per essere sicuri di intervenire SOLO su queste cartelle.
    """
    for i in range(TEST_MIN, TEST_MAX + 1):
        folder_name = f"test{str(i).zfill(2)}"
        folder_path = os.path.join(base_directory, folder_name)
        yield folder_name, folder_path


def scan_test_folders(remote_directory, report_text):
    """
    Scansiona le cartelle test01..test30 nella directory remota indicata e
    scrive nel report:
      - quali cartelle sono presenti/mancanti
      - per quelle presenti, elenca i file con la data di creazione.
    """
    report_text.delete("1.0", "end")

    if not os.path.exists(remote_directory):
        messagebox.showerror("Errore", "La directory specificata non esiste.")
        return

    report_text.insert("end", f"Controllo nella directory: {remote_directory}\n")

    for folder_name, folder_path in _iter_test_folders(remote_directory):
        if os.path.isdir(folder_path):
            report_text.insert("end", f"Trovata: {folder_name}\n")
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    creation_time = datetime.fromtimestamp(
                        os.path.getctime(file_path), tz=timezone.utc
                    )
                    report_text.insert(
                        "end",
                        f"  - {file} (Creato il: {creation_time})\n",
                    )
        else:
            report_text.insert("end", f"Mancante: {folder_name}\n")


def _copy_test_folders(remote_directory, target_root, report_text=None):
    """
    Copia tutte le cartelle test01..test30 esistenti da remote_directory
    dentro target_root (mantenendo i nomi delle cartelle).

    Restituisce la lista delle cartelle effettivamente copiate.
    """
    copied = []

    for folder_name, src in _iter_test_folders(remote_directory):
        if os.path.exists(src):
            dest = os.path.join(target_root, folder_name)
            try:
                shutil.copytree(src, dest, dirs_exist_ok=True)
                copied.append(folder_name)
            except Exception as e:
                if report_text is not None:
                    report_text.insert(
                        "end",
                        f"Errore durante la copia di {src} -> {dest}: {e}\n",
                    )

    return copied


def create_local_copy(
    remote_directory,
    report_text,
    lbl_directory,
    update_directory_listing_func,
    update_subdirectories_list_func,
):
    """
    Crea una copia locale delle cartelle test01..test30 presenti in remote_directory.

    - La copia viene creata sul Desktop in una nuova cartella con nome timestamp
      (es. '20251106_17-30').
    - Vengono copiate SOLO le cartelle test01..test30.
    - Aggiorna:
        * il report,
        * la label lbl_directory,
        * la tabella/tree tramite le funzioni di update passate.

    Ritorna il percorso della nuova directory creata.
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    timestamp = datetime.now().strftime("%Y%m%d_%H-%M")
    new_directory = os.path.join(desktop, timestamp)
    os.makedirs(new_directory, exist_ok=True)

    copied = _copy_test_folders(remote_directory, new_directory, report_text)

    report_text.insert("end", f"Copie create in: {new_directory}\n")
    if not copied:
        report_text.insert(
            "end",
            "Attenzione: nessuna cartella test01–test30 trovata nella directory remota.\n",
        )

    # Aggiorna la label di quella scheda (vecchio comportamento)
    lbl_directory.config(text=f"Directory selezionata: {new_directory}")

    # Aggiorna eventuali viste (lista file / treeview)
    if update_directory_listing_func is not None:
        update_directory_listing_func(new_directory)

    if update_subdirectories_list_func is not None:
        update_subdirectories_list_func(new_directory)

    return new_directory


def clear_test_folders(selected_directory, report_text):
    """
    Cancella ricorsivamente TUTTI i file e le sottocartelle contenuti in
    test01..test30 sotto selected_directory (ma NON tocca altre cartelle).

    Mostra una tripla conferma "paranoica" prima di procedere.
    """
    if not selected_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory.")
        return

    confirm = messagebox.askyesno(
        "Conferma",
        "Sei sicuro di voler cancellare i dati nelle cartelle test?",
    )
    if not confirm:
        return

    confirm_final = messagebox.askyesno(
        "Conferma finale",
        "Questa azione è irreversibile. Continuare?",
    )
    if not confirm_final:
        return

    confirm_final_final = messagebox.askyesno(
        "Conferma finalissima",
        "Siamo proprio sicuri sicuri??? Continuare?",
    )
    if not confirm_final_final:
        return

    for folder_name, folder_path in _iter_test_folders(selected_directory):
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        report_text.insert(
                            "end",
                            f"Errore durante la cancellazione di {file_path}: {e}\n",
                        )
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        shutil.rmtree(dir_path)
                    except Exception as e:
                        report_text.insert(
                            "end",
                            f"Errore durante la cancellazione di {dir_path}: {e}\n",
                        )

    report_text.insert("end", "Tutte le cartelle test remote sono state pulite.\n")


def choose_directory(lbl_directory, update_directory_listing_func, update_subdirectories_list_func):
    """
    Dialogo standard "Scegli directory" usato nelle vecchie schede:
    - aggiorna la label passata,
    - chiama le funzioni di update per ricaricare lista file e tree.
    """
    selected_directory = filedialog.askdirectory()
    if selected_directory:
        lbl_directory.config(text=f"Directory selezionata: {selected_directory}")
        update_directory_listing_func(selected_directory)
        update_subdirectories_list_func(selected_directory)


def open_selected_directory(selected_directory):
    """
    Apre nel file browser la directory selezionata.

    Può ricevere:
      - una stringa con il path,
      - una Label tkinter (da cui legge .cget("text")),
      - una StringVar (da cui legge .get()).

    Se il path non è valido, mostra un warning.
    """
    # Normalizza il parametro in una stringa di path
    path = None

    # Caso: Label (o widget simile)
    if hasattr(selected_directory, "cget"):
        try:
            text = selected_directory.cget("text")
            # Gestisce anche il vecchio prefisso "Directory selezionata: ..."
            path = text.replace("Directory selezionata:", "").strip()
        except Exception:
            path = None

    # Caso: StringVar o oggetto con .get()
    if path is None and hasattr(selected_directory, "get"):
        try:
            path = selected_directory.get()
        except Exception:
            path = None

    # Caso generico: già una stringa (o altro oggetto)
    if path is None:
        path = str(selected_directory)

    if not path or not os.path.exists(path):
        messagebox.showwarning("Attenzione", "Nessuna directory valida selezionata.")
        return

    try:
        if os.name == "nt":
            os.startfile(path)
        elif os.name == "posix":
            if sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
    except Exception as e:
        messagebox.showerror(
            "Errore",
            f"Non è stato possibile aprire la directory:\n{str(e)}",
        )
