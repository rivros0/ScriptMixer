import os
import shutil
import tkinter as tk
from tkinter import filedialog, Toplevel, Text, Scrollbar
from tkinter import ttk, messagebox
from datetime import datetime, timezone
import difflib
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

#####################################################################################
#                               Gestione cartelle remote

# Funzione per controllare la presenza delle cartelle test01 - test30 nella dir remota
def scan_test_folders():
    remote_directory = entry_remote_directory.get()
    report_text.delete(1.0, tk.END)

    if not os.path.exists(remote_directory):
        messagebox.showerror("Errore", "La directory specificata non esiste.")
        return

    report_text.insert(tk.END, f"Controllo nella directory: {remote_directory}\n")

    for i in range(1, 31):
        folder_name = f"test{str(i).zfill(2)}"
        folder_path = os.path.join(remote_directory, folder_name)
        if os.path.isdir(folder_path):
            report_text.insert(tk.END, f"Trovata: {folder_name}\n")
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    creation_time = datetime.fromtimestamp(os.path.getctime(file_path), tz=timezone.utc)

                    report_text.insert(tk.END, f"  - {file} (Creato il: {creation_time})\n")
        else:
            report_text.insert(tk.END, f"Mancante: {folder_name}\n")

# Funzione per copiare le cartelle in una nuova directory sul desktop
def create_local_copy():
    global local_copy_directory
    remote_directory = entry_remote_directory.get()
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    timestamp = datetime.now().strftime("%Y%m%d_%H-%M")
    new_directory = os.path.join(desktop, timestamp)
    os.makedirs(new_directory, exist_ok=True)

    for i in range(1, 31):
        folder_name = f"test{str(i).zfill(2)}"
        src = os.path.join(remote_directory, folder_name)
        dest = os.path.join(new_directory, folder_name)
        if os.path.exists(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)  # Copia anche il contenuto

    report_text.insert(tk.END, f"Copie create in: {new_directory}\n")
    lbl_directory.config(text=f"Directory selezionata: {new_directory}")
    local_copy_directory = new_directory

    update_directory_listing(new_directory)
    update_subdirectories_list(new_directory)  # Aggiorna anche il Treeview

# Funzione per pulire il contenuto delle cartelle test
def clear_test_folders():
    selected_directory = entry_remote_directory.get()

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
                        report_text.insert(tk.END, f"Errore durante la cancellazione di {file_path}: {str(e)}\n")
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        shutil.rmtree(dir_path)
                    except Exception as e:
                        report_text.insert(tk.END, f"Errore durante la cancellazione di {dir_path}: {str(e)}\n")

    report_text.insert(tk.END, "Tutte le cartelle test remote sono state pulite.\n")


#######################################################################################
#                                   REPORT
def mix_files():
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    prompt_string = entry_prompt.get("1.0", tk.END).strip()
    extension = entry_extension.get()

    output_directory = os.path.join(selected_directory, "00_MixOutput")
    os.makedirs(output_directory, exist_ok=True)

    report_text.delete(1.0, tk.END)  # Pulisce il campo di testo del report

    for item in tree.get_children():
        subdir = tree.item(item, "values")[0]
        mix_result = create_mix_file(selected_directory, subdir, prompt_string, extension, output_directory)
        report_text.insert(tk.END, mix_result)

########################################################################################
#                                   Directory corrente in OS
# Funzione per aprire la directory selezionata
def open_selected_directory():
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    if os.path.exists(selected_directory):  # Controlla se la directory esiste
        try:
            if os.name == 'nt':  # Windows
                os.startfile(selected_directory)
            elif os.name == 'posix':  # macOS o Linux
                os.system(f'open "{selected_directory}"' if sys.platform == 'darwin' else f'xdg-open "{selected_directory}"')
        except Exception as e:
            tk.messagebox.showerror("Errore", f"Non è stato possibile aprire la directory:\n{str(e)}")
    else:
        tk.messagebox.showwarning("Attenzione", "Nessuna directory valida selezionata.")


#######################################################################################################
#                                   MERGE 
def create_mix_file(base_directory, subdir, prompt_string, extension, output_directory):
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

        with open(mix_file_path, "w") as mix_file:

            # Includi l'intro solo se la casella di spunta è selezionata
            if include_prompt_var.get():
                mix_file.write(prompt_string + "\n")
                mix_file.write("###############################################################" + "\n\n")

            # Includi il nome della subdirectory solo se la casella di spunta è selezionata
            if include_subdir_var.get():
                mix_file.write(subdir + "\n\n")
                mix_file.write("###############################################################" + "\n\n")


            for file_path in files_to_mix:
                with open(file_path, "r") as current_file:
                    mix_file.write(f"{os.path.basename(file_path)}\n{current_file.read()}\n")

        tree.tag_configure(subdir, background="green")
        return f"Mix completato per {subdir}: file con estensione {extension} uniti con successo.\n"
    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n"

def choose_directory():

    selected_directory = filedialog.askdirectory()
    if selected_directory:
        lbl_directory.config(text=f"Directory selezionata: {selected_directory}")
        update_directory_listing(selected_directory)
        update_subdirectories_list(selected_directory)

# Funzione per aggiornare la lista dei file con filtro per estensione
def update_directory_listing(directory):
    report_text.delete(1.0, tk.END)
    file_extension = entry_extension.get().strip()

    if not file_extension.startswith('.') and file_extension != '':
        file_extension = f".{file_extension}"  # Aggiungi il punto se manca

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file_extension == '' or file.endswith(file_extension):  # Filtra per estensione se specificata
                file_path = os.path.join(root, file)
                report_text.insert(tk.END, f"{file_path}\n")

# Funzione per aggiornare la lista delle subdirectory nel Treeview
def update_subdirectories_list(directory):
    tree.delete(*tree.get_children())  # Pulisce il contenuto attuale del Treeview

    for subdir in os.listdir(directory):
        subdir_path = os.path.join(directory, subdir)
        if os.path.isdir(subdir_path):
            num_files = sum(len(files) for _, _, files in os.walk(subdir_path))
            extension_files = [f for f in os.listdir(subdir_path) if f.endswith(entry_extension.get())]
            num_extension_files = len(extension_files)

            tree.insert("", "end", values=(subdir, len(os.listdir(subdir_path)), num_files, num_extension_files, ", ".join(extension_files)))


#########################################################################################################
#                                   Popolamento ListaFIle

def update_subdirectories_list(selected_directory):
    subdirectories = [d for d in os.listdir(selected_directory) if os.path.isdir(os.path.join(selected_directory, d))]
    subdirectories.sort()

    tree.delete(*tree.get_children())

    for subdir in subdirectories:
        check_directory_content(selected_directory, subdir)

def check_directory_content(base_directory, subdir):
    full_path = os.path.join(base_directory, subdir)

    num_folders, num_files, num_extension_files, extension_files = count_directory_content(full_path)

    has_content = num_folders + num_files > 0
    icon_color = "yellow" if has_content else "gray"

    tree.insert("", "end", values=(subdir, num_folders, num_files, num_extension_files, extension_files))

def count_directory_content(directory):
    num_folders = 0
    num_files = 0
    num_extension_files = 0
    extension_files = []

    for root, dirs, files in os.walk(directory):
        num_folders += len(dirs)
        num_files += len(files)
        current_extension_files = [f for f in files if f.endswith(entry_extension.get())]
        num_extension_files += len(current_extension_files)
        extension_files += current_extension_files

    return num_folders, num_files, num_extension_files, extension_files

########################################################################################
#                                   MEGAmerge per Stampa

def merge_all_files():
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    merged_file_path = os.path.join(output_directory, "00_MEGAmerged_output.txt")

    if not os.path.exists(output_directory):
        messagebox.showwarning("Attenzione", "La directory 00_MixOutput non esiste. Esegui prima la fase di mix.")
        return

    try:
        with open(merged_file_path, "w") as merged_file:
            for file_name in sorted(os.listdir(output_directory)):
                if file_name.endswith("_mix.txt"):
                    file_path = os.path.join(output_directory, file_name)
                    with open(file_path, "r") as f:
                        merged_file.write(f.read())
                        merged_file.write("\n\f\n")  # Interruzione di pagina
        report_text.insert(tk.END, f"Merge completato. File creato: {merged_file_path}\n")
    except Exception as e:
        report_text.insert(tk.END, f"Errore durante il merge dei file: {str(e)}\n")


#####################################################################################################
#                                   Similarità

def calculate_similarity(file1_path, file2_path):
    try:
        with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2:
            content1 = file1.read().replace('\r\n', '\n').replace('\r', '\n')
            content2 = file2.read().replace('\r\n', '\n').replace('\r', '\n')
            matcher = difflib.SequenceMatcher(None, content1, content2)
            return matcher, matcher.ratio() * 100  # Matcher e somiglianza in percentuale
    except Exception as e:
        return None, 0  # Se c'è un errore (es. file non leggibile), somiglianza 0

def plot_similarity_matrix(output_directory):
    files = [os.path.join(output_directory, file) for file in os.listdir(output_directory) if file.endswith("_mix.txt")]
    num_files = len(files)
    similarity_matrix = np.zeros((num_files, num_files))
    matchers = [[None for _ in range(num_files)] for _ in range(num_files)]

    for i in range(num_files):
        for j in range(num_files):
            if i != j:
                matcher, similarity_matrix[i, j] = calculate_similarity(files[i], files[j])
                matchers[i][j] = matcher

    def on_click(event):
        if event.inaxes is None:
            return

        x, y = int(event.xdata), int(event.ydata)
        if x != y and matchers[x][y]:
            show_similar_fragments(files[x], files[y], matchers[x][y])

    # Visualizzazione della matrice di somiglianza
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(similarity_matrix, annot=True, fmt=".0f", cmap="coolwarm", xticklabels=[os.path.basename(f) for f in files],
                yticklabels=[os.path.basename(f) for f in files], ax=ax)
    plt.title("Matrice di Similarit\u00e0 tra i File di Output")
    plt.xlabel("File di Output")
    plt.ylabel("File di Output")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()

    return files, similarity_matrix

#####################################################################################################
#                                       GUI - Similarità
#                                      Finestra di confronto

def show_similar_fragments(file1, file2, matcher):
    top = Toplevel(root)
    top.title(f"Somiglianze tra {os.path.basename(file1)} e {os.path.basename(file2)}")
    top.geometry("1024x768")
    top.resizable(True, True)

    # Frames per le colonne
    frame1 = tk.Frame(top)
    frame1.grid(row=0, column=0, sticky="nsew")
    frame2 = tk.Frame(top)
    frame2.grid(row=0, column=1, sticky="nsew")

    # Testi e scrollbar
    text1 = Text(frame1, wrap="none", width=50, height=20)
    text1.pack(side="left", fill="both", expand=True)

    text2 = Text(frame2, wrap="none", width=50, height=20)
    text2.pack(side="left", fill="both", expand=True)

    scroll_y = Scrollbar(top, orient="vertical")
    scroll_y.grid(row=0, column=2, sticky="ns")

    text1.config(yscrollcommand=scroll_y.set)
    text2.config(yscrollcommand=scroll_y.set)

    def sync_scroll(*args):
        text1.yview(*args)
        text2.yview(*args)

    scroll_y.config(command=sync_scroll)

    # Leggi i contenuti successivi al nome del file
    content1_start = matcher.a.find("\n", matcher.a.find("###############################################################")) + 1
    content2_start = matcher.b.find("\n", matcher.b.find("###############################################################")) + 1

    content1 = matcher.a[content1_start:]
    content2 = matcher.b[content2_start:]

    content1_lines = content1.splitlines()
    content2_lines = content2.splitlines()

    # Calcola il numero di righe vuote per allineare il testo
    max_line_count = max(len(content1_lines), len(content2_lines))

    for i in range(len(content1_lines), max_line_count):
        content1_lines.append("")

    for i in range(len(content2_lines), max_line_count):
        content2_lines.append("")

    # Inserisci il testo nelle colonne
    for line1, line2 in zip(content1_lines, content2_lines):
        text1.insert("end", line1 + "\n")
        text2.insert("end", line2 + "\n")

    top.grid_rowconfigure(0, weight=1)
    top.grid_columnconfigure(0, weight=1)
    top.grid_columnconfigure(1, weight=1)

def analyze_similarities():
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    output_directory = os.path.join(selected_directory, "00_MixOutput")

    if not os.path.exists(output_directory):
        report_text.insert(tk.END, "La directory 00_MixOutput non esiste. Esegui prima la fase di mix.\n")
        return

    files, similarity_matrix = plot_similarity_matrix(output_directory)


############################################################################################################
#                                               GUI - MAIN

root = tk.Tk()
root.title("Ninei - Smixer_v5")
root.geometry("1024x768")

# Layout principale con grid
root.columnconfigure(3, weight=1)  # Colonna principale
root.rowconfigure(11, weight=1)    # Riga che contiene il treeview (espandibile)

#Gestione cartelle remote

# Directory remota
lbl_remote_directory = tk.Label(root, text="Directory remota:")
lbl_remote_directory.grid(row=0, column=0, sticky="w", padx=10, pady=5)

entry_remote_directory = tk.Entry(root, width=50)
entry_remote_directory.insert(0, "Y:\\")  # Directory predefinita
entry_remote_directory.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

# Bottoni per la gestione delle cartelle remote
btn_scan = tk.Button(root, text="Scan", command=scan_test_folders)
btn_scan.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

btn_copy = tk.Button(root, text="Crea Copia Locale", command=create_local_copy)
btn_copy.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

btn_clear = tk.Button(root, text="Pulisci Test Remoti", command=clear_test_folders)
btn_clear.grid(row=1, column=2, sticky="ew", padx=5, pady=5)

# Stringa Prompt
lbl_prompt = tk.Label(root, text="INTRO:")
lbl_prompt.grid(row=2, column=0, sticky="w", padx=10, pady=5)

entry_prompt = tk.Text(root, width=80, height=2)
entry_prompt.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# Casella di spunta per includere o escludere l'Intro
include_prompt_var = tk.BooleanVar(value=True)  # Di default, è selezionata
chk_include_prompt = tk.Checkbutton(root, text="Includi Intro", variable=include_prompt_var)
chk_include_prompt.grid(row=3, column=1, sticky="w", padx=10, pady=5)

# Aggiungi una casella di spunta per l'inclusione della subdirectory
include_subdir_var = tk.BooleanVar(value=True)  # Di default, selezionata
chk_include_subdir = tk.Checkbutton(root, text="Includi Nome", variable=include_subdir_var)
chk_include_subdir.grid(row=3, column=2, sticky="w", padx=10, pady=5)

# Estensione file
lbl_extension = tk.Label(root, text="Estensione dei file:")
lbl_extension.grid(row=4, column=0, sticky="w", padx=10, pady=5)

entry_extension = tk.Entry(root)
entry_extension.grid(row=4, column=1, sticky="ew", padx=10, pady=5)

# Bottone Scegli Directory
btn_choose_directory = tk.Button(root, text="Scegli Directory", command=choose_directory)
btn_choose_directory.grid(row=5, column=0, columnspan=1, sticky="ew", padx=10, pady=5)

lbl_directory = tk.Label(root, text="Directory non selezionata", anchor="w")
lbl_directory.grid(row=5, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# Lista delle subdirectories con icona di stato e numero di cartelle, file, file con estensione
tree = ttk.Treeview(root, columns=("subdirectory", "num_folders", "num_files", "num_extension_files", "extension_files"), show="headings")
tree.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

# Configurazione delle colonne della griglia (per espandibilità)
root.columnconfigure(2, weight=1)
root.rowconfigure(6, weight=1)  # Espandi la griglia per il treeview

tree.column("subdirectory", anchor="w", width=200, minwidth=200)
tree.column("num_folders", anchor="center", width=100, minwidth=100)
tree.column("num_files", anchor="center", width=100, minwidth=100)
tree.column("num_extension_files", anchor="center", width=150, minwidth=150)
tree.column("extension_files", anchor="w", width=300, minwidth=300)

tree.heading("subdirectory", text="Subdirectory")
tree.heading("num_folders", text="Cartelle")
tree.heading("num_files", text="File")
tree.heading("num_extension_files", text="File con Estensione")
tree.heading("extension_files", text="Elenco File Estensione")

# Bottone Mix
btn_mix = tk.Button(root, text="Mixa", command=mix_files)
btn_mix.grid(row=7, column=0, sticky="ew", padx=10, pady=5)

#Bottone per il merge dei file
btn_merge_files = tk.Button(root, text="MEGAmerge", command=merge_all_files)
btn_merge_files.grid(row=7, column=1, sticky="ew", padx=10, pady=5)

# Bottone per aprire la directory
btn_open_directory = tk.Button(root, text="Apri Directory Output", command=open_selected_directory)
btn_open_directory.grid(row=7, column=2, sticky="ew", padx=10, pady=5)

#Bottone per heatmap
btn_analyze = tk.Button(root, text="Analizza Similarità", command=analyze_similarities)
btn_analyze.grid(row=8, column=0, sticky="ew", padx=10, pady=5)

# Report
lbl_report = tk.Label(root, text="Report:")
lbl_report.grid(row=9, column=0, sticky="nw", padx=10, pady=5)

report_text = tk.Text(root, width=1024, height=12)
report_text.grid(row=10, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

# Scrollbar per il report
scrollbar = Scrollbar(root, orient="vertical", command=report_text.yview)
scrollbar.grid(row=10, column=3, sticky="ns", pady=5)

report_text.config(yscrollcommand=scrollbar.set)

# Avvia il mainloop
root.mainloop()