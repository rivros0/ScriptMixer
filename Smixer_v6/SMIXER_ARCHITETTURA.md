# SMX – Architettura e scelte progettuali

## 1. Obiettivi del progetto

Smixer è uno strumento per:

1. **Monitorare in tempo reale** le cartelle di consegna dei compiti (modalità *Live*).
2. **Raccogliere e copiare** in locale le cartelle dei test degli studenti (modalità *Raccolta*).
3. **Supportare la correzione**:

   * mix dei file degli studenti,
   * merge in PDF,
   * analisi delle somiglianze tra elaborati (modalità *Correzione*).

**Vincolo fondamentale:**
tutte le operazioni “sensibili” devono agire *solo* sulle cartelle `test01` … `test30`.
Risulta molto importante permettere all'utente di poter inserire del testo prima o dopo il tag "test01". prossimamente le  cartelle riceveranno un prefisso o un suffisso a seconda del laboratorio che viene utilizzato.
Utilizziamo un array nel quale insieriamo eventuali stringhe da utilizzare allo scopo.
Un menù di selezione a tendina nel posto appropriato sarà ben accetto.
Anche questa informazione dovrà essere inserita nel file di configurazione salvabile.

---

## 2. Principi di progettazione

1. **Semplicità prima di tutto**

   * Pochi moduli, ognuno con responsabilità chiare.
   * Evitare astrazioni troppo complesse o premature.

2. **Separazione fra GUI e logica**

   * I file dei frame (`frame_live`, `frame_raccolta`, `frame_correzione`) contengono solo interfaccia grafica e collegamenti ai bottoni.
   * I moduli di logica (`data_handler`, `business_logic`, `similarity`, `utils`) contengono il “lavoro sporco” (filesystem, PDF, analisi, ecc.).

3. **Configurazione centralizzata**

   * Le impostazioni globali (directory remota, estensione file, nome verifica, ecc.) sono conservate in un dizionario `global_config` di `tk.*Var` in `main.py`.
   * `main.py` si occupa di salvare/caricare questa configurazione in JSON.

4. **Niente side-effect nascosti**

   * Le funzioni che modificano file/cartelle devono:

     * lavorare **solo** sulle directory passate come parametro,
     * scrivere sempre un messaggio di log in un `Text` (o restituire un valore chiaro).

5. **Chiarezza sui percorsi**

   * `remote_directory`: dove si trovano le cartelle `test01`…`test30` sul server.
   * `local_base_directory`: dove vengono copiate e riorganizzate le cartelle in locale (per raccolta/correzione).

---

## 3. Struttura dei file / moduli

Struttura prevista della repo (semplificata):

* `main.py`
* `utils.py`
* `data_handler.py`
* `business_logic.py`
* `similarity.py`
* `frame_live.py`
* `frame_preparazione.py`
* `frame_correzione.py`
* `frame_export.py`
* `frame_domini.py`

Tutto in root. 

---

## 4. Ruolo di ogni modulo

### 4.0 Barra superiore comune

La barra superiore è creata in `main.py` ed è **comune a tutte le modalità** (Preparazione, Live, Correzione, Export). Non è ridisegnata dentro ogni frame.

Contiene:

* `Label` **"Nome verifica:"** e una `Entry` associata a `global_config["verifica_name"]` (StringVar) per inserire un identificativo della verifica (es. nome prova, classe, data).
* `Label` **"Directory selezionata:"** e una `Label` cliccabile con `textvariable=global_config["selected_directory"]`.

  * Se il valore è `"nessuna"` o vuoto, al click viene aperto un `filedialog.askdirectory` e la scelta viene salvata in `global_config["selected_directory"]`.
  * Se contiene un percorso valido, al click viene chiamata `data_handler.open_selected_directory(path)` che apre la directory nel file manager di sistema.
* Sfondo grigio chiaro (`bg="#eeeeee"`).

Questa barra rimane in alto e viene usata come **punto unico** per vedere e cambiare la directory di lavoro corrente.

### 4.1 `main.py`

Responsabilità:

* Creare la finestra principale Tkinter (`root = tk.Tk()`), titolo e dimensioni.
* Definire `global_config`:

  * `remote_directory` (StringVar)
  * `file_extension` (StringVar, es. `.cpp`)
  * `verifica_name` (StringVar)
  * `selected_directory` (StringVar, inizialmente `"nessuna"`)
  * `current_mode` (StringVar) – modalità corrente ("Preparazione", "Live", "Correzione", "Export").
* Creare e mantenere i 4 frame principali all'interno di `content_frame`:

  * `frame_preparazione = create_frame_preparazione(content_frame, global_config)`
  * `frame_live = create_frame_live(content_frame, global_config)`
  * `frame_correzione = create_frame_correzione(content_frame, global_config)`
  * `frame_export = create_frame_export(content_frame, global_config)`
* Gestire lo **switch di modalità** tramite **menù a tendina nella menubar**:

  * menù `Modalità` con 4 `add_radiobutton` collegati a `current_mode`.
  * la funzione `set_mode(mode: str)` nasconde tutti i frame (`pack_forget()`) e mostra solo quello selezionato (`pack(fill="both", expand=True)`).
* Creare la **barra superiore comune** (vedi 4.0) con:

  * label "Nome verifica:" + entry `global_config["verifica_name"]`;
  * label "Directory selezionata:" + label cliccabile su `global_config["selected_directory"]`.
* Implementare:

  * `salva_configurazione()` → salva su file JSON i valori di `remote_directory`, `file_extension`, `verifica_name`, `selected_directory`, `current_mode`.
  * `carica_configurazione()` → carica da JSON gli stessi valori e richiama `set_mode`.

**Nota progettuale:**
`main.py` non contiene logica di business (niente os.walk, niente PDF, niente analisi): si occupa solo di **GUI generale**, configurazione e orchestrazione dei frame.

### 4.2 `utils.py`

Funzioni di supporto generiche, *indipendenti* dal dominio “test01…test30”, ma che in alcuni casi riusano `data_handler._iter_test_folders`.

Funzioni principali:

* `update_directory_listing(directory: str, entry_extension, report_text)`

  * Popola la text-area di report con l'elenco dei file trovati nella directory (ricorsiva), filtrando per estensione.
  * `entry_extension` può essere una `Entry`/`StringVar` o una stringa.

* `count_directory_content(directory: str, entry_extension)`

  * Conta quante sottocartelle, quanti file totali, quanti file con una certa estensione e restituisce anche la lista dei file filtrati.

* `check_directory_content(base_directory: str, subdir: str, tree, entry_extension)`

  * Calcola le statistiche sulla sottocartella `subdir` e inserisce una riga nella Treeview della scheda Correzione.

* `update_subdirectories_list(selected_directory: str, tree, entry_extension)`

  * Elenca le sottodirectory immediate, le ordina alfabeticamente e per ciascuna chiama `check_directory_content(...)`.

* `scan_remote_directory(remote_directory: str, extension: str, count_lines: bool=False)`

  * Usata dalla scheda **Live**.
  * Scansiona solo le cartelle `test01`…`test30` presenti in `remote_directory` (usando `data_handler._iter_test_folders`).
  * Restituisce una lista di tuple con: nome cartella, numero di file trovati, eventuale numero di righe totali, elenco file, ultima modifica (stringa).

* `copy_test_directories(remote_directory: str, destination_root: str, nome_verifica: str)`

  * Usata dalla scheda **Live**.
  * Crea una nuova cartella in `destination_root` con nome timestampato (ed eventualmente con suffisso basato su `nome_verifica`).
  * Copia al suo interno solo le cartelle `test01`…`test30` esistenti.
  * Restituisce una stringa di esito da mostrare in etichetta.

---

### 4.3 `data_handler.py`

Responsabile delle **operazioni sulle cartelle dei test** (dominio “compiti”) e dell'apertura directory nel file manager.

Funzioni principali:

* `_iter_test_folders(base_directory)`

  * Generatore interno che produce le coppie `(folder_name, folder_path)` per `test01`…`test30`.

* `_sanitize_verifica_name(nome: str) -> str`

  * Ripulisce il nome verifica per usarlo nei nomi di cartella: trim, sostituzione spazi con underscore, rimozione caratteri non alfanumerici/`_`/`-`.

* `scan_test_folders(remote_directory, report_text)`

  * Scansiona le cartelle `test01`…`test30` in `remote_directory`.
  * Scrive nel `report_text` quali cartelle sono presenti o mancanti.
  * Per ogni file trovato mostra anche la data di creazione (UTC).

* `_copy_test_folders(remote_directory, target_root, report_text=None)`

  * Copia le cartelle `test01`…`test30` esistenti da `remote_directory` dentro `target_root`.
  * Usata internamente da `create_local_copy`.

* `create_local_copy(remote_directory, report_text, lbl_directory, update_directory_listing_func, update_subdirectories_list_func, nome_verifica=None)`

  * Crea una copia locale delle cartelle `test01`…`test30` sul **Desktop** in una nuova cartella chiamata:

    * `YYYYMMDD_HH-MM` oppure
    * `YYYYMMDD_HH-MM_<nome_verifica_sanitizzato>`.
  * Scrive un riepilogo dettagliato nel `report_text` (cartelle copiate o eventuale assenza di cartelle test).
  * Aggiorna `lbl_directory` (es. testo "Directory selezionata: <percorso>").
  * Chiama le funzioni `update_directory_listing_func` e `update_subdirectories_list_func` se fornite.
  * Restituisce il percorso della nuova directory creata.

* `clear_test_folders(selected_directory, report_text)`

  * Cancella **ricorsivamente** TUTTI i file e sottocartelle contenuti in `test01`…`test30` sotto `selected_directory`, senza toccare altre cartelle.
  * Prima di procedere mostra una tripla conferma "paranoica".

* `choose_directory(lbl_directory, update_directory_listing_func, update_subdirectories_list_func)`

  * Apre un `filedialog.askdirectory()` e, se l'utente sceglie una cartella:

    * aggiorna `lbl_directory` con il path selezionato,
    * chiama `update_directory_listing_func` e `update_subdirectories_list_func`.

* `open_selected_directory(selected_directory)`

  * Accetta una stringa, una `Label` o una `StringVar`.
  * Risolve il path e lo apre nel file manager (Explorer/Finder/xdg-open).
  * Se il path non è valido, mostra un warning.

---

### 4.4 `business_logic.py`

Responsabile della **logica di mix** e della **creazione dei PDF** a partire dai file `_mix.txt`.

Funzioni principali:

* `wrap_preserve_indent(text: str, width: int) -> str`

  * Esegue il wrapping del testo riga per riga preservando l'indentazione iniziale.

* `_resolve_base_directory(directory_source) -> str`

  * Accetta una stringa di path oppure un widget Tk (tipicamente una `Label` con testo "Directory selezionata: ...").
  * Restituisce sempre il path base pulito.

* `_get_mix_output_directory(base_directory: str) -> str`

  * Restituisce il percorso alla directory `00_MixOutput` sotto la directory base.

* `_ensure_mix_directory_exists(output_directory: str) -> bool`

  * Verifica l'esistenza di `00_MixOutput`. Se non esiste, mostra un warning e restituisce `False`.

#### Fase di MIX: creazione file `_mix.txt`

* `mix_files(lbl_directory, entry_prompt, entry_extension, tree, report_text, include_prompt: bool, include_subdir: bool)`

  * È la funzione chiamata direttamente dalla scheda **Correzione**.
  * Legge il path base da `lbl_directory` (che contiene la directory selezionata).
  * Legge il testo di introduzione da `entry_prompt` (Text) e l'estensione da `entry_extension`.
  * Per ogni riga della `tree` (sottodirectory `test01`, `test02`, ...) chiama `create_mix_file(...)`.
  * Scrive nel `report_text` l'esito del mix per ogni sottocartella.

* `create_mix_file(base_directory: str, subdir: str, prompt_string: str, extension: str, output_directory: str, include_prompt: bool, include_subdir: bool) -> str`

  * Crea il file di mix per una specifica sottocartella (es. `test01`).
  * Cerca ricorsivamente tutti i file con l'estensione indicata.
  * Struttura dei file `_mix.txt` generati:

    * eventuale prompt iniziale (se `include_prompt` è True);
    * eventuale riga con il nome della subdirectory (se `include_subdir` è True);
    * per ciascun file sorgente trovato:

      * una riga di separazione `###############################################################`;
      * il nome del file e il contenuto.

#### Fase di EXPORT: PDF multipli e MEGAmerge

* `create_individual_pdfs(directory_source, report_text)`

  * Usa `_resolve_base_directory` per ottenere la directory base.
  * Lavora sulla sottocartella `00_MixOutput` della directory base.
  * Per ciascun file `*_mix.txt` crea un PDF con lo stesso nome base (es. `test01_mix.txt` → `test01_mix.pdf`).
  * Usa `reportlab` con font monospazio e wrapping controllato (via `wrap_preserve_indent`) per mantenere leggibilità del codice.
  * Scrive nel `report_text` l'elenco dei PDF creati e un riepilogo finale.

* `merge_all_files(directory_source, report_text)`

  * Genera un unico PDF finale pensato per l'uso con **PdfMegaMerge** / stampa fronte-retro.
  * Usa i PDF individuali presenti in `00_MixOutput`:

    * Se non trova PDF, prova prima a crearli chiamando `create_individual_pdfs`.
  * Per ogni PDF:

    * aggiunge tutte le pagine al writer;
    * se il numero di pagine è dispari, aggiunge una **pagina bianca di riempimento** in modo che ogni elaborato abbia un numero **pari** di pagine.
  * Scrive il risultato finale in `00_MixOutput/00_MEGAmerged_output_final.pdf`.
  * Logga nel `report_text` il numero di pagine per ciascun elaborato e il percorso del PDF finale.

**Workflow per la creazione dei PDF**

1. In Correzione, l'utente seleziona la directory di lavoro (con le sottocartelle `testXX`).
2. Premendo **"Mixa"**, `business_logic.mix_files` genera per ogni sottocartella un file `testXX_mix.txt` in `00_MixOutput`.
3. Passando alla scheda **Export**, l'utente vede l'elenco dei file presenti in `00_MixOutput`.
4. Premendo **"Crea PDF multipli"** viene chiamata `create_individual_pdfs`.
5. Premendo **"Per PdfMegaMerge"** viene chiamata `merge_all_files`, che produce il PDF unico con pagine pari.
6. Tutte le operazioni scrivono un riepilogo nel log della scheda Export.

---

### 4.5 `similarity.py`

Responsabile dell’**analisi delle somiglianze** tra elaborati.

Funzioni principali:

* `_resolve_directory_source(directory_source) -> str`

  * Accetta una stringa di path, una `Label` o una `StringVar`.
  * Restituisce il path pulito alla directory base.

* `calculate_similarity(file1_path: str, file2_path: str) -> (difflib.SequenceMatcher, float)`

  * Calcola la similarità (%) tra due file testo usando `difflib.SequenceMatcher`.
  * Restituisce il matcher e un valore percentuale 0–100.

* `show_similar_fragments(file1, file2, matcher)`

  * Apre una nuova finestra con due colonne di testo affiancate.
  * Mostra i contenuti dei due file (dopo l’eventuale marker di separazione `###############################################################`).
  * Allinea le righe per facilitare il confronto visivo.

* `plot_similarity_matrix(output_directory, report_text=None)`

  * Cerca i file `*_mix.txt` in `output_directory` (tipicamente `00_MixOutput`).
  * Costruisce una matrice NxN di similarità e la visualizza come heatmap (matplotlib + seaborn).
  * Cliccando su una cella non diagonale apre `show_similar_fragments` sui due file corrispondenti.
  * Restituisce `(files, similarity_matrix)`.

* `analyze_similarities(directory_source, report_text)`

  * Funzione chiamata dalla GUI (scheda Correzione).
  * Risolve la directory base da `directory_source` (spesso la label con "Directory selezionata: ...").
  * Usa la sottocartella `00_MixOutput` e analizza i file `*_mix.txt` con `plot_similarity_matrix`.
  * Scrive nel `report_text` eventuali messaggi (es. "servono almeno 2 file").

---

### 4.6 `frame_live.py`

Responsabile della **modalità Live**.

Firma:

```python
def create_frame_live(root, global_config):
    ...
    return frame
```

Funzionalità (sfondo bianco):

* **Directory remota**

  * `Entry` collegata a `global_config["remote_directory"]`.

* **Estensione/i**

  * `Entry` collegata a `global_config["file_extension"]`.
  * L’etichetta suggerisce l’uso di più estensioni, ma attualmente il filtro è pensato per una singola estensione (stringa).

* **Opzioni**

  * Checkbox "Conta righe" → abilita il conteggio delle righe totali dei file trovati.
  * Checkbox "Aggiornamento automatico" → abilita la scansione periodica.

* **Pulsanti**

  * `Scan` → chiama `utils.scan_remote_directory(...)` e aggiorna la tabella.
  * `Pulisci tabella` → svuota completamente la Treeview.
  * `Crea copia locale` → chiede una directory di destinazione e chiama `utils.copy_test_directories(...)`; l’esito è mostrato in una label.

* **Tabella risultati (Treeview)**

  * Colonne:

    * `cartella`
    * `num_file`
    * `num_righe`
    * `elenco_file`
    * `ultima_modifica`
    * `tempo_trascorso`
  * Viene popolata sulla base dei risultati di `scan_remote_directory`.

* **Aggiornamento periodico**

  * Variabile `SCAN_INTERVAL = 30000` ms (30 secondi).
  * Se "Aggiornamento automatico" è attivo, viene usato `frame.after(SCAN_INTERVAL, aggiorna_tabella)` con gestione di `after_cancel` per evitare duplicazioni.

---

### 4.7 `frame_preparazione.py`

Responsabile della **modalità Preparazione** (viene usata prima di Correzione/Export per preparare il contesto di lavoro sulle cartelle test).

Firma:

```python
def create_frame_preparazione(root, global_config):
    ...
    return frame
```

Funzionalità (sfondo giallino `YELLOW_BG = "#fff5cc"`):

* **Riga 0 – Directory remota**

  * Label "Directory remota (contiene test01..test30):".
  * `Entry` collegata a `global_config["remote_directory"].`
  * Bottone "Scegli…" che apre un `filedialog.askdirectory` e aggiorna `remote_directory`.

* **Riga 1 – Pulsanti operativi**

  * `Scansiona cartelle test`

    * Recupera `remote_directory` da config.
    * Chiama `data_handler.scan_test_folders(remote_dir, report_text)` e mostra nel log quali cartelle test sono presenti/mancanti e i relativi file.
  * `Crea copia locale (Desktop)`

    * Chiama `data_handler.create_local_copy(...)` per creare sul Desktop una copia delle cartelle `test01`…`test30` in una cartella timestampata.
    * Aggiorna `global_config["selected_directory"]` con il nuovo percorso.
    * Aggiorna anche la label locale "Ultima directory locale creata" e scrive nel log che la directory è pronta per Correzione/Export.
  * `Cancella cartelle test remote`

    * Richiama `data_handler.clear_test_folders(remote_dir, report_text)`.
    * Cancella i contenuti delle cartelle `test01`…`test30` sulla directory remota, dopo tripla conferma.
  * `Apri directory remota`

    * Usa `data_handler.open_selected_directory(remote_dir)` per aprire la directory remota nel file manager.

* **Label stato copia locale**

  * "Ultima directory locale creata: (nessuna)" aggiornata dopo ogni copia locale riuscita.

* **Area log / report**

  * `Text` con scrollbar verticale dove vengono scritte tutte le operazioni (scansione, copia, cancellazione).
  * Messaggio iniziale che spiega il flusso consigliato: impostare directory remota, scansionare, creare copia locale, eventualmente cancellare le cartelle test sul server.

Questa modalità è il punto in cui il docente:

* controlla rapidamente lo stato delle cartelle `testXX` sul server;
* crea una copia locale organizzata per la correzione;
* può ripulire le cartelle test remote dopo essersi assicurato di avere la copia locale.

---

### 4.8 `frame_correzione.py`

Responsabile della **modalità Correzione**.

Firma:

```python
def create_frame_correzione(root, global_config):
    ...
    return frame
```

Funzionalità (sfondo bianco):

* **Intro / Prompt**

  * Label "INTRO:" e `Text` multi-linea per inserire un'introduzione da anteporre agli elaborati.
  * Checkbox "Includi Intro" (`include_prompt_var`).
  * Checkbox "Includi Nome (subdir)" (`include_subdir_var`).

* **Estensione dei file**

  * Label "Estensione dei file:".
  * `Entry` collegata a `global_config["file_extension"]`.

* **Directory di lavoro locale**

  * Label locale "Directory selezionata: (nessuna)" che riflette il valore di `global_config["selected_directory"]`.
  * Quando `selected_directory` cambia (da header o da "Scegli Directory"), la callback `on_selected_directory_change`:

    * aggiorna la label;
    * se la directory esiste, chiama `utils.update_directory_listing` per popolare il log con l'elenco file;
    * chiama `utils.update_subdirectories_list` per riempire la Treeview con le sottocartelle (tipicamente `testXX`).

* **Treeview sottodirectory**

  * Colonne:

    * `subdirectory`
    * `num_folders`
    * `num_files`
    * `num_extension_files`
    * `extension_files`
  * Mostra per ogni sottocartella le statistiche calcolate da `utils.check_directory_content`.

* **Log / Report**

  * Area `Text` con sfondo chiaro (`YELLOW_REPORT_BG`) e scrollbar verticale.
  * Utilizzata per loggare l’output del mix e dei controlli sulla directory.

* **Pulsanti principali**

  * `Scegli Directory`

    * Apre un `filedialog.askdirectory` e aggiorna `global_config["selected_directory"]`.
    * Il resto dell’aggiornamento (label, tabella, log) è gestito da `on_selected_directory_change`.
  * `Mixa`

    * Chiama `business_logic.mix_files(...)` passando `lbl_directory`, `entry_prompt`, `entry_extension`, la `tree`, il `report_text` e i flag `include_prompt_var`, `include_subdir_var`.
    * Genera i file `*_mix.txt` in `00_MixOutput`.
  * `Apri Directory Output`

    * Calcola `<selected_directory>/00_MixOutput` e la apre tramite `data_handler.open_selected_directory`.
  * `Analizza Similarità`

    * Chiama `similarity.analyze_similarities(lbl_directory, report_text)` per generare la matrice delle similarità e la vista affiancata dei file.

* **Messaggio iniziale**

  * La scheda mostra un testo guida che descrive i passi tipici (selezione directory, impostazione estensione/intro, mix, MEGAmerge/analisi).

Le operazioni di **export in PDF** vengono poi gestite dalla scheda `Export` (vedi 4.9).

### 4.9 `frame_export.py`

Responsabile della **modalità Export**, dedicata all'esportazione degli elaborati in PDF.

Firma:

```python
def create_frame_export(root, global_config):
    ...
    return frame
```

Layout e funzionalità (sfondo giallino `YELLOW_BG = "#fff5cc"`):

* **Riga 0 – Directory di output**

  * Label "Directory di output (00_MixOutput):".
  * Label cliccabile che mostra il percorso completo di `00_MixOutput` calcolato a partire da `global_config["selected_directory"]`.
  * Al click, se la directory esiste, viene aperta nel file manager tramite `data_handler.open_selected_directory`.

* **Riga 1 – Pulsanti PDF**

  * `Crea PDF multipli`

    * Chiama `business_logic.create_individual_pdfs(base_dir, log_text)` usando la directory selezionata.
    * Crea un PDF per ogni file `*_mix.txt` presente in `00_MixOutput`.
  * `Per PdfMegaMerge`

    * Chiama `business_logic.merge_all_files(base_dir, log_text)`.
    * Crea il PDF unico `00_MEGAmerged_output_final.pdf` con numero pari di pagine per ogni elaborato.
  * `Aggiorna elenco`

    * Chiama `update_file_list()` per ricaricare l’elenco dei file.

* **Riga 2–3 – Text area elenco file di output**

  * Label "File presenti in 00_MixOutput:".
  * `Text` con scrollbar verticale che mostra:

    * la lista dei file presenti in `00_MixOutput`;
    * eventuali messaggi se la directory non esiste o è vuota.

* **Riga 4–5 – Log eventi**

  * Label "Log / Report:".
  * `Text` dedicato al log delle operazioni di export (creazione PDF, errori, messaggi informativi).

* **Comportamento dinamico**

  * `update_file_list()` aggiorna sia il testo della label con il path di `00_MixOutput` sia la text area elenco.
  * È collegata via trace alla variabile `global_config["selected_directory"]`: quando cambia la directory selezionata, la lista viene aggiornata automaticamente.
  * All’avvio viene scritto un messaggio guida che spiega il flusso (mix in Correzione → PDF multipli → MEGAmerge).

Questa modalità è l'ultimo passo del flusso di lavoro: dopo aver preparato e corretto gli elaborati, il docente può generare i PDF singoli e il PDF unico finale, pronto per la stampa fronte-retro o per strumenti come PdfMegaMerge.

### 4.10 `frame_domini.py`

Responsabile della gestione dei **domìni** (insiemi di competenze/argomenti) associati alle verifiche.

Questa scheda non è direttamente coinvolta nel flusso Preparazione → Live → Correzione → Export, ma fornisce strumenti per definire e mantenere una lista strutturata di domini che possono essere utilizzati:

* nel testo di INTRO delle verifiche;
* nei nomi delle cartelle/sessioni;
* nei report esportati.

Firma:

```python
def create_frame_domini(root, global_config):
    ...
    return frame
```

Funzionalità (sfondo giallino, coerente con le altre schede di configurazione):

* **Riquadro elenco domini**

  * Lista (es. `Listbox` o `Treeview`) che mostra i domini attualmente definiti.
  * Ogni dominio può avere almeno:

    * un nome breve (es. "Arduino", "Array", "Ricorsione");
    * una descrizione opzionale.

* **Pulsanti di gestione**

  * `Aggiungi dominio`

    * Apre una finestra di dialogo in cui inserire nome e descrizione.
    * Aggiunge il nuovo dominio alla lista in memoria.
  * `Modifica dominio`

    * Permette di rinominare il dominio selezionato e/o modificarne la descrizione.
  * `Elimina dominio`

    * Rimuove il dominio selezionato (con conferma).

* **Persistenza su file**

  * I domini vengono salvati e caricati da un file di configurazione dedicato (es. `domini.json`) nella stessa directory del programma o in una sottocartella di configurazione.
  * All'avvio della scheda vengono caricati i domini esistenti.
  * Alla modifica (aggiunta/rimozione/modifica) viene aggiornato il file.

* **Integrazione con le altre schede**

  * La scheda Domini non modifica direttamente le cartelle `testXX` o i PDF, ma fornisce dati che altre schede possono usare, ad esempio:

    * la scheda Correzione può proporre un menù a tendina per inserire automaticamente nel prompt di INTRO i domini selezionati;
    * la scheda Preparazione può usare il dominio per costruire automaticamente il nome della copia locale (es. `YYYYMMDD_HH-MM_Array`).

Questa scheda è pensata per mantenere ordinata nel tempo la tassonomia delle verifiche, separando gli aspetti di **organizzazione didattica** (domini/argomenti) dalla gestione tecnica dei file e dei PDF. `frame_export.py`

Responsabile della **modalità Export**, dedicata all'esportazione degli elaborati in PDF.

Firma:

```python
def create_frame_export(root, global_config):
    ...
    return frame
```

Layout e funzionalità (sfondo giallino, es. `YELLOW_BG`):

* **Riga 1 – Header comune**

  * Condivide la stessa struttura descritta in 4.0 (Nome + Directory selezionata cliccabile).
  * La "Directory selezionata" in questo contesto punta di norma alla directory che contiene `00_MixOutput`.

* **Riga 2 – Directory di output**

  * `Label` "Directory di output".
  * `Label`/`Entry` che mostra `global_config["output_directory"]`.
  * Bottone "Scegli…" per modificare `output_directory` tramite `filedialog.askdirectory`.

* **Riga 3 – Pulsanti export**

  * Bottone **"Crea PDF multipli"**

    * Chiama `business_logic.export_multiple_pdfs(base_directory, output_directory, report_text)`.
    * Genera un PDF per ciascun file presente in `00_MixOutput`.
  * Bottone **"Per PdfMegaMerge"**

    * Chiama `business_logic.export_single_merged_pdf(base_directory, output_directory, report_text)`.
    * Genera un PDF unico contenente tutte le verifiche in sequenza.

* **Riga 4 – Lista file di output**

  * Una `Text` (o `ScrolledText`) che mostra l'elenco dei file presenti nella `output_directory`.
  * Viene aggiornata dopo ogni operazione di export per dare feedback immediato sui PDF generati.

* **Riga 5 – Log eventi**

  * Il consueto log testuale (es. `ScrolledText`) usato anche nelle altre frame.
  * Tutte le operazioni di export scrivono qui messaggi con timestamp (inizio/fine operazione, numero di file creati, eventuali errori).

Questa modalità è pensata come ultimo passo del flusso di lavoro: dopo aver preparato e corretto gli elaborati, il docente può generare i PDF da stampare o archiviare, inclusi i file adatti a essere gestiti da strumenti esterni come PdfMegaMerge.

---

## 5. Convenzioni sui nomi e sui percorsi

* Cartelle test: sempre `test01`, `test02`, …, `test30`.
* Cartelle di output:

  * `00_MixOutput` per i file mixati.
  * `00_PDF` (o simile) per gli output in PDF finali.
* Variabili Tkinter di configurazione in `global_config`:

  * `global_config["remote_directory"]`
  * `global_config["local_directory"]` (se usata)
  * `global_config["file_extension"]`
  * `global_config["verifica_name"]`
  * `global_config["auto_scan_enabled"]`
  * `global_config["count_lines_enabled"]`
  * ecc.

---

## 6. Error handling e logging

* Errori bloccanti (es. directory inesistente, permessi negati):

  * visualizzati con `messagebox.showerror`.
* Errori non bloccanti o messaggi informativi:

  * scritti nel `report_text` della modalità corrente.
* Operazioni lunghe:

  * scritta una riga iniziale “Operazione X avviata…”
  * e una finale “Operazione X completata.”

---

## 7. Evoluzioni future (facoltative)

* Aggiunta di filtri per tipo di file (es. solo `.cpp` o `.java`).
* Esportazione automatica di un file di log in `.txt` o `.csv`.
* Parametrizzazione del range di cartelle (`test01`…`testNN` non fisso a 30).
