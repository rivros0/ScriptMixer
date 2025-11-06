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
* `frame_raccolta.py`
* `frame_correzione.py`
* `frame_export.py`

Tutto in root. 

---

## 4. Ruolo di ogni modulo

### 4.0 Layout comune delle frame

Tutte le frame (`frame_raccolta`, `frame_live`, `frame_correzione`, `frame_export`) condividono una **prima riga standard** con:

* `Label` **"Nome"** e una `Entry` associata a `global_config["nome"]` (StringVar) per inserire un identificativo della sessione di lavoro (es. nome verifica, classe, data).
* `Label` **"Directory selezionata"** e una `Label` cliccabile che mostra `global_config["current_directory"]`.

  * Al click su questa label viene chiamata una funzione di utilità (es. `data_handler.open_selected_directory(...)`) che apre la directory nel file manager di sistema (Explorer/Finder o equivalente).
* Sfondo coerente con il tema del programma (per le frame di lavoro principale si utilizza un giallino chiaro condiviso, es. costante `YELLOW_BG`).

Questa riga è sempre visibile nella parte alta di ogni frame e viene aggiornata quando l'utente cambia directory di lavoro.

### 4.1 `main.py`

Responsabilità:

* Creare la finestra principale Tkinter.
* Definire `global_config`:

  * `remote_directory` (StringVar)
  * `local_directory` (StringVar) – se serve per la raccolta
  * `output_directory` (StringVar) – directory usata per l'export degli elaborati (PDF, ecc.)
  * `file_extension` (lista/Array di estensioni selezionabili)
  * `verifica_name` (StringVar)
  * `nome` (StringVar) – etichetta della sessione di lavoro/nomedocente
  * `current_directory` (StringVar) – directory attualmente selezionata e mostrata nell'header comune
  * eventuali flag (es. `auto_scan_enabled`, `count_lines_enabled`, ecc.).
* Creare e mantenere i 4 frame principali:

  * `frame_raccolta = create_frame_raccolta(root, global_config)`
  * `frame_live = create_frame_live(root, global_config)`
  * `frame_correzione = create_frame_correzione(root, global_config)`
  * `frame_export = create_frame_export(root, global_config)`
* Gestire lo **switch di modalità** tramite una `Combobox` (menu a tendina) anziché tramite menu classico:

  * la combobox elenca le modalità: "Preparazione", "Live", "Correzione", "Export";
  * al cambio di valore viene richiamata una funzione che nasconde tutte le frame e mostra solo quella selezionata.
* Implementare:

  * `salva_configurazione()`
  * `carica_configurazione()`

**Nota progettuale:**
`main.py` **non deve** contenere logica di business (niente os.walk, niente PDF, niente analisi). Solo collegamenti.

---

### 4.2 `utils.py`

Funzioni di supporto generiche, *indipendenti* dal dominio “test01…test30”.

Funzioni previste:

* `update_directory_listing(directory: str, entry_extension, report_text)`

  * Mostra nel `Text` tutti i file (eventualmente filtrati per estensione).

* `update_subdirectories_list(selected_directory: str, tree: ttk.Treeview, entry_extension)`

  * Popola un `Treeview` con le sottocartelle e magari con info di base (num file ecc.).

* `check_directory_content(directory: str, entry_extension)`

  * Restituisce info sul contenuto della directory: num cartelle, num file, num file con estensione specifica.

* `count_directory_content(directory: str, entry_extension)`

  * Come sopra, ma con eventuale restituzione di lista file, ecc.

Tutte queste funzioni:

* **Non** devono conoscere `test01`…`test30`.
* Possono essere riutilizzate in tutte le modalità.

---

### 4.3 `data_handler.py`

Responsabile delle **operazioni sulle cartelle dei test** (dominio “compiti”).

Funzioni previste:

* `scan_test_folders(remote_directory: str, report_text)`

  * Controlla `test01`…`test30` dentro `remote_directory`.
  * Per ogni cartella:

    * verifica l’esistenza,
    * opzionalmente conta file (e righe, se richiesto),
    * scrive un report.

* `create_local_copy(remote_directory: str, local_base_directory: str, report_text)`

  * Copia le cartelle `test01`…`test30` da `remote_directory` a `local_base_directory`.
  * Mantiene struttura completa (sottocartelle e file).

* `clear_test_folders(local_base_directory: str, report_text)`

  * Pulisce eventuali cartelle di output (`00_MixOutput`, `00_PDF`, ecc.) secondo regole che definiremo.

* `choose_directory(label_widget)`

  * Apre un `filedialog.askdirectory` e aggiorna il testo di una `Label`.

* `open_selected_directory(selected_directory: str)`

  * Apre la cartella nel file manager (Windows, macOS, Linux).

**Nota:**
`data_handler.py` può usare `messagebox` per errori gravi (es. directory inesistente), ma nella maggior parte dei casi scrive nei `report_text` passati dai frame.

---

### 4.4 `business_logic.py`

Responsabile della **logica di correzione ed export** sui file degli studenti.

Funzioni previste principali:

* `mix_files(base_directory: str, verifica_name: str, file_extensions: list[str], report_text)`

  * Cerca all’interno delle cartelle `test01`…`test30` (o in una directory scelta) i file di verifica con estensioni contenute in `file_extensions` (es. [".cpp", ".h"], [".java"], ecc.).
  * Per ogni cartella `testXX` crea un file di testo mixato nella cartella `00_MixOutput` sotto `base_directory`.
  * Ogni file mixato contiene, in ordine definito, i vari sorgenti pertinenti allo studente.

* `create_mix_file(...)`

  * Funzione interna di supporto a `mix_files`, non necessariamente esposta ai frame.

* `export_multiple_pdfs(base_directory: str, output_directory: str, report_text)`

  * Legge tutti i file di testo presenti in `00_MixOutput` sotto `base_directory`.
  * Per ciascun file testo genera **un PDF separato** nella `output_directory` (es. `00_PDF/`), usando `reportlab`.
  * Naming suggerito: `NN_CognomeNome.pdf` o, se non disponibile, `testXX_mix.pdf`.
  * Inserisce automaticamente titoli/pagine di separazione se richiesto.

* `export_single_merged_pdf(base_directory: str, output_directory: str, report_text)`

  * Legge tutti i file di testo in `00_MixOutput` (ordinati per numero di test o criterio configurato).
  * Crea **un unico PDF** contenente in sequenza tutte le verifiche, con eventuali interruzioni di pagina tra uno studente e l'altro.
  * Salva il file in `output_directory` con un nome ben definito (es. `MegaMerge_Verifica_<data>.pdf`).
  * Questo PDF è pensato per essere usato direttamente o come input per strumenti esterni (es. PdfMegaMerge).

* `merge_all_files(base_directory: str, output_directory: str, report_text)`

  * Funzione di alto livello che, in base a opzioni o parametri, può:

    * chiamare `export_multiple_pdfs` per creare un PDF per studente;
    * chiamare `export_single_merged_pdf` per creare il PDF unico con tutte le verifiche.

**Workflow per la creazione del PDF con tutte le verifiche**

1. L'utente lancia, dalla modalità di Correzione, il **mix** dei file sorgenti (uno per studente) usando `mix_files`.
2. Una volta verificata la correttezza dei file in `00_MixOutput`, l'utente passa alla modalità **Export**.
3. Nella modalità Export, seleziona la directory di lavoro (che contiene `00_MixOutput`) e la directory di output per i PDF.
4. Premendo il pulsante:

   * **"Crea PDF multipli"** → viene chiamata `export_multiple_pdfs`.
   * **"Per PdfMegaMerge"** → viene chiamata `export_single_merged_pdf` per ottenere un unico PDF con tutte le verifiche.
5. Tutte le operazioni di creazione PDF devono scrivere un riepilogo nel `report_text` (numero di file elaborati, percorsi dei PDF generati, eventuali errori).

**Obiettivo:**
Il frame di correzione e il frame di export, insieme, devono fungere da pannello di controllo avanzato sulla fase di correzione e stampa.
Devono permettere di:

* esplorare la struttura delle cartelle dei test (anche annidate) e visualizzare l'elenco dei file per singolo studente;
* ispezionare velocemente uno o più file (apertura con editor esterno o anteprima testuale);
* aprire la cartella selezionata nel file manager;
* avviare il mix automatico dei file di verifica → `business_logic.mix_files(...)`;
* esportare gli elaborati in **PDF multipli** (uno per studente) → `business_logic.export_multiple_pdfs(...)`;
* esportare un **PDF unico con tutte le verifiche** (pensato per PdfMegaMerge) → `business_logic.export_single_merged_pdf(...)`;
* lanciare l'analisi delle similarità e, a partire dalla matrice, aprire il confronto dettagliato tra due elaborati (finestra diff / evidenziazione frammenti simili).
* lanciare l'analisi delle similarità e, a partire dalla matrice, aprire il confronto dettagliato tra due elaborati (finestra diff / evidenziazione frammenti simili).

---

### 4.5 `similarity.py`

Responsabile dell’**analisi delle somiglianze** tra elaborati.

Funzioni previste:

* `calculate_similarity(file1_path: str, file2_path: str) -> (difflib.SequenceMatcher, float)`

  * Restituisce il matcher e la percentuale di similarità.

* `plot_similarity_matrix(base_directory: str)`

  * Cerca i file in `00_MixOutput` (o in una directory specificata).
  * Calcola matrice NxN di similarità.
  * Mostra una heatmap (matplotlib/seaborn).
  * Restituisce `(files_list, similarity_matrix)`.

* `show_similar_fragments(matcher, file1_path: str, file2_path: str)`

  * Apre una finestra Tkinter con due `Text` affiancati, mostrando le parti più simili.

* `analyze_similarities(lbl_directory, report_text)`

  * Funzione “bridge” pensata per essere chiamata direttamente dal frame:

    * legge la directory dalla label,
    * usa `plot_similarity_matrix`,
    * aggiorna il report.

---

### 4.6 `frames/frame_live.py`

Responsabile della **modalità Live**.

Firma:

```python
def create_frame_live(root, global_config):
    ...
    return frame
```

Funzionalità:

* Campo per `remote_directory` (legato a `global_config["remote_directory"]`).
* Campo per estensione file (legato a `global_config["file_extension"]`).
* Tabella (Treeview) che mostra, per `test01`…`test30`:

  * nome cartella,
  * numero di file trovati (eventualmente con estensione filtrata),
  * eventuale data/ora ultima modifica,
  * opzionalmente numero di righe complessive (se `global_config["count_lines_enabled"]` è attivo).
* Pulsanti:

  * “Scansiona ora” → chiama `scan_test_folders(...)` o una funzione analoga.
  * “Crea copia locale” → `create_local_copy(...)`.
  * “Pulisci tabella” → svuota il Treeview.

Gestione timer:

* Variabile `SCAN_INTERVAL` in ms (es. 30000).
* Checkbox per attivare/disattivare “scansione automatica”.
* Uso di `frame.after(SCAN_INTERVAL, funzione_scan)` per la scansione periodica.

---

### 4.7 `frame_raccolta.py`

Responsabile della **modalità Preparazione/Raccolta** (viene usata prima del Live per preparare il contesto di lavoro sulle cartelle test).

Firma:

```python
def create_frame_raccolta(root, global_config):
    ...
    return frame
```

Funzionalità effettive (derivate da `frame_preparazione.py` della repo v6):

* **Selettore directory base**

  * Campo di testo collegato a `global_config["remote_directory"]`.
  * Bottone "Scegli…" che apre un `filedialog.askdirectory` e aggiorna la directory base.

* **Pulsanti principali (riga 2)**

  * `Scan`

    * Avvia una scansione della directory base.
    * Usa `utils.scan_test_directories(path, extension="", root_prefix="test*")` per cercare **solo** cartelle `testXX`.
    * Popola la tabella riepilogativa con:

      * nome cartella,
      * numero di file,
      * elenco file trovati (lista compatta),
      * data/ora di ultima modifica.
  * `Crea copia locale`

    * Chiede una directory di destinazione.
    * Propone un nome predefinito (timestamp + `_preparazione`).
    * Crea la nuova cartella e vi copia **solo** le cartelle `test01`…`test30`, mantenendo struttura di sottocartelle e file.
    * Ogni eventuale errore di copia viene loggato e, se necessario, segnalato con `messagebox`.
  * `Distribuisci file`

    * Chiede all'utente un file da distribuire.
    * Copia tale file in tutte le cartelle `testXX` trovate da `utils.scan_test_directories`.
    * Aggiorna la tabella al termine della distribuzione.

* **Pulsante di pulizia cartelle test**

  * `Pulisci cartelle test`

    * Dopo doppia conferma tramite `messagebox.askyesno`, cancella **solo i contenuti interni** delle cartelle `test01`…`test30` presenti nella directory base.
    * Mantiene le cartelle, ma svuota file e sottocartelle.
    * Aggiorna la tabella a operazione completata.

* **Tabella (Treeview)**

  * Colonne previste:

    * `Cartella`
    * `N. File`
    * `File trovati`
    * `Ultima modifica`
  * Mostra una riga per ciascuna cartella `testXX` trovata nella directory base.

* **Area log in calce**

  * Una `ScrolledText` che riceve, tramite funzione locale `log(msg)`, i messaggi operativi con timestamp (scansioni, copie, distribuzioni, pulizie, eventuali errori).

La modalità Preparazione/Raccolta è quindi il punto in cui il docente:

* controlla rapidamente lo stato delle cartelle `testXX` sul server;
* crea uno snapshot locale completo e organizzato dei compiti da correggere;
* distribuisce materiali comuni (file di testo, tracce, template) nelle cartelle degli studenti;
* svuota in sicurezza le cartelle test tra una verifica e la successiva.

---

### 4.8 `frames/frame_correzione.py`

Responsabile della **modalità Correzione**.

Firma:

```python
def create_frame_correzione(root, global_config):
    ...
    return frame
```

Funzionalità:

* Selettore directory base per la correzione (di solito la directory locale dove sono stati copiati i test).

* Pulsanti principali:

  * “Aggiorna elenco cartelle / file” → usa `utils.update_subdirectories_list` e funzioni correlate per mostrare cartelle e file degli studenti.
  * “Mix dei file di verifica” → `business_logic.mix_files(...)`.
  * “Analisi similarità” → `similarity.analyze_similarities(...)`.
  * “Apri cartella” → `open_selected_directory(...)`.

* Area `Text` per il **report** delle operazioni (log di mix, analisi, errori, ecc.).

Le operazioni di **export in PDF** sono demandate alla modalità `Export` descritta nella sezione successiva.

### 4.9 `frame_export.py`

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
