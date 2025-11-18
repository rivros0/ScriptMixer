import tkinter as tk
from tkinter import ttk, messagebox

import similarity_ftp


def open_similarity_map(
    parent_frame,
    metrics_by_student_cache,
    texts_test_cache,
    merged_domain_texts_cache,
    students_in_test_cache,
    students_in_domain_cache,
):
    """
    Apre la finestra principale "Mappa similitudini (verifica ↔ MERGE dominio)"
    e gestisce anche l'apertura della finestra di comparazioni avanzate.

    I parametri sono i riferimenti alle strutture dati mantenute da frame_domini:
      - metrics_by_student_cache: dict {studente: metriche_globali}
      - texts_test_cache: dict {studente: testo_verifica}
      - merged_domain_texts_cache: dict {studente: testo_merged_dominio}
      - students_in_test_cache: list degli studenti presenti nei test
      - students_in_domain_cache: list degli studenti presenti nei domini
    """

    # ------------------------------------------------------------------
    # Finestra "comparazioni avanzate" (riuso della logica preesistente)
    # ------------------------------------------------------------------
    def apri_comparazioni_avanzate(alunno):
        """
        Finestra con tre elenchi:
          - Test ↔ Test
          - Test ↔ Domini
          - Dominio ↔ Domini
        con colorazione blu/arancio/rosso in funzione della similarità.
        """
        if len(students_in_test_cache) == 0 and len(students_in_domain_cache) == 0:
            messagebox.showwarning(
                "Attenzione",
                "Esegui prima l'analisi per generare i dati di confronto.",
            )
            return

        top = tk.Toplevel(parent_frame)
        top.title("Comparazioni avanzate per: " + str(alunno))

        nota = tk.Label(
            top,
            text=(
                "Valori in percentuale. Cromia: "
                "blu=bassa, arancio=media, rosso=alta similarità."
            ),
        )
        nota.grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=6)

        def crea_tv_con_colori(parent, titolo):
            group = tk.LabelFrame(parent, text=titolo)
            tv = ttk.Treeview(
                group,
                columns=("Confronto", "Similarità %"),
                show="headings",
                height=14,
            )

            tv.heading("Confronto", text="Confronto")
            tv.heading("Similarità %", text="Similarità %")

            tv.column("Confronto", width=280, anchor="w")
            tv.column("Similarità %", width=120, anchor="center")

            sb = ttk.Scrollbar(group, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=sb.set)

            tv.grid(row=0, column=0, sticky="nsew")
            sb.grid(row=0, column=1, sticky="ns")

            group.grid_rowconfigure(0, weight=1)
            group.grid_columnconfigure(0, weight=1)

            tv.tag_configure("low", foreground="blue")
            tv.tag_configure("mid", foreground="#cc7a00")
            tv.tag_configure("high", foreground="red")

            return group, tv

        grp_tvt, tv_tvt = crea_tv_con_colori(
            top,
            "Test ↔ Test ({} vs altri test)".format(alunno),
        )
        grp_tvt.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")

        grp_tvd, tv_tvd = crea_tv_con_colori(
            top,
            "Test ↔ Domini (test di {} vs merge domini)".format(alunno),
        )
        grp_tvd.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")

        grp_dvd, tv_dvd = crea_tv_con_colori(
            top,
            "Dominio ↔ Domini (merge dominio di {} vs merge domini)".format(alunno),
        )
        grp_dvd.grid(row=1, column=2, padx=8, pady=8, sticky="nsew")

        # -------------------------
        # Test ↔ Test
        # -------------------------
        if alunno in texts_test_cache:
            base_text = texts_test_cache.get(alunno, "")
            i = 0
            while i < len(students_in_test_cache):
                other = students_in_test_cache[i]
                t_other = texts_test_cache.get(other, "")

                val = similarity_ftp.calculate_text_similarity_percent(
                    base_text,
                    t_other,
                )

                tag = ""
                if val >= 80.0:
                    tag = "high"
                elif val >= 60.0:
                    tag = "mid"
                else:
                    if val <= 30.0:
                        tag = "low"

                tv_tvt.insert(
                    "",
                    "end",
                    values=(alunno + " ↔ " + other, "{:.1f}".format(val)),
                    tags=(tag,),
                )
                i = i + 1
        else:
            tv_tvt.insert("", "end", values=("Nessun test per " + alunno, "-"))

        # -------------------------
        # Test ↔ Domini
        # -------------------------
        if alunno in texts_test_cache:
            base_text = texts_test_cache.get(alunno, "")
            i = 0
            while i < len(students_in_domain_cache):
                other = students_in_domain_cache[i]
                d_other = merged_domain_texts_cache.get(other, "")

                val = similarity_ftp.calculate_text_similarity_percent(
                    base_text,
                    d_other,
                )

                tag = ""
                if val >= 80.0:
                    tag = "high"
                elif val >= 60.0:
                    tag = "mid"
                else:
                    if val <= 30.0:
                        tag = "low"

                tv_tvd.insert(
                    "",
                    "end",
                    values=(alunno + " (test) ↔ " + other + " (dom)", "{:.1f}".format(val)),
                    tags=(tag,),
                )
                i = i + 1
        else:
            tv_tvd.insert("", "end", values=("Nessun test per " + alunno, "-"))

        # -------------------------
        # Dominio ↔ Domini
        # -------------------------
        if alunno in merged_domain_texts_cache:
            base_dom = merged_domain_texts_cache.get(alunno, "")
            i = 0
            while i < len(students_in_domain_cache):
                other = students_in_domain_cache[i]
                d_other = merged_domain_texts_cache.get(other, "")

                val = similarity_ftp.calculate_text_similarity_percent(
                    base_dom,
                    d_other,
                )

                tag = ""
                if val >= 80.0:
                    tag = "high"
                elif val >= 60.0:
                    tag = "mid"
                else:
                    if val <= 30.0:
                        tag = "low"

                tv_dvd.insert(
                    "",
                    "end",
                    values=(alunno + " (dom) ↔ " + other + " (dom)", "{:.1f}".format(val)),
                    tags=(tag,),
                )
                i = i + 1
        else:
            tv_dvd.insert("", "end", values=("Nessun dominio per " + alunno, "-"))

        top.grid_rowconfigure(1, weight=1)
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=1)

    # ------------------------------------------------------------------
    # Finestra "mappa similitudini" (riepilogo globale per studente)
    # ------------------------------------------------------------------
    if len(metrics_by_student_cache) == 0:
        messagebox.showinfo(
            "Informazione",
            "Non ci sono risultati da visualizzare. Esegui prima l'analisi.",
        )
        return

    top_mappa = tk.Toplevel(parent_frame)
    top_mappa.title("Riepilogo similitudini (verifica ↔ MERGE dominio)")

    cols = (
        "Studente",
        "Simil. Test/Dominio (%)",
        "Righe riutilizzate",
        "Caratteri riutilizzati",
        "% char su test",
        "Righe test",
        "Caratteri test",
    )

    tv = ttk.Treeview(top_mappa, columns=cols, show="headings", height=20)

    i = 0
    while i < len(cols):
        c = cols[i]
        tv.heading(c, text=c)

        if c == "Studente":
            tv.column(c, width=200, anchor="w")
        else:
            tv.column(c, width=160, anchor="center")

        i = i + 1

    sb = ttk.Scrollbar(top_mappa, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)

    tv.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")

    tv.tag_configure("low", foreground="blue")
    tv.tag_configure("mid", foreground="#cc7a00")
    tv.tag_configure("high", foreground="red")

    nomi = sorted(list(metrics_by_student_cache.keys()))

    i = 0
    while i < len(nomi):
        nome = nomi[i]
        m = metrics_by_student_cache[nome]

        sim_globale = float(m.get("similarity_percent", 0.0))
        shared_lines = int(m.get("shared_lines_count", 0))
        shared_chars = int(m.get("shared_chars_len", 0))
        perc_shared_chars = float(m.get("percent_shared_chars_on_test", 0.0))
        total_lines_test = int(m.get("total_lines_test", 0))
        total_chars_test = int(m.get("total_chars_test", 0))

        tag = ""
        if sim_globale >= 80.0 or perc_shared_chars >= 80.0:
            tag = "high"
        elif sim_globale >= 60.0 or perc_shared_chars >= 60.0:
            tag = "mid"
        else:
            if sim_globale <= 30.0 and perc_shared_chars <= 30.0:
                tag = "low"

        values = (
            nome,
            "{:.1f}".format(sim_globale),
            str(shared_lines),
            str(shared_chars),
            "{:.1f}".format(perc_shared_chars),
            str(total_lines_test),
            str(total_chars_test),
        )

        tv.insert("", "end", values=values, tags=(tag,))
        i = i + 1

    def on_double_click(event):
        item_id = tv.identify_row(event.y)
        if item_id == "":
            return
        vals = tv.item(item_id, "values")
        if not vals:
            return
        selected = vals[0]
        apri_comparazioni_avanzate(selected)

    tv.bind("<Double-1>", on_double_click)

    legenda = tk.Label(
        top_mappa,
        text=(
            "Legenda: blu = bassa similarità, arancio = media, rosso = alta. "
            "Doppio clic su uno studente per aprire le comparazioni avanzate."
        ),
        justify="left",
        anchor="w",
    )
    legenda.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=6)

    top_mappa.grid_rowconfigure(0, weight=1)
    top_mappa.grid_columnconfigure(0, weight=1)
