import tkinter as tk
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def create_frame_raccolta(root):
    frame_raccolta = tk.Frame(root, bg="lightgreen")
    tk.Label(frame_raccolta, text="Modalità Raccolta - Layout da implementare",
    bg="lightgreen", font=("Arial", 14)).pack(padx=20, pady=20)
    return frame_raccolta