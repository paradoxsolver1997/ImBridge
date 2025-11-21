import tkinter as tk
from tkinter import ttk
import os
import json
from src.tabs.base_tab import BaseTab
from src.utils.commons import check_tool
from src.frames.title_frame import TitleFrame


class ToolTab(BaseTab):
    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "ink_output")
        
        tool_list_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs", "tool_list.json")
        with open(tool_list_path, "r", encoding="utf-8") as f:
            tool_list = json.load(f)
        self.python_keys = [(t["key"], t["display"]) for t in tool_list if t.get("type") == "python"]
        self.exe_keys = [(t["key"], t["display"]) for t in tool_list if t.get("type") == "exe"]
        self.dll_keys = [(t["key"], t["display"]) for t in tool_list if t.get("type") == "dll"]
        self.build_content()


    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Image Workshop",
            comment_text="Quick processing of your image",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")     

        # Tool Check
        python_row = ttk.LabelFrame(self, text="Python Dependencies", style="Bold.TLabelframe")
        python_row.pack(padx=(8, 8), pady=(4, 4), fill="x")
        for key, label in self.python_keys:
            status = "✔️" if check_tool(key) else "❌"
            color = "red" if status == "❌" else "black"
            ttk.Label(python_row, text="🛈", style="Info.TLabel").pack(
                side="left", padx=(6, 0), pady=(2, 4)
            )
            ttk.Label(python_row, text=f"{label}: {status}", foreground=color).pack(
                side="left", padx=(0, 8), pady=(8, 4)
            )

        external_row = ttk.LabelFrame(
            self, text="External Tools", style="Bold.TLabelframe"
        )
        external_row.pack(side="left", padx=8, pady=8, fill="both", expand=True)
        for key, label in self.exe_keys:
            sub_row = ttk.Frame(external_row)
            sub_row.pack(fill="x", pady=0)
            status = "✔️" if check_tool(key) else "❌"
            color = "red" if status == "❌" else "black"
            ttk.Label(sub_row, text="🛈", style="Info.TLabel").pack(
                side="left", padx=(6, 0), pady=(0, 0)
            )
            ttk.Label(sub_row, text=f"{label}: {status}", foreground=color).pack(
                side="left", padx=(0, 8), pady=(6, 0)
            )

        dll_row = ttk.LabelFrame(
            self, text="External Tools", style="Bold.TLabelframe"
        )
        dll_row.pack(side="left", padx=8, pady=8, fill="both", expand=True)
        for key, label in self.dll_keys:
            sub_row = ttk.Frame(dll_row)
            sub_row.pack(fill="x")
            status = "✔️" if check_tool(key) else "❌"
            color = "red" if status == "❌" else "black"
            ttk.Label(sub_row, text="🛈", style="Info.TLabel").pack(
                side="left", padx=(6, 0), pady=(2, 4)
            )
            ttk.Label(sub_row, text=f"{label}: {status}", foreground=color).pack(
                side="left", padx=(0, 8), pady=(8, 4)
            )