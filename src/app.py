import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os

from src.utils.logger import Logger

from src.frames.preview_frame import PreviewFrame
from src.frames.log_frame import LogFrame

from src.tabs.about_tab import AboutTab
from src.tabs.ink_tab import InkTab
from src.tabs.transform_tab import TransformTab
from src.tabs.tool_tab import ToolTab
from src.tabs.convertion_tab import ConvertionTab
from src.frames.file_details_frame import FileDetailsFrame
from src.tabs.crop_tab import CropTab


def init_styles():
    style = ttk.Style()
    # LabelFrame title font bold
    style.configure("Italic.TLabelframe.Label", font=("Segoe UI", 10, "italic"))
    style.configure("Bold.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    # Other styles that can be uniformly set:
    style.configure("TButton", font=("Segoe UI", 10))
    style.configure("TLabel", font=("Segoe UI", 10))
    style.configure("TEntry", font=("Segoe UI", 10))
    style.configure("Info.TLabel", font=("Arial", 20), foreground="blue")
    # You can continue to add other control styles


class App(tk.Tk):
    """Modular App for ImBridge (signature-focused subset)."""

    def __init__(self):
        super().__init__()

        init_styles()
        self.title("ImBridge")
        self.geometry("600x600")
        tkfont.nametofont("TkDefaultFont").config(family="Segoe UI", size=10)
        # Logging system
        self.logger = Logger(gui_widget=None)  # Not bound yet, will bind log_text later
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "output"
        )
        self.build_content()


    def build_content(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        # Notebook (tabs)
        nb = ttk.Notebook(main_frame)
        nb.pack(side="top", fill="both", expand=True)
        nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Bottom area: log and preview side by side
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side="bottom", fill="x")

        self.preview_frame = PreviewFrame(bottom_frame, title="OutputPreview", width=160, height=160)
        self.preview_frame.pack(side="right", fill="y", padx=0, pady=0, expand=False)

        self.log_frame = LogFrame(bottom_frame, title="Log Output")
        self.log_frame.pack(side="left", fill="both", expand=True)
        
        self.logger.set_gui_widget(self.log_frame.log_text)

        self.list_window = tk.Toplevel(self)
        self.list_window.title(f"文件详细信息 - {self.title}")
        self.list_window.protocol("WM_DELETE_WINDOW", self.hide_list_window)
        self.file_details_frame = FileDetailsFrame(self.list_window)
        self.file_details_frame.pack(fill="both", expand=True)
        self.list_window.withdraw()

        # Create and add tabs
        convertion_tab = ConvertionTab(nb)
        nb.add(convertion_tab, text=" Convert ")
        enhance_tab = InkTab(nb)
        nb.add(enhance_tab, text=" Ink Magic ")
        transform_tab = TransformTab(nb)
        nb.add(transform_tab, text=" Transform ")
        crop_tab = CropTab(nb)
        nb.add(crop_tab, text=" Crop ")
        tool_tab = ToolTab(nb)
        nb.add(tool_tab, text=" Dependencies★ ")
        about_tab = AboutTab(nb)
        nb.add(about_tab, text=" About ")

        nb.select(0)  # Enable Bitmap by default

    def on_tab_changed(self, event=None):
        self.preview_frame.clear_preview()
        nb = event.widget  # Notebook实例
        current_tab_id = nb.select()
        current_tab = nb.nametowidget(current_tab_id)
        # 假设tab有io_frame和files_var
        if hasattr(current_tab, "io_frame") and hasattr(current_tab.io_frame, "files_var"):
            current_tab.io_frame.files_var.set(value="")
            self.file_details_frame.populate_file_list([])

    def hide_list_window(self):
        self.list_window.withdraw()
