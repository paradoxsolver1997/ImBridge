import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os
import json
import webbrowser

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
        self.python_keys = [(t["key"], t["display"], t["homepage"]) for t in tool_list if t.get("type") == "python"]
        self.exe_keys = [(t["key"], t["display"], t["homepage"]) for t in tool_list if t.get("type") == "exe"]
        self.dll_keys = [(t["key"], t["display"], t["homepage"]) for t in tool_list if t.get("type") == "dll"]
        self.external_keys = self.exe_keys + self.dll_keys
        self.build_content()


    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Dependencies Check",
            comment_text="A check list of required external tools and Python libraries.",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")     

        external_row = ttk.LabelFrame(
            self, text="Python Dependencies", style="Bold.TLabelframe"
        )
        external_row.pack(side="top", padx=8, pady=8, fill="x", expand=True, anchor="n")
        for key, label, homepage in self.python_keys:
            sub_row = ttk.Frame(external_row)
            sub_row.pack(fill="x", pady=0)
            status = "✔" if check_tool(key) else "✘"
            color = "red" if status == "✘" else "green"
            ttk.Label(sub_row, text=f"{status}", style="Info.TLabel", foreground=color).pack(
                side="left", padx=(6, 0), pady=0
            )
            ttk.Label(sub_row, text=f"{label}").pack(
                side="left", padx=(0, 8), pady=0
            )
            # 为每个link创建独立的变量
            link = ttk.Label(sub_row, text=homepage, foreground="blue", cursor="hand2")
            link.pack(side="left", anchor="w", padx=0, pady=0)
            self.render_hyperlink_label(link)
            # 使用lambda捕获当前循环的homepage值
            link.bind("<Button-1>", lambda e, url=homepage: webbrowser.open(url))

        dll_row = ttk.LabelFrame(
            self, text="External Tools", style="Bold.TLabelframe"
        )
        dll_row.pack(side="top", padx=8, pady=8, fill="x", expand=True, anchor="n")
        for key, label, homepage in self.external_keys:
            sub_row = ttk.Frame(dll_row)
            sub_row.pack(fill="x")
            status = "✔" if check_tool(key) else "✘"
            color = "red" if status == "✘" else "green"
            ttk.Label(sub_row, text=f"{status}", style="Info.TLabel", foreground=color).pack(
                side="left", padx=(6, 0), pady=0
            )
            ttk.Label(sub_row, text=f"{label}").pack(
                side="left", padx=(0, 8), pady=0
            )
            link = ttk.Label(sub_row, text=homepage, foreground="blue", cursor="hand2")
            link.pack(side="left", anchor="w", padx=0, pady=0)
            self.render_hyperlink_label(link)
            # 使用lambda捕获当前循环的homepage值
            link.bind("<Button-1>", lambda e, url=homepage: webbrowser.open(url))

    def render_hyperlink_label(self, label: ttk.Label):
        underline_font = tkfont.Font(self, label.cget("font"))
        underline_font.configure(underline=True, family="Segoe UI", size=10, weight="normal")
        label.configure(font=underline_font)