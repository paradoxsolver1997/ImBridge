import tkinter as tk
from tkinter import ttk
import os
from src.utils import converter
from src.tabs.base_tab import BaseTab
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame


class VectorTab(BaseTab):

    def __init__(self, parent, title=None, logger=None):
        super().__init__(parent, title=title, logger=logger)
        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "vector_output")
        self.build_content()

    def build_content(self):
        # Tool check (ghostscript, pstoedit, cairosvg)

        self.title_frame = TitleFrame(
            self,
            title_text="Vector Format Conversion (Batch)",
            comment_text="Convert vectors to vectors or bitmaps",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")

        self.io_frame = InputOutputFrame(
            self,
            filetypes=[("Vector", "*.svg;*.pdf;*.eps;*.ps")]
        )
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")

        self.io_frame.out_dir_var.set(value=self.output_dir)
        if not os.path.exists(self.io_frame.out_dir_var.get()):
            os.makedirs(self.io_frame.out_dir_var.get(), exist_ok=True)

        
        # Output format

        row_frame = ttk.Frame(self)
        row_frame.pack(padx=(0, 0), pady=(4, 4), fill="x")

        '''
        frm_1 = ttk.LabelFrame(
            row_frame, text="Option 1. Analyze Vectors", style="Bold.TLabelframe"
        )
        frm_1.pack(side="left", padx=(6, 8), pady=(4, 4), fill="both", expand=True)
        
        analyze_row = ttk.Frame(frm_1)
        analyze_row.pack(fill="x", padx=0, pady=(8, 8))
        ttk.Button(
            analyze_row,
            text="Analyze",
            command=lambda: self.batch_convert(
                mode="analyze",
                file_list=self.io_frame.files_var.get().strip().split("\n")
            ),
        ).pack(side="left", padx=8)
        '''
        frm_2 = ttk.LabelFrame(
            row_frame, text="Option 2. Convert to Vectors", style="Bold.TLabelframe"
        )
        frm_2.pack(side="left", padx=(6, 8), pady=(4, 4), fill="both", expand=True)
        format_row = ttk.Frame(frm_2)
        format_row.pack(fill="x", padx=0, pady=(8, 8))
        self.vector_fmt = tk.StringVar(value=".pdf")

        ttk.Label(format_row, text="Output format:").pack(
            side="left", padx=(8, 4), anchor="w"
        )
        ttk.Combobox(
            format_row,
            textvariable=self.vector_fmt,
            values=[".svg", ".pdf", ".eps", ".ps"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(6, 4))
        
        ttk.Button(
            format_row,
            text="Convert",
            command=lambda: self.batch_convert(
                mode="v2v",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.vector_fmt.get()
            ),
        ).pack(side="right", padx=8)

        # Bitmap format selection
        frm_3 = ttk.LabelFrame(
            self, text="Option 3. Convert to Bitmaps", style="Bold.TLabelframe"
        )
        frm_3.pack(padx=(6, 8), pady=(8, 4), fill="x")
        bitmap_fmt_row = ttk.Frame(frm_3)
        bitmap_fmt_row.pack(fill="x", padx=0, pady=4)
        self.bitmap_fmt = tk.StringVar(value=".png")

        ttk.Label(bitmap_fmt_row, text="Bitmap format:").pack(
            side="left", padx=(8, 4), anchor="w"
        )
        ttk.Combobox(
            bitmap_fmt_row,
            textvariable=self.bitmap_fmt,
            values=[".png", ".jpg", ".tiff"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(8, 4))

        # DPI setting
        self.dpi_var = tk.IntVar(value=300)
        self.dpi_labeled_entry = LabeledValidatedEntry(
            bitmap_fmt_row,
            var=self.dpi_var,
            bounds=(100, 600),
            label_prefix="DPI",
            width=6,
            enable_condition=lambda: self.bitmap_fmt.get().lower() != ".svg",
        )
        self.dpi_labeled_entry.pack(side="left", padx=(6, 4))

        ttk.Button(
            bitmap_fmt_row,
            text="Convert",
            command=lambda: self.batch_convert(
                mode="v2b",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.bitmap_fmt.get(),
                dpi=self.dpi_var.get(),
            ),
        ).pack(side="right", padx=8)
