import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os
import webbrowser

from src.tabs.base_tab import BaseTab
from src.frames.title_frame import TitleFrame


docs_dir = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
        )



class AboutTab(BaseTab):
    """
    Tab for sharing files between PC and mobile devices.
    Integrates server configuration for file transfer.
    """

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.build_content()

    def build_content(self):
        # Server configuration widget

        self.title_frame = TitleFrame(
            self,
            title_text="About ImBridge",
            comment_text="A local tool for batch image/document conversion and enhancement.",
        )
        self.title_frame.pack(fill="x", padx=(8, 8), pady=(8, 4))

        self.info_frame = ttk.LabelFrame(self, text="Information", style="Bold.TLabelframe")
        self.info_frame.pack(fill="x", padx=(8, 8), pady=(4, 4))
        
        self.author_row = ttk.Frame(self.info_frame)
        self.author_row.pack(side="top", fill="x", padx=8, pady=(2, 2))
        self.author = ttk.Label(self.author_row, text="Author:")
        self.author.pack(side="left", anchor="w", padx=0, pady=(0, 0))
        self.author_link = ttk.Label(self.author_row, text="Paradoxsolver", foreground="blue", cursor="hand2")
        self.author_link.pack(side="left", anchor="w", padx=0, pady=(0, 0))
        self.render_hyperlink_label(self.author_link)
        self.author_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/paradoxsolver1997"))

        
        self.license_row = ttk.Frame(self.info_frame)
        self.license_row.pack(side="top", fill="x", padx=8, pady=(2, 2))
        self.license_label = ttk.Label(self.license_row, text="License: ")
        self.license_label.pack(side="left", anchor="w", padx=(0, 0), pady=(0, 0))
        self.license_link = ttk.Label(self.license_row, text="Mozilla Public License Version 2.0", foreground="blue", cursor="hand2")
        self.license_link.pack(side="left", anchor="w", padx=0, pady=(0, 0))
        self.render_hyperlink_label(self.license_link)
        self.license_link.bind("<Button-1>", lambda e: webbrowser.open("https://www.mozilla.org/en-US/MPL/2.0/"))

        self.project_row = ttk.Frame(self.info_frame)
        self.project_row.pack(side="top", fill="x", padx=8, pady=(2, 2))
        self.project_label = ttk.Label(self.project_row, text="Project: ")
        self.project_label.pack(side="left", anchor="w", padx=(0, 0), pady=(0, 0))
        self.project_link = ttk.Label(self.project_row, text="https://github.com/paradoxsolver1997/ImBridge", foreground="blue", cursor="hand2")
        self.project_link.pack(side="left", anchor="w", padx=0, pady=(0, 0))
        self.render_hyperlink_label(self.project_link)
        self.project_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/paradoxsolver1997/ImBridge"))


        self.thanks_frame = ttk.LabelFrame(self, text="Special Thanks", style="Bold.TLabelframe")
        self.thanks_frame.pack(fill="x", padx=(8, 8), pady=(4, 4))

        self.row_1 = ttk.Frame(self.thanks_frame)
        self.row_1.pack(side="top", fill="x", padx=8, pady=(2, 2))
        self.row_1_label = ttk.Label(self.row_1, text="See the Dependencies★ tab")
        self.row_1_label.pack(side="left", anchor="w", padx=(0, 0), pady=(2, 2))

        self.title_frame.pack(fill="x", padx=(8, 8), pady=(2, 2))
        self.help_frame = ttk.LabelFrame(
            self, text="Help & Documentation", style="Bold.TLabelframe"
        )
        self.help_frame.pack(fill="x", padx=(8, 8), pady=(2, 2))

        ttk.Button(self.help_frame, text="Open Help Document", command=lambda: webbrowser.open(f"file://{docs_dir}/help.html")).pack(
            side="left", padx=2, pady=(2, 2))
        ttk.Button(self.help_frame, text="Guide of Image Formats", command=lambda: webbrowser.open(f"file://{docs_dir}/image_formats.html")).pack(
            side="left", padx=2, pady=(2, 2))
        

    def show_license(self):
        license_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "LICENSE"))
        try:
            with open(license_path, "r", encoding="utf-8") as f:
                license_text = f.read()
        except Exception as ex:
            license_text = f"Failed to read LICENSE: {ex}"
        win = tk.Toplevel(self)
        win.title("MIT License")
        win.geometry("720x480")
        win.grab_set()
        frame = tk.Frame(win, bg="white")
        frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(frame, wrap="word", font=("Consolas", 11), bg="white", fg="#222", yscrollcommand=scrollbar.set)
        text.insert("1.0", license_text)
        text.config(state="disabled")
        text.pack(fill="both", expand=True, padx=8, pady=8)
        scrollbar.config(command=text.yview)


    def render_hyperlink_label(self, label: ttk.Label):
        underline_font = tkfont.Font(self, label.cget("font"))
        underline_font.configure(underline=True, family="Segoe UI", size=10, weight="normal")
        label.configure(font=underline_font)
