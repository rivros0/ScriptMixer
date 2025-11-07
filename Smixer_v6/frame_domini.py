import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
import threading
from ftplib import FTP, error_perm

YELLOW_BG = "#fff5cc"

def create_frame_domini(root, global_config):
    f = tk.Frame(root, bg=YELLOW_BG)

    # === Riga 1: Pulsanti ===
    btn_carica = tk.Button(f, text="Carica file domini (CSV)", width=25)
    btn_carica.grid(row=0, column=0, padx=6, pady=6)

    btn_scarica = tk.Button(f, text="Scarica tutti i domini via FTP", width=25, state="disabled")
    btn_scarica.grid(row=0, column=1, padx=6, pady=6)

    btn_analizza = tk.Button(f, text="Analizza somiglianze", width=25, state="disabled")
    btn_analizza.grid(row=0, column=2, padx=6, pady=6)

    btn_mappa = tk.Button(f, text="Mostra mappa similitudini", width=25, state="disabled")
    btn_mappa.grid(row=0, column=3, padx=6, pady=6)

    # === Riga 2: Tabella ===
    cols = ("Cognome", "Dominio", "FTP user", "FTP password", "Cartella test", "Stato")
    tree = ttk.Treeview(f, columns=cols, show="headings", height=18)
    for c in cols:
        tree.heading(c, text=c)
        width = 120 if c != "Cognome" else 130
        tree.column(c, width=width, anchor="center")
    tree.grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

    vsb = ttk.Scrollbar(f, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=1, column=4, sticky="ns")

    # === Riga 3: Log ===
    tk.Label(f, text="Log eventi:", bg=YELLOW_BG).grid(row=2, column=0, sticky="w", padx=6, pady=6)
    txt_log = tk.Text(f, height=6, width=120)
    txt_log.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

    def log(msg):
        txt_log.insert("end", msg + "\n")
        txt_log.see("end")

    # === CSV loader ===
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

                    found_test = ""
                    stato = "⚠️ Non trovata"
                    for td in test_dirs:
                        if td.lower().endswith(cognome):
                            found_test = td
                            stato = "✅ Associata"
                            break

                    tree.insert("", "end", values=(cognome, dominio, ftp_user, ftp_pass, found_test, stato))

                log(f"File CSV '{os.path.basename(path)}' caricato correttamente.")
                btn_scarica.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella lettura del CSV:\n{e}")
            return

    btn_carica.configure(command=carica_csv)

    # === Download FTP ===
    def scarica_tutti():
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning("Attenzione", "Seleziona prima la directory principale delle prove (cartelle testXX).")
            return

        destinazione = os.path.join(base_dir, "00_DominiFTP")
        os.makedirs(destinazione, exist_ok=True)

        items = tree.get_children()
        if not items:
            messagebox.showwarning("Attenzione", "Nessun dominio da scaricare. Carica prima il CSV.")
            return

        log(f"=== Inizio download FTP in {destinazione} ===")

        def thread_worker():
            for item in items:
                valori = tree.item(item, "values")
                cognome, dominio, ftp_user, ftp_pass = valori[0], valori[1], valori[2], valori[3]
                host = dominio
                if not host.startswith("ftp."):
                    host = f"ftp.{host}"

                local_dir = os.path.join(destinazione, cognome)
                os.makedirs(local_dir, exist_ok=True)

                log(f"Connessione a {host}...")
                try:
                    ftp = FTP(host, timeout=30)
                    ftp.login(user=ftp_user, passwd=ftp_pass)
                    log(f"✅ Login riuscito su {host}")
                except Exception as e:
                    log(f"❌ Errore di connessione/login {host}: {e}")
                    continue

                def recursive_download(path="."):
                    try:
                        ftp.cwd(path)
                        files = ftp.nlst()
                        for nome in files:
                            try:
                                ftp.cwd(nome)
                                ftp.cwd("..")
                                new_path = os.path.join(local_dir, nome)
                                os.makedirs(new_path, exist_ok=True)
                                recursive_download(nome)
                                ftp.cwd("..")
                            except error_perm:
                                local_file = os.path.join(local_dir, nome)
                                with open(local_file, "wb") as f:
                                    ftp.retrbinary(f"RETR {nome}", f.write)
                    except Exception:
                        pass

                try:
                    recursive_download(".")
                    ftp.quit()
                    log(f"✅ Download completato per {cognome} ({dominio})\n")
                except Exception as e:
                    log(f"❌ Errore durante il download di {cognome}: {e}\n")

            log("=== Download FTP completato ===")
            btn_analizza.configure(state="normal")

        threading.Thread(target=thread_worker, daemon=True).start()

    btn_scarica.configure(command=scarica_tutti)

    f.grid_rowconfigure(1, weight=1)
    f.grid_columnconfigure(3, weight=1)

    log("Frame domini attivo. In attesa di caricamento CSV...")

    return f
