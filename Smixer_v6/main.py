import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json

from data_handler import scan_test_folders, create_local_copy, clear_test_folders, choose_directory, open_selected_directory
from business_logic import mix_files, merge_all_files
from similarity import analyze_similarities
from utils import update_directory_listing, update_subdirectories_list

# Variabile globale per tracciare se la configurazione è stata salvata
config_saved = True

def mark_unsaved(event=None):
    global config_saved
    config_saved = False

def trace_unsaved(*args):
    global config_saved
    config_saved = False

# Creazione della finestra principale
root = tk.Tk()
root.title("Ninei - Smixer_v6")
root.geometry("1024x768")

# Configurazione della grid principale
root.columnconfigure(3, weight=1)
root.rowconfigure(11, weight=1)

# Variabili di opzione
include_prompt_var = tk.BooleanVar(value=True)
include_prompt_var.trace("w", trace_unsaved)
include_subdir_var = tk.BooleanVar(value=True)
include_subdir_var.trace("w", trace_unsaved)

# --- Sezione: Gestione cartelle remote ---
lbl_remote_directory = tk.Label(root, text="Directory remota:")
lbl_remote_directory.grid(row=0, column=0, sticky="w", padx=10, pady=5)

entry_remote_directory = tk.Entry(root, width=50)
entry_remote_directory.insert(0, "Y:\\")  # Directory predefinita
entry_remote_directory.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
entry_remote_directory.bind("<KeyRelease>", mark_unsaved)

# Funzione per il comando Scan
def on_scan():
    remote_dir = entry_remote_directory.get()
    scan_test_folders(remote_dir, report_text)

btn_scan = tk.Button(root, text="Scan", command=on_scan)
btn_scan.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

# Funzioni wrapper per aggiornare le liste (directory e subdirectories)
def update_dir_listing_wrapper(directory):
    update_directory_listing(directory, entry_extension, report_text)

def update_subdirs_list_wrapper(directory):
    update_subdirectories_list(directory, tree, entry_extension)

# Funzione per il comando "Crea Copia Locale"
def on_copy():
    remote_dir = entry_remote_directory.get()
    create_local_copy(remote_dir, report_text, lbl_directory, update_dir_listing_wrapper, update_subdirs_list_wrapper)
    mark_unsaved()

btn_copy = tk.Button(root, text="Crea Copia Locale", command=on_copy)
btn_copy.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

# Funzione per il comando "Pulisci Test Remoti"
def on_clear():
    selected_dir = entry_remote_directory.get()
    clear_test_folders(selected_dir, report_text)
    mark_unsaved()

btn_clear = tk.Button(root, text="Pulisci Test Remoti", command=on_clear)
btn_clear.grid(row=1, column=2, sticky="ew", padx=5, pady=5)

# --- Sezione: Report e Prompt ---
lbl_prompt = tk.Label(root, text="INTRO:")
lbl_prompt.grid(row=2, column=0, sticky="w", padx=10, pady=5)

entry_prompt = tk.Text(root, width=80, height=2)
entry_prompt.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
entry_prompt.bind("<KeyRelease>", mark_unsaved)

# Bottone "Mixa" spostato sulla stessa riga delle checkbox (riga 3, colonna 0)
def on_mix():
    mix_files(lbl_directory, entry_prompt, entry_extension, tree, report_text, include_prompt_var.get(), include_subdir_var.get())
    mark_unsaved()

btn_mix = tk.Button(root, text="Mixa", command=on_mix)
btn_mix.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

# Checkbox per le opzioni di inclusione
chk_include_prompt = tk.Checkbutton(root, text="Includi Intro", variable=include_prompt_var)
chk_include_prompt.grid(row=3, column=1, sticky="w", padx=10, pady=5)

chk_include_subdir = tk.Checkbutton(root, text="Includi Nome", variable=include_subdir_var)
chk_include_subdir.grid(row=3, column=2, sticky="w", padx=10, pady=5)



lbl_extension = tk.Label(root, text="Estensione dei file:")
lbl_extension.grid(row=4, column=0, sticky="w", padx=10, pady=5)

entry_extension = tk.Entry(root)
entry_extension.grid(row=4, column=1, sticky="ew", padx=10, pady=5)
entry_extension.bind("<KeyRelease>", mark_unsaved)

# Funzioni wrapper per il comando "Scegli Directory"
def update_dir_listing_for_choice(directory):
    update_directory_listing(directory, entry_extension, report_text)

def update_subdirs_list_for_choice(directory):
    update_subdirectories_list(directory, tree, entry_extension)

def on_choose_directory():
    choose_directory(lbl_directory, update_dir_listing_for_choice, update_subdirs_list_for_choice)
    mark_unsaved()

btn_choose_directory = tk.Button(root, text="Scegli Directory", command=on_choose_directory)
btn_choose_directory.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

lbl_directory = tk.Label(root, text="Directory non selezionata", anchor="w")
lbl_directory.grid(row=5, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# --- Sezione: Treeview per le subdirectories ---
# La Treeview include ora una sesta colonna "Azione"
tree = ttk.Treeview(root, columns=("subdirectory", "num_folders", "num_files", "num_extension_files", "extension_files", "copia"), show="headings")
tree.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
root.columnconfigure(2, weight=1)
root.rowconfigure(6, weight=1)

tree.column("subdirectory", anchor="w", width=200, minwidth=200)
tree.column("num_folders", anchor="center", width=100, minwidth=100)
tree.column("num_files", anchor="center", width=100, minwidth=100)
tree.column("num_extension_files", anchor="center", width=150, minwidth=150)
tree.column("extension_files", anchor="w", width=300, minwidth=300)
tree.column("copia", anchor="center", width=150, minwidth=150)

tree.heading("subdirectory", text="Subdirectory")
tree.heading("num_folders", text="Cartelle")
tree.heading("num_files", text="File")
tree.heading("num_extension_files", text="File con Estensione")
tree.heading("extension_files", text="Elenco File Estensione")
tree.heading("copia", text="Azione")

# Binding per gestire il click sulla colonna "Azione"
def on_treeview_click(event):
    region = tree.identify("region", event.x, event.y)
    if region == "cell":
        col = tree.identify_column(event.x)
        # La colonna "copia" è la sesta, identificata da "#6"
        if col == "#6":
            row_id = tree.identify_row(event.y)
            if row_id:
                values = tree.item(row_id, "values")
                subdir = values[0]  # Nome della subdirectory
                # Recupera la directory di lavoro
                selected_dir_text = lbl_directory.cget("text")
                if selected_dir_text.startswith("Directory selezionata: "):
                    selected_dir = selected_dir_text.replace("Directory selezionata: ", "")
                else:
                    selected_dir = ""
                mix_file_path = os.path.join(selected_dir, "00_MixOutput", f"{subdir}_mix.txt")
                if os.path.exists(mix_file_path):
                    try:
                        with open(mix_file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        root.clipboard_clear()
                        root.clipboard_append(content)
                        messagebox.showinfo("Copia in Clipboard", f"Contenuto di {subdir}_mix.txt copiato nella clipboard.")
                    except Exception as e:
                        messagebox.showerror("Errore", f"Errore nella copia: {str(e)}")
                else:
                    messagebox.showwarning("Attenzione", "File di mix non presente per questa subdirectory.")

tree.bind("<Button-1>", on_treeview_click)

# --- Sezione: Altre Azioni ---
def on_analyze():
    analyze_similarities(lbl_directory, report_text)

btn_analyze = tk.Button(root, text="Analizza Similarità", command=on_analyze)
btn_analyze.grid(row=7, column=0, sticky="ew", padx=10, pady=5)

def on_merge():
    merge_all_files(lbl_directory, report_text)
    mark_unsaved()

btn_merge_files = tk.Button(root, text="MEGAmerge", command=on_merge)
btn_merge_files.grid(row=7, column=1, sticky="ew", padx=10, pady=5)

def on_open_directory():
    directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    open_selected_directory(directory)

btn_open_directory = tk.Button(root, text="Apri Directory Output", command=on_open_directory)
btn_open_directory.grid(row=7, column=2, sticky="ew", padx=10, pady=5)



# --- Sezione: Report ---
lbl_report = tk.Label(root, text="Report:")
lbl_report.grid(row=9, column=0, sticky="nw", padx=10, pady=5)

report_text = tk.Text(root, width=1024, height=12)
report_text.grid(row=10, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

scrollbar = tk.Scrollbar(root, orient="vertical", command=report_text.yview)
scrollbar.grid(row=10, column=3, sticky="ns", pady=5)
report_text.config(yscrollcommand=scrollbar.set)

# --- Sezione: Barra dei Menù ---

def on_save_config():
    """
    Salva la configurazione corrente in un file JSON, includendo anche la directory di lavoro.
    """
    global config_saved
    config = {
        "remote_directory": entry_remote_directory.get(),
        "prompt_text": entry_prompt.get("1.0", "end").strip(),
        "extension": entry_extension.get(),
        "include_prompt": include_prompt_var.get(),
        "include_subdir": include_subdir_var.get()
    }
    lbl_text = lbl_directory.cget("text")
    if lbl_text.startswith("Directory selezionata: "):
        config["selected_directory"] = lbl_text.replace("Directory selezionata: ", "")
    else:
        config["selected_directory"] = ""
    
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        config_saved = True

def on_load_config():
    """
    Carica la configurazione da un file JSON, aggiorna i campi della GUI e la sezione Treeview.
    """
    global config_saved
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Aggiorna i campi
        entry_remote_directory.delete(0, "end")
        entry_remote_directory.insert(0, config.get("remote_directory", ""))
        
        entry_prompt.delete("1.0", "end")
        entry_prompt.insert("1.0", config.get("prompt_text", ""))
        
        entry_extension.delete(0, "end")
        entry_extension.insert(0, config.get("extension", ""))
        
        include_prompt_var.set(config.get("include_prompt", True))
        include_subdir_var.set(config.get("include_subdir", True))
        
        selected_directory = config.get("selected_directory", "")
        if selected_directory:
            lbl_directory.config(text=f"Directory selezionata: {selected_directory}")
            update_dir_listing_for_choice(selected_directory)
            update_subdirs_list_for_choice(selected_directory)
        else:
            lbl_directory.config(text="Directory non selezionata")
        
        config_saved = True

def on_exit():
    """
    Verifica se la configurazione corrente è stata salvata. Se non lo è,
    propone all'utente di salvarla prima di uscire.
    """
    global config_saved
    if not config_saved:
        risposta = messagebox.askyesnocancel("Configurazione non salvata",
                                              "La configurazione corrente non è stata salvata. Vuoi salvarla prima di uscire?")
        if risposta is None:
            return  # Annulla l'uscita
        elif risposta:
            on_save_config()
    root.destroy()

menubar = tk.Menu(root)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Salva Configurazione", command=on_save_config)
filemenu.add_command(label="Carica Configurazione", command=on_load_config)
filemenu.add_separator()
filemenu.add_command(label="Esci", command=on_exit)
menubar.add_cascade(label="File", menu=filemenu)
root.config(menu=menubar)

# Avvio del mainloop
root.mainloop()
