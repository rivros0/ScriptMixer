import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

def mix_files():
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    prompt_string = entry_prompt.get("1.0", tk.END).strip()
    extension = entry_extension.get()

    output_directory = os.path.join(selected_directory, "MixOutput")
    os.makedirs(output_directory, exist_ok=True)

    report_text.delete(1.0, tk.END)  # Pulisce il campo di testo del report

    for item in tree.get_children():
        subdir = tree.item(item, "values")[0]
        mix_result = create_mix_file(selected_directory, subdir, prompt_string, extension, output_directory)
        report_text.insert(tk.END, mix_result)

def create_mix_file(base_directory, subdir, prompt_string, extension, output_directory):
    full_path = os.path.join(base_directory, subdir)
    mix_file_path = os.path.join(output_directory, f"{subdir}_mix.txt")

    try:
        with open(mix_file_path, "w") as mix_file:
            mix_file.write(prompt_string + "\n")

            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith(extension):
                        file_path = os.path.join(root, file)
                        with open(file_path, "r") as current_file:
                            mix_file.write(f"{file}\n{current_file.read()}\n")

        tree.tag_configure(subdir, background="green")
        return f"Mix completato per {subdir}: file {extension} creato con successo.\n"
    except Exception as e:
        return f"Errore durante il mix per {subdir}: {str(e)}\n"

def choose_directory():
    selected_directory = filedialog.askdirectory()
    if selected_directory:
        lbl_directory.config(text=f"Directory selezionata: {selected_directory}")
        update_subdirectories_list(selected_directory)

def update_subdirectories_list(selected_directory):
    subdirectories = [d for d in os.listdir(selected_directory) if os.path.isdir(os.path.join(selected_directory, d))]
    subdirectories.sort()

    max_subdir_length = max([len(subdir) for subdir in subdirectories], default=0)

    tree.delete(*tree.get_children())

    for subdir in subdirectories:
        check_directory_content(selected_directory, subdir)

def check_directory_content(base_directory, subdir):
    full_path = os.path.join(base_directory, subdir)

    num_folders, num_files, num_extension_files, extension_files = count_directory_content(full_path)

    has_content = num_folders + num_files > 0
    icon_color = "yellow" if has_content else "gray"

    subtree = tree.insert("", "end", values=(subdir, num_folders, num_files, num_extension_files, extension_files))
    tree.tag_configure(subdir, background=icon_color)

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

# Creazione dell'interfaccia grafica
root = tk.Tk()
root.title("Ninei - Smixer_v1")
root.geometry("1024x768")

# Stringa Prompt
lbl_prompt = tk.Label(root, text="Stringa Prompt:")
lbl_prompt.pack(pady=5)

entry_prompt = tk.Text(root, width=1024, height=12)
entry_prompt.pack(pady=5)

# Estensione file
lbl_extension = tk.Label(root, text="Estensione dei file:")
lbl_extension.pack(pady=10)

entry_extension = tk.Entry(root)
entry_extension.pack()

# Bottone Scegli Directory
btn_choose_directory = tk.Button(root, text="Scegli Directory", command=choose_directory)
btn_choose_directory.pack()

lbl_directory = tk.Label(root, text="")
lbl_directory.pack()

# Lista delle subdirectories con icona di stato e numero di cartelle, file, file con estensione
tree = ttk.Treeview(root, columns=("subdirectory", "num_folders", "num_files", "num_extension_files", "extension_files"), show="headings")
tree.pack(pady=10, fill=tk.BOTH, expand=True)

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

# Bottone Mixa
btn_mix = tk.Button(root, text="Mixa", command=mix_files)
btn_mix.pack(pady=10,)

# Directory di output
#lbl_output_directory = tk.Label(root, text="Directory di Output:")
#lbl_output_directory.pack()

#entry_output_directory = tk.Entry(root)
#entry_output_directory.pack()

# Report
lbl_report = tk.Label(root, text="Report:")
lbl_report.pack(pady=5)

report_text = tk.Text(root, width=1024, height=12)
report_text.pack(pady=5)

root.mainloop()
