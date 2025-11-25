import tkinter as tk
from tkinter import ttk
from src.frames.base_frame import BaseFrame


class LogFrame(BaseFrame):

    def __init__(self, parent, title=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title = title if title is not None else "Log Output"
        log_frame = ttk.LabelFrame(self, text=self.title)
        log_frame.pack(side="left", fill="both", expand=True)

        # Log text area with scrollbar
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical")
        log_scroll.pack(side="right", fill="y")
        self.log_text = tk.Text(
            log_frame,
            height=10,
            state="disabled",
            font=("Consolas", 10),
            yscrollcommand=log_scroll.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True, padx=4, pady=2)
        log_scroll.config(command=self.log_text.yview)