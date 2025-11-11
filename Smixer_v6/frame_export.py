import os
import tkinter as tk
from tkinter import Scrollbar, messagebox

import business_logic
import data_handler

YELLOW_BG = "#ec9109"


def create_frame_export(root, global_config):
    """
    Frame modalità EXPORT.

    In questa scheda puoi:
      - vedere la directory di output (00_MixOutput) a partire dalla directory selezionata
      - creare i PDF individuali per ogni *_mix.txt (Crea PDF multipli)
      - creare il PDF unico pronto per PdfMegaMerge / stampa fronte-retro
      - vedere l'elenco dei file presenti in 00_MixOutput
      - consultare il log degli eventi

    Usa:
      - global_config["selected_directory"] : directory di lavoro base (locale)
    """
    frame = tk.Frame(root, bg=YELLOW_BG)

    # ======================================================================
    #  UTILITY LOCALI
    # ======================================================================
    def get_output_directory():
        """
        Restituisce il percorso completo alla directory 00_MixOutput
        sotto la directory selezionata corrente.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir:
            return ""
        return os.path.join(base_dir, "00_MixOutput")

    # ======================================================================
    #  RIGA 0: LABEL DIRECTORY DI OUTPUT
    # ======================================================================
    lbl_output_title = tk.Label(
        frame,
        text="Directory di output (00_MixOutput):",
        bg=YELLOW_BG,
    )
    lbl_output_title.grid(row=0, column=0, sticky="w", padx=8, pady=6)

    lbl_output_path = tk.Label(
        frame,
        text="(nessuna directory selezionata)",
        bg=YELLOW_BG,
        fg="blue",
        cursor="hand2",
        anchor="w",
    )
    lbl_output_path.grid(row=0, column=1, columnspan=2, sticky="ew", padx=8, pady=6)

    def open_output_dir(event=None):
        """
        Apre la directory di output nel file manager di sistema.
        """
        out_dir = get_output_directory()
        if not out_dir or not os.path.exists(out_dir):
            messagebox.showwarning(
                "Attenzione",
                "La directory di output 00_MixOutput non esiste ancora.\n"
                "Esegui prima il MIX dalla scheda Correzione.",
            )
            return
        data_handler.open_selected_directory(out_dir)

    lbl_output_path.bind("<Button-1>", open_output_dir)

    # ======================================================================
    #  RIGA 1: PULSANTI PDF
    # ======================================================================
    def do_create_pdfs():
        """
        Crea i PDF individuali a partire dai file *_mix.txt.
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir:
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima una directory di lavoro (Preparazione/Correzione).",
            )
            return

        business_logic.create_individual_pdfs(base_dir, log_text)
        update_file_list()

    def do_megamerge():
        """
        Crea il PDF unico finale con blocchi a pagine pari (Pronto per PdfMegaMerge).
        """
        base_dir = global_config["selected_directory"].get().strip()
        if not base_dir:
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima una directory di lavoro (Preparazione/Correzione).",
            )
            return

        business_logic.merge_all_files(base_dir, log_text)
        update_file_list()

    btn_create_pdfs = tk.Button(
        frame,
        text="Crea PDF multipli",
        command=do_create_pdfs,
        bg="white",
    )
    btn_create_pdfs.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

    btn_megamerge = tk.Button(
        frame,
        text="Per PdfMegaMerge",
        command=do_megamerge,
        bg="white",
    )
    btn_megamerge.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

    btn_refresh_list = tk.Button(
        frame,
        text="Aggiorna elenco",
        command=lambda: update_file_list(),
        bg="white",
    )
    btn_refresh_list.grid(row=1, column=2, sticky="ew", padx=8, pady=4)

    # ======================================================================
    #  RIGA 2-3: TEXT AREA ELENCO FILE OUTPUT
    # ======================================================================
    lbl_files = tk.Label(
        frame,
        text="File presenti in 00_MixOutput:",
        bg=YELLOW_BG,
    )
    lbl_files.grid(row=2, column=0, sticky="nw", padx=8, pady=4)

    file_list_text = tk.Text(
        frame,
        width=80,
        height=10,
        bg="#fffbe6",
    )
    file_list_text.grid(
        row=3,
        column=0,
        columnspan=3,
        sticky="nsew",
        padx=8,
        pady=4,
    )

    scrollbar_files = Scrollbar(
        frame,
        orient="vertical",
        command=file_list_text.yview,
    )
    scrollbar_files.grid(row=3, column=3, sticky="ns", pady=4)
    file_list_text.config(yscrollcommand=scrollbar_files.set)

    # ======================================================================
    #  RIGA 4-5: LOG / REPORT EVENTI
    # ======================================================================
    lbl_log = tk.Label(frame, text="Log / Report:", bg=YELLOW_BG)
    lbl_log.grid(row=4, column=0, sticky="nw", padx=8, pady=4)

    log_text = tk.Text(
        frame,
        width=80,
        height=10,
        bg="#fffdf0",
    )
    log_text.grid(
        row=5,
        column=0,
        columnspan=3,
        sticky="nsew",
        padx=8,
        pady=4,
    )

    scrollbar_log = Scrollbar(
        frame,
        orient="vertical",
        command=log_text.yview,
    )
    scrollbar_log.grid(row=5, column=3, sticky="ns", pady=4)
    log_text.config(yscrollcommand=scrollbar_log.set)

    # ======================================================================
    #  LAYOUT RESPONSIVE
    # ======================================================================
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(3, weight=1)
    frame.rowconfigure(5, weight=1)

    # ======================================================================
    #  FUNZIONE DI AGGIORNAMENTO ELENCO FILE
    # ======================================================================
    def update_file_list(*_args):
        """
        Aggiorna la textarea con la lista dei file presenti in 00_MixOutput.
        """
        output_dir = get_output_directory()
        file_list_text.delete("1.0", "end")

        if not output_dir:
            file_list_text.insert(
                "end",
                "Nessuna directory di lavoro selezionata.\n"
                "Imposta prima la directory in Preparazione o Correzione.\n",
            )
            return

        lbl_output_path.config(text=output_dir)

        if not os.path.exists(output_dir):
            file_list_text.insert(
                "end",
                f"La directory di output non esiste ancora:\n{output_dir}\n"
                "Esegui prima la fase di MIX dalla scheda Correzione.\n",
            )
            return

        try:
            files = sorted(os.listdir(output_dir))
        except Exception as e:
            file_list_text.insert(
                "end",
                f"Errore nella lettura di {output_dir}:\n{e}\n",
            )
            return

        if not files:
            file_list_text.insert(
                "end",
                f"Nessun file trovato in:\n{output_dir}\n",
            )
            return

        file_list_text.insert(
            "end",
            f"File presenti in {output_dir}:\n\n",
        )
        for f in files:
            file_list_text.insert("end", f" - {f}\n")

    # ======================================================================
    #  AGGIORNA QUANDO CAMBIA LA DIRECTORY SELEZIONATA
    # ======================================================================
    sel_dir_var = global_config.get("selected_directory")

    if sel_dir_var is not None and hasattr(sel_dir_var, "trace_add"):
        sel_dir_var.trace_add("write", lambda *args: update_file_list())
    elif sel_dir_var is not None and hasattr(sel_dir_var, "trace"):
        # compatibilità con versioni più vecchie di Tk
        sel_dir_var.trace("w", lambda *args: update_file_list())

    # Messaggio iniziale nel log
    log_text.insert(
        "end",
        "Modalità Export pronta.\n"
        "- Assicurati di aver eseguito il MIX nella scheda Correzione (file *_mix.txt).\n"
        "- 'Crea PDF multipli' genera un PDF per ogni file *_mix.txt.\n"
        "- 'Per PdfMegaMerge' crea un unico PDF finale:\n"
        "   • usa i PDF individuali\n"
        "   • verifica il numero di pagine di ogni elaborato\n"
        "   • se dispari, aggiunge automaticamente una pagina bianca\n"
        "     in modo che ogni elaborato abbia un numero PARI di pagine\n"
        "     (utile per la stampa fronte/retro e PdfMegaMerge).\n"
        "- L'elenco in alto ti mostra sempre cosa c'è in 00_MixOutput.\n",
    )
    log_text.see("end")

    # Aggiorna subito la label e l'elenco in base alla directory corrente
    update_file_list()

    # Registriamo il callback di refresh per il pulsante globale in header
    global_config["refresh_export"] = update_file_list

    return frame


