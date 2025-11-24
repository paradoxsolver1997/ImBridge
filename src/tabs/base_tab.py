import tkinter as tk

from src.frames.base_frame import BaseFrame

class BaseTab(BaseFrame):
    """
    Generic Tab base class, encapsulates common layout, logging, title, etc.
    Subclasses only need to implement custom widgets and business logic.
    """

    def __init__(self, parent, title=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.logger = getattr(self.winfo_toplevel(), "logger", None)
        self.preview_frame = getattr(self.winfo_toplevel(), "preview_frame", None)

        self.output_dir = getattr(self.winfo_toplevel(), "output_dir", None)
        self.out_dir = tk.StringVar(value=self.output_dir)

    # Subclasses can override this method to add custom widgets
    def build_content(self):
        pass

