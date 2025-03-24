import os
import difflib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tkinter import Toplevel, Text, Scrollbar
import tkinter as tk

def calculate_similarity(file1_path, file2_path):
    try:
        with open(file1_path, 'r', encoding="utf-8") as file1, open(file2_path, 'r', encoding="utf-8") as file2:
            content1 = file1.read().replace('\r\n', '\n').replace('\r', '\n')
            content2 = file2.read().replace('\r\n', '\n').replace('\r', '\n')
            matcher = difflib.SequenceMatcher(None, content1, content2)
            return matcher, matcher.ratio() * 100
    except Exception as e:
        return None, 0

def plot_similarity_matrix(output_directory):
    files = [os.path.join(output_directory, file) for file in os.listdir(output_directory) if file.endswith("_mix.txt")]
    num_files = len(files)
    similarity_matrix = np.zeros((num_files, num_files))
    matchers = [[None for _ in range(num_files)] for _ in range(num_files)]
    for i in range(num_files):
        for j in range(num_files):
            if i != j:
                matcher, similarity = calculate_similarity(files[i], files[j])
                similarity_matrix[i, j] = similarity
                matchers[i][j] = matcher
    def on_click(event):
        if event.inaxes is None:
            return
        x, y = int(event.xdata), int(event.ydata)
        if x != y and matchers[x][y]:
            show_similar_fragments(files[x], files[y], matchers[x][y])
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(similarity_matrix, annot=True, fmt=".0f", cmap="coolwarm", 
                xticklabels=[os.path.basename(f) for f in files],
                yticklabels=[os.path.basename(f) for f in files], ax=ax)
    plt.title("Matrice di Similarità tra i File di Output")
    plt.xlabel("File di Output")
    plt.ylabel("File di Output")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()
    return files, similarity_matrix

def show_similar_fragments(file1, file2, matcher):
    top = Toplevel()
    top.title(f"Somiglianze tra {os.path.basename(file1)} e {os.path.basename(file2)}")
    top.geometry("1024x768")
    top.resizable(True, True)
    frame1 = tk.Frame(top)
    frame1.grid(row=0, column=0, sticky="nsew")
    frame2 = tk.Frame(top)
    frame2.grid(row=0, column=1, sticky="nsew")
    text1 = Text(frame1, wrap="none", width=50, height=20)
    text1.pack(side="left", fill="both", expand=True)
    text2 = Text(frame2, wrap="none", width=50, height=20)
    text2.pack(side="left", fill="both", expand=True)
    scroll_y = Scrollbar(top, orient="vertical")
    scroll_y.grid(row=0, column=2, sticky="ns")
    text1.config(yscrollcommand=scroll_y.set)
    text2.config(yscrollcommand=scroll_y.set)
    def sync_scroll(*args):
        text1.yview(*args)
        text2.yview(*args)
    scroll_y.config(command=sync_scroll)
    try:
        content1_start = matcher.a.find("\n", matcher.a.find("###############################################################")) + 1
        content2_start = matcher.b.find("\n", matcher.b.find("###############################################################")) + 1
        content1 = matcher.a[content1_start:]
        content2 = matcher.b[content2_start:]
    except Exception:
        content1 = ""
        content2 = ""
    content1_lines = content1.splitlines()
    content2_lines = content2.splitlines()
    max_line_count = max(len(content1_lines), len(content2_lines))
    for i in range(len(content1_lines), max_line_count):
        content1_lines.append("")
    for i in range(len(content2_lines), max_line_count):
        content2_lines.append("")
    for line1, line2 in zip(content1_lines, content2_lines):
        text1.insert("end", line1 + "\n")
        text2.insert("end", line2 + "\n")
    top.grid_rowconfigure(0, weight=1)
    top.grid_columnconfigure(0, weight=1)
    top.grid_columnconfigure(1, weight=1)

def analyze_similarities(lbl_directory, report_text):
    selected_directory = lbl_directory.cget("text").replace("Directory selezionata: ", "")
    output_directory = os.path.join(selected_directory, "00_MixOutput")
    if not os.path.exists(output_directory):
        report_text.insert("end", "La directory 00_MixOutput non esiste. Esegui prima la fase di mix.\n")
        return
    files, similarity_matrix = plot_similarity_matrix(output_directory)
