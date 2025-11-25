import tkinter as tk
from tkinter import ttk
from src.frames.base_frame import BaseFrame

class CheckFrame(BaseFrame):
    
    def __init__(
        self, parent, title='', *args, **kwargs
    ):
        self.title = title
        super().__init__(parent, *args, **kwargs)
        self.var = tk.BooleanVar(value=False)
        self.check_button = ttk.Checkbutton(
            self,
            text=self.title,
            variable=self.var
        )
        self.check_button.pack(fill="x", padx=0, pady=(0,8))
