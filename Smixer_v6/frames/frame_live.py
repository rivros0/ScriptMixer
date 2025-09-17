import tkinter as tk
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def create_frame_live(root):
    frame_live = tk.Frame(root, bg="lightblue")
    tk.Label(frame_live, text="Modalità Live - Layout da implementare",
    bg="lightblue", font=("Arial", 14)).pack(padx=20, pady=20)
    return frame_live