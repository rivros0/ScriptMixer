import tkinter as tk
from tkinter import messagebox

# Import dei frame
from frames.frame_live import create_frame_live
from frames.frame_raccolta import create_frame_raccolta
from frames.frame_correzione import create_frame_correzione

# Finestra principale
root = tk.Tk()
root.title("Applicazione Multimodale")
root.geometry("1280x800")

# Variabile per la modalità corrente (ora creata dopo root)
current_mode = tk.StringVar(value="Correzione")

# Funzione per cambiare modalità
def set_mode(mode):
    current_mode.set(mode)
    for f in (frame_live, frame_raccolta, frame_correzione):
        f.pack_forget()
    if mode == "Live":
        frame_live.pack(fill="both", expand=True)
    elif mode == "Raccolta":
        frame_raccolta.pack(fill="both", expand=True)
    elif mode == "Correzione":
        frame_correzione.pack(fill="both", expand=True)

# Menù principale
menubar = tk.Menu(root)

# Menù File
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Esci", command=root.destroy)
menubar.add_cascade(label="File", menu=file_menu)

# Menù Modalità
mode_menu = tk.Menu(menubar, tearoff=0)
mode_menu.add_radiobutton(label="Live", variable=current_mode, value="Live", command=lambda: set_mode("Live"))
mode_menu.add_radiobutton(label="Raccolta", variable=current_mode, value="Raccolta", command=lambda: set_mode("Raccolta"))
mode_menu.add_radiobutton(label="Correzione", variable=current_mode, value="Correzione", command=lambda: set_mode("Correzione"))
menubar.add_cascade(label="Modalità", menu=mode_menu)

root.config(menu=menubar)

# Creazione dei frame
frame_live = create_frame_live(root)
frame_raccolta = create_frame_raccolta(root)
frame_correzione = create_frame_correzione(root)

# Mostra inizialmente la modalità Correzione
set_mode("Correzione")

# Avvia il mainloop
root.mainloop()
