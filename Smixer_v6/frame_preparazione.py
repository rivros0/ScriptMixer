import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import utils

def create_frame_preparazione(root, global_config):
    frame = tk.Frame(root, bg="lightyellow")

    # === Directory Base === #
    tk.Label(frame, text="Directory base:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    tk.Entry(frame, width=80, textvariable=global_config["remote_directory"]).grid(row=0, column=1, padx=5, pady=5, columnspan=3)

    def scegli_directory():
        directory = filedialog.askdirectory(title="Seleziona directory base")
        if directory:
            global_config["remote_directory"].set(directory)

    tk.Button(frame, text="Scegli...", command=scegli_directory).grid(row=0, column=4, padx=5, pady=5)

    # === Pulsanti controllo === #
    btn_scan = tk.Button(frame, text="Scansiona", width=15)
    btn_scan.grid(row=1, column=4, padx=5)
    tk.Button(frame, text="Pulisci tabella", width=15, command=lambda: tree.delete(*tree.get_children())).grid(row=1, column=3, padx=5)

    # === Tabella risultati === #
    tree = ttk.Treeview(frame, columns=("cartella", "num_file", "elenco_file", "ultima_modifica"), show="headings")
    tree.heading("cartella", text="Cartella")
    tree.heading("num_file", text="N. File")
    tree.heading("elenco_file", text="File trovati")
    tree.heading("ultima_modifica", text="Ultima modifica")
    tree.column("cartella", width=200)
    tree.column("num_file", width=70, anchor="center")
    tree.column("elenco_file", width=500)
    tree.column("ultima_modifica", width=160, anchor="center")
    tree.grid(row=2, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(3, weight=1)

    # === Scansione === #
    def aggiorna_tabella():
        path = global_config["remote_directory"].get().strip()
        if not path or not os.path.isdir(path):
            return
        tree.delete(*tree.get_children())
        risultati = utils.scan_test_directories(path, extension="")  # mostra sempre test01..30
        for nome_dir, num_file, files, ultima_mod in risultati:
            tree.insert("", "end", values=(nome_dir, num_file, ", ".join(files), ultima_mod))

    btn_scan.config(command=aggiorna_tabella)

    # === Pulisci cartelle test (solo test01..test30) === #
    def pulisci_cartelle():
        path = global_config["remote_directory"].get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Attenzione", "Seleziona prima una directory valida.")
            return

        if not messagebox.askyesno("Conferma", "Vuoi davvero cancellare TUTTI i contenuti delle cartelle test01..test30?"):
            return
        if not messagebox.askyesno("Conferma finale", "L'operazione è irreversibile. Procedere?"):
            return

        try:
            for i in range(1, 31):
                nome_dir = f"test{str(i).zfill(2)}"
                full_path = os.path.join(path, nome_dir)
                if not os.path.isdir(full_path):
                    continue
                for root_dir, dirs, files in os.walk(full_path, topdown=False):
                    for f in files:
                        try:
                            os.remove(os.path.join(root_dir, f))
                        except Exception as e:
                            print(f"Errore eliminando {f}: {e}")
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root_dir, d))
                        except Exception as e:
                            print(f"Errore eliminando cartella {d}: {e}")

            messagebox.showinfo("Completato", "Tutte le cartelle test01..test30 sono state svuotate.")
            aggiorna_tabella()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la cancellazione: {e}")

    tk.Button(frame, text="Pulisci cartelle test", bg="red", fg="white", command=pulisci_cartelle).grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    # === Distribuisci file (solo test01..test30) === #
    distribuzione_file = {"path": None}

    def scegli_file():
        file_path = filedialog.askopenfilename(title="Seleziona file da distribuire")
        if file_path:
            distribuzione_file["path"] = file_path
            lbl_file.config(text=f"File selezionato: {os.path.basename(file_path)}")

    def distribuisci_file():
        path = global_config["remote_directory"].get().strip()
        file_path = distribuzione_file["path"]
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Attenzione", "Seleziona prima una directory valida.")
            return
        if not file_path or not os.path.isfile(file_path):
            messagebox.showwarning("Attenzione", "Seleziona prima un file valido da distribuire.")
            return

        try:
            nome_file = os.path.basename(file_path)
            for i in range(1, 31):
                nome_dir = f"test{str(i).zfill(2)}"
                full_path = os.path.join(path, nome_dir)
                if not os.path.isdir(full_path):
                    continue
                dest_path = os.path.join(full_path, nome_file)
                with open(file_path, "rb") as fsrc, open(dest_path, "wb") as fdst:
                    fdst.write(fsrc.read())

            lbl_esito.config(text=f"✅ File '{nome_file}' distribuito a tutte le cartelle test01..test30.", fg="green")
            aggiorna_tabella()
        except Exception as e:
            lbl_esito.config(text=f"Errore: {e}", fg="red")

    tk.Button(frame, text="Scegli file", command=scegli_file).grid(row=4, column=0, padx=10, pady=10, sticky="ew")
    tk.Button(frame, text="Distribuisci file", command=distribuisci_file).grid(row=4, column=1, padx=10, pady=10, sticky="ew")
    lbl_file = tk.Label(frame, text="Nessun file selezionato", anchor="w")
    lbl_file.grid(row=4, column=2, columnspan=2, sticky="ew", padx=10)
    lbl_esito = tk.Label(frame, text="", fg="green", anchor="w")
    lbl_esito.grid(row=5, column=0, columnspan=5, sticky="ew", padx=10, pady=5)

    return frame
