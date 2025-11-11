import tkinter as tk
from tkinter import ttk
import logging


class BaseFrame(ttk.Frame):
    """
    Generic Frame base class for all custom Frames to inherit from.
    This can be extended to include common methods, properties, styles, etc.
    """

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        # Common initialization logic can be added here
        self.logger = getattr(self.winfo_toplevel(), "logger", None)

    def build_contents(self):
        pass

    def log(self, message, level=logging.INFO):
        if self.logger:
            self.logger.log(message, level)

    def activate(self):
        def activate_frame(frame):
            if isinstance(frame, ttk.Labelframe):
                frame.configure(style="Normal.TLabelframe")
            for child in frame.winfo_children():
                try:
                    child.configure(state="normal")
                    child.configure(foreground="black")
                except Exception:
                    pass
                activate_frame(child)

        activate_frame(self)

    def deactivate(self):
        def deactivate_frame(frame):
            if isinstance(frame, ttk.Labelframe):
                frame.configure(style="Gray.TLabelframe")
            for child in frame.winfo_children():
                try:
                    child.configure(state="disabled")
                    child.configure(foreground="gray")
                except Exception:
                    pass
                deactivate_frame(child)

        deactivate_frame(self)
