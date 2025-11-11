import tkinter as tk
from tkinter import ttk

from src.frames.base_frame import BaseFrame


class TitleFrame(BaseFrame):
    def __init__(self, parent, title_text, comment_text=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        title_frame = ttk.LabelFrame(self, text=title_text, style="Bold.TLabelframe")
        title_frame.pack(fill="x", expand=True, pady=(4, 4), padx=(4, 4))
        if comment_text:
            comment_row = ttk.Frame(title_frame)
            comment_row.pack(fill="x", padx=(0, 4), pady=(4, 8))
            ttk.Label(comment_row, text=comment_text).pack(side="left", padx=(6, 4))
