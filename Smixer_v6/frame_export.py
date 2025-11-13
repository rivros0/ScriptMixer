import os
import tkinter as tk
from tkinter import Scrollbar, messagebox

import business_logic
import data_handler

YELLOW_BG = "#ec9109"


def create_frame_export(root, global_config):
    """
    Frame modalità EXPORT.

    Funzioni principali:
      - mostra la directory di output 00_MixOutput della verifica corrente
      - elenca i file presenti in 00_MixOutput **escludendo** quelli che iniziano con '00'
      - crea i PDF individuali (solo dai *_mix.txt che NON iniziano con '00')
      - crea il PDF unico finale (MEGAmerge) escludendo i PDF che iniziano con '00'
      - logga le operazioni eseguite

    Non modifichiamo il layout esistente.
    """
    frame = tk.Frame(root, bg=YELLOW_BG)

    # ----------------------------------------------------------------------
    # UTILITY LOCALI
    # ----------------------------------------------------------------------
    def _get_base_dir():
        try:
            base = global_config["selected_directory"].get().strip()
        except Exception:
            base = ""
        return base

    def _get_mix_output_dir():
        base_dir = _get_base_dir()
        if not base_dir:
            return ""
        return os.path.join(base_dir, "00_MixOutput")

    # ----------------------------------------------------------------------
    # RIGA 0: LABEL DIRECTORY DI OUTPUT
    # ----------------------------------------------------------------------
    lbl_output_title = tk.Label(frame, text="Directory di output (00_MixOutput):", bg=YELLOW_BG)
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
        out_dir = _get_mix_output_dir()
        if not out_dir or not os.path.exists(out_dir):
            messagebox.showwarning(
                "Attenzione",
                "La directory 00_MixOutput non esiste.\nEsegui prima il MIX in 'Correzione'.",
            )
            return
        data_handler.open_selected_directory(out_dir)

    lbl_output_path.bind("<Button-1>", open_output_dir)

    # ----------------------------------------------------------------------
    # RIGA 1: PULSANTI PDF
    # ----------------------------------------------------------------------
    def do_create_pdfs():
        base_dir = _get_base_dir()
        if not base_dir:
            messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
            return
        # business_logic già filtra i file '00*' (patch sotto)
        business_logic.create_individual_pdfs(base_dir, log_text)
        update_file_list()

    def do_megamerge():
        base_dir = _get_base_dir()
        if not base_dir:
            messagebox.showwarning("Attenzione", "Seleziona prima una directory di lavoro.")
            return
        # business_logic già filtra i pdf '00*' (patch sotto)
        business_logic.merge_all_files(base_dir, log_text)
        update_file_list()

    btn_create_pdfs = tk.Button(frame, text="Crea PDF multipli", command=do_create_pdfs, bg="white")
    btn_create_pdfs.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

    btn_megamerge = tk.Button(frame, text="Per PdfMegaMerge", command=do_megamerge, bg="white")
    btn_megamerge.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

    btn_refresh_list = tk.Button(frame, text="Aggiorna elenco", command=lambda: update_file_list(), bg="white")
    btn_refresh_list.grid(row=1, column=2, sticky="ew", padx=8, pady=4)

    # ----------------------------------------------------------------------
    # RIGA 2-3: TEXT AREA ELENCO FILE (00_MixOutput)
    # ----------------------------------------------------------------------
    lbl_files = tk.Label(frame, text="File presenti in 00_MixOutput:", bg=YELLOW_BG)
    lbl_files.grid(row=2, column=0, sticky="nw", padx=8, pady=4)

    file_list_text = tk.Text(frame, width=80, height=10, bg="#fffbe6")
    file_list_text.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=8, pady=4)

    scrollbar_files = Scrollbar(frame, orient="vertical", command=file_list_text.yview)
    scrollbar_files.grid(row=3, column=3, sticky="ns", pady=4)
    file_list_text.config(yscrollcommand=scrollbar_files.set)

    # ----------------------------------------------------------------------
    # RIGA 4-5: LOG / REPORT
    # ----------------------------------------------------------------------
    lbl_log = tk.Label(frame, text="Log / Report:", bg=YELLOW_BG)
    lbl_log.grid(row=4, column=0, sticky="nw", padx=8, pady=4)

    log_text = tk.Text(frame, width=80, height=10, bg="#fffdf0")
    log_text.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=8, pady=4)

    scrollbar_log = Scrollbar(frame, orient="vertical", command=log_text.yview)
    scrollbar_log.grid(row=5, column=3, sticky="ns", pady=4)
    log_text.config(yscrollcommand=scrollbar_log.set)

    # ----------------------------------------------------------------------
    # LAYOUT RESPONSIVE
    # ----------------------------------------------------------------------
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(3, weight=1)
    frame.rowconfigure(5, weight=1)

    # ----------------------------------------------------------------------
    # AGGIORNA ELENCO (con filtro '00*')
    # ----------------------------------------------------------------------
    def update_file_list(*_args):
        """
        Aggiorna la lista dei file presenti in 00_MixOutput **escludendo**
        qualunque elemento che inizi con '00'.
        """
        output_dir = _get_mix_output_dir()
        file_list_text.delete("1.0", "end")

        if not output_dir:
            file_list_text.insert(
                "end",
                "Nessuna directory di lavoro selezionata.\n"
                "Imposta prima la directory in Preparazione o Correzione.\n",
            )
            lbl_output_path.config(text="(nessuna directory selezionata)")
            return

        lbl_output_path.config(text=output_dir)

        if not os.path.exists(output_dir):
            file_list_text.insert(
                "end",
                "La directory di output non esiste ancora:\n" + output_dir + "\n"
                "Esegui prima la fase di MIX dalla scheda Correzione.\n",
            )
            return

        try:
            all_names = sorted(os.listdir(output_dir))
        except Exception as e:
            file_list_text.insert("end", "Errore nella lettura di " + output_dir + ":\n" + str(e) + "\n")
            return

        # FILTRO: escludi tutto ciò che inizia con '00'
        names = []
        i = 0
        while i < len(all_names):
            nm = all_names[i]
            if not str(nm).startswith("00"):
                names.append(nm)
            i = i + 1

        if not names:
            file_list_text.insert("end", "Nessun file (filtrati gli elementi '00*') in:\n" + output_dir + "\n")
            return

        file_list_text.insert("end", "File presenti in " + output_dir + ":\n\n")
        j = 0
        while j < len(names):
            file_list_text.insert("end", " - " + names[j] + "\n")
            j = j + 1

    # ----------------------------------------------------------------------
    # REAZIONE AL CAMBIO DIRECTORY SELEZIONATA
    # ----------------------------------------------------------------------
    sel_dir_var = global_config.get("selected_directory")
    if sel_dir_var is not None and hasattr(sel_dir_var, "trace_add"):
        sel_dir_var.trace_add("write", lambda *_: update_file_list())
    elif sel_dir_var is not None and hasattr(sel_dir_var, "trace"):
        sel_dir_var.trace("w", lambda *_: update_file_list())

    # Messaggio iniziale nel log
    log_text.insert(
        "end",
        "Modalità Export pronta.\n"
        "- 'Crea PDF multipli' crea i PDF in 00_Pdf dai file *_mix.txt presenti in 00_MixOutput.\n"
        "- 'Per PdfMegaMerge' unisce i PDF di 00_Pdf in un unico file,\n"
        "  aggiungendo una pagina bianca dove necessario per blocchi a PAGINE PARI.\n"
        "- Nota: elementi che iniziano con '00' sono ignorati (sia in lista, sia in PDF e merge).\n",
    )
    log_text.see("end")

    # Avvio
    update_file_list()
    global_config["refresh_export"] = update_file_list

    return frame
