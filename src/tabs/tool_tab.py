import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
from src.utils import converter
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame


class ToolTab(BaseTab):
    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "ink_output")
        self.build_content()

    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Image Workshop",
            comment_text="Quick processing of your image",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")     

        # Tool Check
        tool_row = ttk.LabelFrame(self, text="Tool Check", style="Bold.TLabelframe")
        tool_row.pack(padx=(8, 8), pady=(4, 4), fill="x")
        tool_keys = [
            ("cairosvg", "cairosvg"),
            ("PyPDF2", "PyPDF2"),
            ("ghostscript", "Ghostscript"),
            ("pstoedit", "pstoedit"),
            ("libcairo-2.dll", "libcairo-2.dll"),
        ]
        for key, label in tool_keys:
            status = "✔️" if converter.check_tool(key) else "❌"
            color = "red" if status == "❌" else "black"
            ttk.Label(tool_row, text=f"{label}: {status}", foreground=color).pack(
                side="left", padx=(6, 8), pady=8
            )


        frm_3 = ttk.LabelFrame(
            self, text="Tool Check", style="Bold.TLabelframe"
        )
        frm_3.pack(side="left", padx=8, pady=8, fill="both", expand=True)
        status = "✔️" if converter.check_tool("potrace") else "❌"
        ttk.Label(frm_3, text=f"Potrace: {status}").pack(
            side="left", padx=(8, 4), pady=8
        )