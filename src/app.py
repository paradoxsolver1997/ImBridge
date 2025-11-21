import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os

from src.utils.logger import Logger

from src.frames.preview_frame import PreviewFrame
from src.frames.log_frame import LogFrame

from src.tabs.about_tab import AboutTab
from src.tabs.ink_tab import InkTab
from src.tabs.resize_tab import ResizeTab
from src.tabs.tool_tab import ToolTab
from src.tabs.convertion_tab import ConvertionTab


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
        self.geometry("720x600")
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

        self.preview_frame = PreviewFrame(bottom_frame, title="Preview", width=160, height=160)
        self.preview_frame.pack(side="right", fill="y", padx=0, pady=0, expand=False)

        self.log_frame = LogFrame(bottom_frame, title="Log Output")
        self.log_frame.pack(side="left", fill="both", expand=True)
        
        self.logger.set_gui_widget(self.log_frame.log_text)

        # Create and add tabs
        convertion_tab = ConvertionTab(nb)
        nb.add(convertion_tab, text="  Convertion  ")
        #bitmap_tab = BitmapTab(nb)
        #nb.add(bitmap_tab, text="  Bitmap  ")
        #vector_tab = VectorTab(nb)
        #nb.add(vector_tab, text="  Vector  ")
        enhance_tab = InkTab(nb)
        nb.add(enhance_tab, text="  Workshop  ")
        resize_tab = ResizeTab(nb)
        nb.add(resize_tab, text="  Resize & Crop  ")
        #resize_vector_tab = ResizeVectorTab(nb)
        #nb.add(resize_vector_tab, text="  Resize Vector  ")
        tool_tab = ToolTab(nb)
        nb.add(tool_tab, text="  Dependencies★  ")
        about_tab = AboutTab(nb)
        nb.add(about_tab, text="  About  ")

        nb.select(0)  # Enable Bitmap by default

    def on_tab_changed(self, event=None):
        self.preview_frame.clear_preview()

    
