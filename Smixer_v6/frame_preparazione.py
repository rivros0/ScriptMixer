import os
import datetime
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText

import utils


def create_frame_preparazione(root, global_config):
    frame = tk.Frame(root, bg="lightyellow")

    # ============ RIGA 1: Directory base ============ #
    tk.Label(frame, text="Directory base:", bg="lightyellow").grid(
        row=0, column=0, sticky="w", padx=8, pady=8
    )
    tk.Entry(
        frame, width=80, textvariable=global_config["remote_directory"]
    ).grid(row=0, column=1, padx=5, pady=8, columnspan=3, sticky="we")

    def scegli_directory():
        directory = filedialog.askdirectory(title="Seleziona directory base")
        if directory:
            global_config["remote_directory"].set(directory)
            log(f"Directory base impostata: {directory}")

    tk.Button(frame, text="Scegli...", command=scegli_directory).grid(
        row=0, column=4, padx=8, pady=8, sticky="w"
    )

    # ============ RIGA 2: Pulsanti ============ #
    btn_scan = tk.Button(frame, text="Scan", width=16)
    btn_scan.grid(row=1, column=0, padx=8, pady=4, sticky="w")

    btn_copia = tk.Button(frame, text="Crea copia locale", width=20)
    btn_copia.grid(row=1, column=1, padx=8, pady=4, sticky="w")

    btn_distribuisci = tk.Button(frame, text="Distribuisci file", width=18)
    btn_distribuisci.grid(row=1, column=2, padx=8, pady=4, sticky="w")

    # Spaziatore per distribuire bene la riga
    tk.Label(frame, text="", bg="lightyellow").grid(row=1, column=3, sticky="we")
    frame.grid_columnconfigure(3, weight=1)

    # ============ AREA TABELLA (Treeview) ============ #
    tree = ttk.Treeview(
        frame,
        columns=("cartella", "num_file", "elenco_file", "ultima_modifica"),
        show="headings",
    )
    tree.heading("cartella", text="Cartella")
    tree.heading("num_file", text="N. File")
    tree.heading("elenco_file", text="File trovati")
    tree.heading("ultima_modifica", text="Ultima modifica")

    tree.column("cartella", width=200)
    tree.column("num_file", width=80, anchor="center")
    tree.column("elenco_file", width=520, anchor="w")
    tree.column("ultima_modifica", width=170, anchor="center")

    tree.grid(row=2, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")
    frame.grid_rowconfigure(2, weight=1)
    frame.grid_columnconfigure(2, weight=1)

    # ============ AZIONI ============ #
    def aggiorna_tabella():
        path = global_config["remote_directory"].get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Attenzione", "Seleziona prima una directory valida.")
            return
        tree.delete(*tree.get_children())
        # SOLO test01..test30
        risultati = utils.scan_test_directories(path, extension="", root_prefix="test*")
        for nome_dir, num_file, files, ultima_mod in risultati:
            tree.insert("", "end", values=(nome_dir, num_file, ", ".join(files), ultima_mod))
        log("Scansione completata (solo cartelle test01..test30).")

    btn_scan.config(command=aggiorna_tabella)

    def crea_copia_locale():
        """
        Copia SOLO le cartelle test01..test30 nella cartella destinazione scelta,
        in una nuova sottocartella dal nome indicato dall'utente.
        """
        base = global_config["remote_directory"].get().strip()
        if not base or not os.path.isdir(base):
            messagebox.showwarning("Attenzione", "Seleziona prima una directory base valida.")
            return

        destinazione = filedialog.askdirectory(title="Seleziona cartella di destinazione")
        if not destinazione:
            return

        default_name = datetime.datetime.now().strftime("%Y%m%d_%H%M") + "_preparazione"
        nome_cartella = simpledialog.askstring(
            "Nome cartella",
            "Inserisci il nome della cartella di destinazione:",
            initialvalue=default_name,
            parent=frame,
        )
        if not nome_cartella:
            return

        new_dir = os.path.join(destinazione, nome_cartella)
        try:
            os.makedirs(new_dir, exist_ok=True)

            # Copia SOLO test01..test30
            for i in range(1, 31):
                nome_dir = f"test{str(i).zfill(2)}"
                src_dir = os.path.join(base, nome_dir)
                if not os.path.isdir(src_dir):
                    continue
                dest_dir = os.path.join(new_dir, nome_dir)
                os.makedirs(dest_dir, exist_ok=True)

                for root_dir, dirs, files in os.walk(src_dir):
                    rel_path = os.path.relpath(root_dir, src_dir)
                    final_dest = os.path.join(dest_dir, rel_path)
                    os.makedirs(final_dest, exist_ok=True)
                    for file in files:
                        src_file = os.path.join(root_dir, file)
                        dest_file = os.path.join(final_dest, file)
                        try:
                            with open(src_file, "rb") as fsrc, open(dest_file, "wb") as fdst:
                                fdst.write(fsrc.read())
                        except Exception as e:
                            log(f"Errore copiando {src_file}: {e}")

            messagebox.showinfo("Copia completata", f"I file sono stati copiati in:\n{new_dir}")
            log(f"Copia locale completata in: {new_dir}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la copia: {e}")
            log(f"Errore copia locale: {e}")

    btn_copia.config(command=crea_copia_locale)

    def distribuisci_file():
        """
        Sceglie un file da distribuire e lo copia in tutte le cartelle test01..test30.
        """
        base = global_config["remote_directory"].get().strip()
        if not base or not os.path.isdir(base):
            messagebox.showwarning("Attenzione", "Seleziona prima una directory base valida.")
            return

        file_path = filedialog.askopenfilename(title="Seleziona file da distribuire")
        if not file_path:
            return

        try:
            nome_file = os.path.basename(file_path)
            # Determina cartelle target SOLO test01..test30
            names = [t[0] for t in utils.scan_test_directories(base, extension="", root_prefix="test*")]
            if not names:
                messagebox.showinfo("Info", "Nessuna cartella testXX trovata.")
                return

            for nome_dir in names:
                full_path = os.path.join(base, nome_dir)
                os.makedirs(full_path, exist_ok=True)
                dest_path = os.path.join(full_path, nome_file)
                with open(file_path, "rb") as fsrc, open(dest_path, "wb") as fdst:
                    fdst.write(fsrc.read())

            messagebox.showinfo("Distribuzione completata", f"File '{nome_file}' distribuito nelle cartelle test.")
            log(f"Distribuzione completata: {nome_file} -> cartelle test")
            aggiorna_tabella()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la distribuzione: {e}")
            log(f"Errore distribuzione: {e}")

    btn_distribuisci.config(command=distribuisci_file)

    # ============ PULISCI CARTELLE TEST ============ #
    def pulisci_cartelle():
        path = global_config["remote_directory"].get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Attenzione", "Seleziona prima una directory valida.")
            return
        if not messagebox.askyesno(
            "Conferma", "Vuoi davvero cancellare TUTTI i contenuti (solo nelle cartelle test01..test30)?"
        ):
            return
        if not messagebox.askyesno("Conferma finale", "L'operazione è irreversibile. Procedere?"):
            return

        try:
            names = [t[0] for t in utils.scan_test_directories(path, extension="", root_prefix="test*")]
            for nome_dir in names:
                full_path = os.path.join(path, nome_dir)
                for root_dir, dirs, files in os.walk(full_path, topdown=False):
                    for f in files:
                        try:
                            os.remove(os.path.join(root_dir, f))
                        except Exception as e:
                            log(f"Errore eliminando file {f}: {e}")
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root_dir, d))
                        except Exception as e:
                            log(f"Errore eliminando cartella {d}: {e}")

            messagebox.showinfo("Completato", "Pulizia completata nelle cartelle test.")
            log("Pulizia completata (solo test01..test30).")
            aggiorna_tabella()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la cancellazione: {e}")
            log(f"Errore pulizia: {e}")

    tk.Button(
        frame, text="Pulisci cartelle test", bg="red", fg="white", command=pulisci_cartelle
    ).grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    # ============ LOG IN CALCE ============ #
    tk.Label(frame, text="Log:", bg="lightyellow").grid(row=4, column=0, sticky="w", padx=10)
    log_area = ScrolledText(frame, height=6, wrap="word")
    log_area.grid(row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="nsew")

    frame.grid_rowconfigure(5, weight=0)

    def log(msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        log_area.insert("end", f"[{ts}] {msg}\n")
        log_area.see("end")

    # prima scansione automatica (opzionale, commenta se non la vuoi)
    # aggiorna_tabella()

    return frame
