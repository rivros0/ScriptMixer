import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import webbrowser

YELLOW_BG = "#fff5cc"

def create_frame_domini(root, global_config):
    f = tk.Frame(root, bg=YELLOW_BG)

    # === Riga 1: Nome e Directory selezionata ===
    tk.Label(f, text="Nome:", bg=YELLOW_BG).grid(row=0, column=0, sticky="w", padx=6, pady=6)
    ent_nome = tk.Entry(f, width=25)
    ent_nome.grid(row=0, column=1, sticky="w", padx=6, pady=6)

    tk.Label(f, text="Directory selezionata:", bg=YELLOW_BG).grid(row=0, column=2, sticky="w", padx=6, pady=6)
    lbl_dir = tk.Label(f, textvariable=global_config["selected_directory"], fg="blue", cursor="hand2", bg=YELLOW_BG)
    lbl_dir.grid(row=0, column=3, sticky="w", padx=6, pady=6)

    def apri_dir(event):
        d = global_config["selected_directory"].get()
        if d and os.path.isdir(d):
            webbrowser.open(d)
    lbl_dir.bind("<Button-1>", apri_dir)

    # === Riga 2: Pulsanti ===
    btn_carica = tk.Button(f, text="Carica file domini (CSV)", width=25)
    btn_carica.grid(row=1, column=0, padx=6, pady=6)

    btn_scarica = tk.Button(f, text="Scarica tutti i domini via FTP", width=25, state="disabled")
    btn_scarica.grid(row=1, column=1, padx=6, pady=6)

    btn_analizza = tk.Button(f, text="Analizza somiglianze", width=25, state="disabled")
    btn_analizza.grid(row=1, column=2, padx=6, pady=6)

    btn_mappa = tk.Button(f, text="Mostra mappa similitudini", width=25, state="disabled")
    btn_mappa.grid(row=1, column=3, padx=6, pady=6)

    # === Riga 3: Tabella ===
    cols = ("Cognome", "Dominio", "FTP user", "FTP password", "Cartella test", "Stato")
    tree = ttk.Treeview(f, columns=cols, show="headings", height=16)
    for c in cols:
        tree.heading(c, text=c)
        width = 120 if c != "Cognome" else 130
        tree.column(c, width=width, anchor="center")
    tree.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

    vsb = ttk.Scrollbar(f, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=2, column=4, sticky="ns")

    # === Riga 4: Log ===
    tk.Label(f, text="Log eventi:", bg=YELLOW_BG).grid(row=3, column=0, sticky="w", padx=6, pady=6)
    txt_log = tk.Text(f, height=6, width=120)
    txt_log.grid(row=4, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

    def log(msg):
        txt_log.insert("end", msg + "\n")
        txt_log.see("end")

    # === Funzione principale: caricamento CSV ===
    def carica_csv():
        path = filedialog.askopenfilename(
            title="Seleziona file CSV con domini",
            filetypes=[("File CSV", "*.csv"), ("Tutti i file", "*.*")]
        )
        if not path:
            return

        # pulizia tabella
        for i in tree.get_children():
            tree.delete(i)

        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning("Attenzione", "Seleziona prima la directory principale delle prove (cartelle testXX).")
            return

        # elenco cartelle test
        test_dirs = [d for d in os.listdir(base_dir) if d.lower().startswith("test") and os.path.isdir(os.path.join(base_dir, d))]
        log(f"Trovate {len(test_dirs)} cartelle test nella directory selezionata.")

        try:
            with open(path, newline='', encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    cognome = row.get("cognome", "").strip().lower()
                    dominio = row.get("dominio", "").strip()
                    ftp_user = row.get("ftp_user", "").strip()
                    ftp_pass = row.get("ftp_password", "").strip()

                    # ricerca cartella corrispondente
                    found_test = ""
                    stato = "⚠️ Non trovata"
                    for td in test_dirs:
                        if td.lower().endswith(cognome):
                            found_test = td
                            stato = "✅ Associata"
                            break

                    tree.insert("", "end", values=(cognome, dominio, ftp_user, ftp_pass, found_test, stato))

                log(f"File CSV '{os.path.basename(path)}' caricato correttamente.")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella lettura del CSV:\n{e}")
            return

    btn_carica.configure(command=carica_csv)

    # layout flessibile
    f.grid_rowconfigure(2, weight=1)
    f.grid_columnconfigure(3, weight=1)

    log("Frame domini attivo. In attesa di caricamento CSV...")

    return f
