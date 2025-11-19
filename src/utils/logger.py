import logging
from tkinter import messagebox


class GuiLogHandler(logging.Handler):
    """Custom Handler to output logs to GUI controls (e.g., tk.Text)."""

    def __init__(self, text_widget=None):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        if self.text_widget:
            self.text_widget.config(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.config(state="disabled")


class Logger:
    """Unified logging interface for the project, supporting both standard output and GUI output."""

    def __init__(self, name="ImBridge", gui_widget=None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.fmt = logging.Formatter(
            "[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # ConsoleHandler
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            ch = logging.StreamHandler()
            ch.setFormatter(self.fmt)
            self.logger.addHandler(ch)

        # GUI Handler
        if gui_widget and not any(
            isinstance(h, GuiLogHandler) for h in self.logger.handlers
        ):
            gh = GuiLogHandler(gui_widget)
            gh.setFormatter(self.fmt)
            self.logger.addHandler(gh)

    def set_gui_widget(self, widget):
        """Dynamically set/update GUI widget."""
        for h in self.logger.handlers:
            if isinstance(h, GuiLogHandler):
                h.text_widget = widget
                return
        gh = GuiLogHandler(widget)
        gh.setFormatter(self.fmt)
        self.logger.addHandler(gh)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg, messagebox_flag=True):
        self.logger.warning(msg)
        if messagebox_flag:
            messagebox.showwarning("Warning", str(msg))

    def error(self, msg, messagebox_flag=False):
        self.logger.error(msg)
        if messagebox_flag:
            messagebox.showerror("Error", str(msg))

    def debug(self, msg):
        self.logger.debug(msg)

    def exception(self, msg):
        self.logger.exception(msg)

    def get_logger(self):
        return self.logger