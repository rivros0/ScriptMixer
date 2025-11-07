# frame_associa.py

import os
import tkinter as tk
from tkinter import messagebox, Scrollbar, ttk


def _email_local_part(email: str) -> str:
    """
    Restituisce solo la parte locale dell'email (prima della @).
    Esempio:
      'nome.cognome@pantanelli-monnet.edu.it' -> 'nome.cognome'
    Se non c'è '@', restituisce la stringa così com'è.
    """
    email = email.strip()
    if "@" in email:
        return email.split("@", 1)[0]
    return email


def open_associa_window(root, global_config):
    """
    Finestra per associare gli indirizzi email degli alunni
    alle cartelle di test della directory locale selezionata.

    Funzionamento:

      - Usa global_config["selected_directory"] come base:
            <...>/20251107_10-30_VerificaTPSI
        che contiene le cartelle:
            test01, test02, ...

      - Colonna sinistra:
          * Text dove incollare le email (una per riga)
          * Pulsante "Aggiorna lista email" che le mette in una Listbox
          * Listbox di email selezionabili

      - Colonna destra:
          * Listbox delle cartelle (test01, test02, test03... eventuali suffissi compresi)

      - Sotto:
          * Tabella "Associazioni" (cartella ↔ email)
          * Pulsante "Associa selezionati" → cartella/email scelti nella GUI
          * Pulsante "Associa automaticamente (in ordine)"
          * Pulsante "Applica e rinomina cartelle" → crea i nomi:
                test01__nome.cognome2009
                test02__nome.cognome2009
            (in fase di rinomina viene usata SOLO la parte prima della @)
    """

    win = tk.Toplevel(root)
    win.title("Associa email a cartelle di test")
    win.geometry("1000x600")
    win.configure(bg="white")

    # ------------------------------------------------------------------
    #   Directory di lavoro attuale
    # ------------------------------------------------------------------
    base_dir_var = tk.StringVar()

    def get_current_base_dir():
        sel = global_config.get("selected_directory")
        if sel is None:
            return ""
        path = sel.get().strip()
        if not path or path.lower() == "nessuna":
            return ""
        return path

    def update_base_dir_label():
        path = get_current_base_dir()
        if not path:
            base_dir_var.set("Directory di lavoro: (nessuna)")
        else:
            base_dir_var.set(f"Directory di lavoro: {path}")

    lbl_base_dir = tk.Label(
        win,
        textvariable=base_dir_var,
        bg="white",
        anchor="w",
    )
    lbl_base_dir.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

    update_base_dir_label()

    # ------------------------------------------------------------------
    #   COLONNA SINISTRA: TEXT + LISTA EMAIL
    # ------------------------------------------------------------------
    left_frame = tk.Frame(win, bg="white")
    left_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    lbl_emails_text = tk.Label(
        left_frame,
        text="Incolla qui le email (una per riga):",
        bg="white",
        anchor="w",
    )
    lbl_emails_text.pack(anchor="w")

    text_emails = tk.Text(left_frame, width=45, height=8)
    text_emails.pack(fill="x", expand=False)

    lbl_emails_list = tk.Label(
        left_frame,
        text="Email (seleziona per associare):",
        bg="white",
        anchor="w",
    )
    lbl_emails_list.pack(anchor="w", pady=(10, 0))

    listbox_emails = tk.Listbox(left_frame, width=45, height=10)
    listbox_emails.pack(side="left", fill="both", expand=True, pady=(0, 5))

    scroll_emails = Scrollbar(left_frame, orient="vertical", command=listbox_emails.yview)
    scroll_emails.pack(side="right", fill="y", pady=(0, 5))
    listbox_emails.config(yscrollcommand=scroll_emails.set)

    def parse_emails_from_text():
        raw = text_emails.get("1.0", "end")
        emails = [line.strip() for line in raw.splitlines() if line.strip()]
        return emails

    def update_email_list():
        listbox_emails.delete(0, "end")
        emails = parse_emails_from_text()
        if not emails:
            listbox_emails.insert("end", "(Nessuna email)")
            return
        for e in emails:
            listbox_emails.insert("end", e)

    btn_update_email_list = tk.Button(
        left_frame,
        text="Aggiorna lista email",
        command=update_email_list,
        bg="white",
    )
    btn_update_email_list.pack(anchor="w", pady=5)

    # ------------------------------------------------------------------
    #   COLONNA DESTRA: LISTA CARTELLE TEST
    # ------------------------------------------------------------------
    right_frame = tk.Frame(win, bg="white")
    right_frame.grid(row=1, column=2, sticky="nsew", padx=10, pady=10)

    lbl_folders = tk.Label(
        right_frame,
        text="Cartelle nella directory di lavoro (seleziona test):",
        bg="white",
        anchor="w",
    )
    lbl_folders.pack(anchor="w")

    listbox_folders = tk.Listbox(right_frame, width=45, height=20)
    listbox_folders.pack(side="left", fill="both", expand=True)

    scroll_folders = Scrollbar(right_frame, orient="vertical", command=listbox_folders.yview)
    scroll_folders.pack(side="right", fill="y")
    listbox_folders.config(yscrollcommand=scroll_folders.set)

    def refresh_folders():
        listbox_folders.delete(0, "end")
        base_dir = get_current_base_dir()

        if not base_dir:
            listbox_folders.insert("end", "(Nessuna directory selezionata)")
            return

        if not os.path.isdir(base_dir):
            listbox_folders.insert("end", f"(Directory non valida: {base_dir})")
            return

        subdirs = [
            d
            for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d))
        ]
        subdirs.sort()

        if not subdirs:
            listbox_folders.insert("end", "(Nessuna sottocartella trovata)")
            return

        for d in subdirs:
            listbox_folders.insert("end", d)

    refresh_folders()

    # ------------------------------------------------------------------
    #   COLONNA CENTRALE: PULSANTI DI ASSOCIAZIONE
    # ------------------------------------------------------------------
    center_frame = tk.Frame(win, bg="white")
    center_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

    btn_refresh_all = tk.Button(
        center_frame,
        text="Aggiorna directory / cartelle",
        command=lambda: (update_base_dir_label(), refresh_folders()),
        bg="white",
    )
    btn_refresh_all.pack(pady=5)

    # Dizionario delle associazioni scelte tramite GUI:
    #   { "nome_cartella": "email_completa" }
    associations = {}

    # ------------------------------------------------------------------
    #   TABELLA ASSOCIAZIONI
    # ------------------------------------------------------------------
    mapping_frame = tk.Frame(win, bg="white")
    mapping_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

    lbl_mapping = tk.Label(
        mapping_frame,
        text="Associazioni (cartella ↔ email):",
        bg="white",
        anchor="w",
    )
    lbl_mapping.pack(anchor="w")

    tree_mapping = ttk.Treeview(
        mapping_frame,
        columns=("cartella", "email"),
        show="headings",
        height=8,
    )
    tree_mapping.heading("cartella", text="Cartella")
    tree_mapping.heading("email", text="Email")

    tree_mapping.column("cartella", width=200, anchor="w")
    tree_mapping.column("email", width=400, anchor="w")

    tree_mapping.pack(side="left", fill="both", expand=True)

    scroll_mapping = Scrollbar(mapping_frame, orient="vertical", command=tree_mapping.yview)
    scroll_mapping.pack(side="right", fill="y")
    tree_mapping.config(yscrollcommand=scroll_mapping.set)

    def refresh_mapping_tree():
        tree_mapping.delete(*tree_mapping.get_children())
        for cartella in sorted(associations.keys()):
            tree_mapping.insert(
                "",
                "end",
                values=(cartella, associations[cartella]),
            )

    def do_associate_selected():
        """
        Associa l'email selezionata (sinistra) alla cartella selezionata (destra).
        Non rinomina ancora sul disco: aggiorna solo 'associations' e la tabella.
        """
        sel_email_idx = listbox_emails.curselection()
        if not sel_email_idx:
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima un'email nella lista a sinistra.",
            )
            return

        email = listbox_emails.get(sel_email_idx[0])
        if not email or email.startswith("("):
            messagebox.showwarning(
                "Attenzione",
                "La riga selezionata nella lista email non è valida.",
            )
            return

        sel_folder_idx = listbox_folders.curselection()
        if not sel_folder_idx:
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima una cartella di test nella lista a destra.",
            )
            return

        folder = listbox_folders.get(sel_folder_idx[0])
        if not folder or folder.startswith("("):
            messagebox.showwarning(
                "Attenzione",
                "La riga selezionata nella lista cartelle non è valida.",
            )
            return

        associations[folder] = email
        refresh_mapping_tree()

    btn_associate_selected = tk.Button(
        center_frame,
        text="Associa selezionati →",
        command=do_associate_selected,
        bg="white",
    )
    btn_associate_selected.pack(pady=10)

    def do_associate_sequential():
        """
        Comodità: associa in automatico in ordine:
          1ª email -> 1ª cartella, 2ª -> 2ª, ecc.
        """
        emails = parse_emails_from_text()
        base_dir = get_current_base_dir()

        if not base_dir or not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima una directory locale valida.",
            )
            return

        folders = []
        for i in range(listbox_folders.size()):
            name = listbox_folders.get(i)
            if not name or name.startswith("("):
                continue
            folders.append(name)

        if not emails or not folders:
            messagebox.showwarning(
                "Attenzione",
                "Servono almeno una email e una cartella di test.",
            )
            return

        count = min(len(emails), len(folders))

        for i in range(count):
            associations[folders[i]] = emails[i]

        refresh_mapping_tree()

        messagebox.showinfo(
            "Associazione in ordine",
            f"Create {count} associazioni (email ↔ cartella) in ordine.",
        )

    btn_associate_seq = tk.Button(
        center_frame,
        text="Associa automaticamente (in ordine)",
        command=do_associate_sequential,
        bg="white",
    )
    btn_associate_seq.pack(pady=5)

    # ------------------------------------------------------------------
    #   APPLICA: RINOMINA FISICAMENTE LE CARTELLE
    # ------------------------------------------------------------------
    def do_apply_and_rename():
        base_dir = get_current_base_dir()
        if not base_dir:
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima una directory locale (copiata dal server).",
            )
            return

        if not os.path.isdir(base_dir):
            messagebox.showwarning(
                "Attenzione",
                f"La directory selezionata non esiste:\n{base_dir}",
            )
            return

        if not associations:
            messagebox.showwarning(
                "Attenzione",
                "Non ci sono associazioni da applicare.\n"
                "Usa 'Associa selezionati' o 'Associa automaticamente (in ordine)'.",
            )
            return

        riepilogo = "\n".join(
            f"{cartella}  ->  {email}"
            for cartella, email in sorted(associations.items())
        )
        conferma = messagebox.askyesno(
            "Conferma rinomina cartelle",
            "Verranno rinominate le seguenti cartelle:\n\n"
            f"{riepilogo}\n\n"
            "Nel nome della cartella verrà usata SOLO la parte prima di '@'.\n\n"
            "Procedere?",
        )
        if not conferma:
            return

        rinominate = 0
        errori = 0

        for old_name, email in associations.items():
            # base_name: parte prima di eventuale "__"
            if "__" in old_name:
                base_name = old_name.split("__", 1)[0]
            else:
                base_name = old_name

            local = _email_local_part(email)  # <-- qui togliamo il dominio
            new_name = f"{base_name}__{local}"

            old_path = os.path.join(base_dir, old_name)
            new_path = os.path.join(base_dir, new_name)

            if not os.path.exists(old_path):
                errori += 1
                continue

            if os.path.exists(new_path) and old_path != new_path:
                errori += 1
                continue

            try:
                os.rename(old_path, new_path)
                rinominate += 1
            except Exception as e:
                errori += 1
                messagebox.showerror(
                    "Errore",
                    f"Errore nel rinominare '{old_name}' in '{new_name}':\n{e}",
                )

        associations.clear()
        refresh_mapping_tree()
        refresh_folders()

        messagebox.showinfo(
            "Operazione completata",
            f"Cartelle rinominate: {rinominate}\n"
            f"Eventuali errori: {errori}",
        )

    btn_apply = tk.Button(
        center_frame,
        text="Applica e rinomina cartelle",
        command=do_apply_and_rename,
        bg="#d0ffd0",
    )
    btn_apply.pack(pady=15)

    # ------------------------------------------------------------------
    #   LAYOUT DINAMICO
    # ------------------------------------------------------------------
    win.grid_rowconfigure(1, weight=1)
    win.grid_rowconfigure(2, weight=1)
    win.grid_columnconfigure(0, weight=1)
    win.grid_columnconfigure(1, weight=0)
    win.grid_columnconfigure(2, weight=1)
