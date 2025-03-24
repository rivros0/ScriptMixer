import os
import shutil
import sys
from tkinter import filedialog, messagebox
from datetime import datetime, timezone

def scan_test_folders(remote_directory, report_text):
    report_text.delete("1.0", "end")
    if not os.path.exists(remote_directory):
        messagebox.showerror("Errore", "La directory specificata non esiste.")
        return

    report_text.insert("end", f"Controllo nella directory: {remote_directory}\n")
    for i in range(1, 31):
        folder_name = f"test{str(i).zfill(2)}"
        folder_path = os.path.join(remote_directory, folder_name)
        if os.path.isdir(folder_path):
            report_text.insert("end", f"Trovata: {folder_name}\n")
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    creation_time = datetime.fromtimestamp(os.path.getctime(file_path), tz=timezone.utc)
                    report_text.insert("end", f"  - {file} (Creato il: {creation_time})\n")
        else:
            report_text.insert("end", f"Mancante: {folder_name}\n")

def create_local_copy(remote_directory, report_text, lbl_directory, update_directory_listing_func, update_subdirectories_list_func):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    timestamp = datetime.now().strftime("%Y%m%d_%H-%M")
    new_directory = os.path.join(desktop, timestamp)
    os.makedirs(new_directory, exist_ok=True)

    for i in range(1, 31):
        folder_name = f"test{str(i).zfill(2)}"
        src = os.path.join(remote_directory, folder_name)
        dest = os.path.join(new_directory, folder_name)
        if os.path.exists(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)
    
    report_text.insert("end", f"Copie create in: {new_directory}\n")
    lbl_directory.config(text=f"Directory selezionata: {new_directory}")
    
    update_directory_listing_func(new_directory)
    update_subdirectories_list_func(new_directory)
    
    return new_directory

def clear_test_folders(selected_directory, report_text):
    if not selected_directory:
        messagebox.showwarning("Attenzione", "Seleziona prima una directory.")
        return

    confirm = messagebox.askyesno("Conferma", "Sei sicuro di voler cancellare i dati nelle cartelle test?")
    if not confirm:
        return

    confirm_final = messagebox.askyesno("Conferma finale", "Questa azione è irreversibile. Continuare?")
    if not confirm_final:
        return

    confirm_final_final = messagebox.askyesno("Conferma finalissima", "Siamo proprio sicuri sicuri??? Continuare?")
    if not confirm_final_final:
        return

    for i in range(1, 31):
        folder_name = f"test{str(i).zfill(2)}"
        folder_path = os.path.join(selected_directory, folder_name)
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        report_text.insert("end", f"Errore durante la cancellazione di {file_path}: {str(e)}\n")
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        shutil.rmtree(dir_path)
                    except Exception as e:
                        report_text.insert("end", f"Errore durante la cancellazione di {dir_path}: {str(e)}\n")
    report_text.insert("end", "Tutte le cartelle test remote sono state pulite.\n")

def choose_directory(lbl_directory, update_directory_listing_func, update_subdirectories_list_func):
    selected_directory = filedialog.askdirectory()
    if selected_directory:
        lbl_directory.config(text=f"Directory selezionata: {selected_directory}")
        update_directory_listing_func(selected_directory)
        update_subdirectories_list_func(selected_directory)

def open_selected_directory(selected_directory):
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
