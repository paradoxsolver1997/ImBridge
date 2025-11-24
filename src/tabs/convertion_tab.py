import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame


class ConvertionTab(BaseTab):

    def __init__(self, parent, title=None, logger=None):
        super().__init__(parent, title=title, logger=logger)
        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "convertion_output")
        self.build_content()

    def build_content(self):
        # Tool check (ghostscript, pstoedit, cairosvg)

        self.title_frame = TitleFrame(
            self,
            title_text="Format Conversion (Batch)",
            comment_text="Convert formats between bitmaps and vectors",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")

        input_filetypes=[
                ("Images & Vectors", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.svg;*.pdf;*.eps;*.ps"),
                ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff"),
                ("Vectors", "*.svg;*.pdf;*.eps;*.ps"),
            ]
        parameters = {
            "input_label": "Input Images",
            "input_filetypes": input_filetypes,
            "multiple_input_files": True,
            "output_label": "Output Folder",
            "default_output_dir": self.output_dir,
        }
        self.io_frame = InputOutputFrame(self, title="Settings", **parameters)
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")


        # Bitmap format selection
        convert_frame = ttk.LabelFrame(
            self, text="Convertion", style="Bold.TLabelframe"
        )
        convert_frame.pack(padx=(6, 8), pady=(8, 4), fill="x")
        bitmap_fmt_row = ttk.Frame(convert_frame)
        bitmap_fmt_row.pack(fill="x", padx=0, pady=4)
        self.out_fmt = tk.StringVar(value=".png")

        ttk.Label(bitmap_fmt_row, text="Output format:").pack(
            side="left", padx=(8, 4), anchor="w"
        )
        ttk.Combobox(
            bitmap_fmt_row,
            textvariable=self.out_fmt,
            values=[".jpg", ".png", ".bmp", ".tiff", ".jpeg", ".svg", ".pdf", ".eps", ".ps"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(8, 4))

        # Quality setting
        self.quality_var = tk.IntVar(value=95)
        self.quality_labeled_entry = LabeledValidatedEntry(
            bitmap_fmt_row,
            var=self.quality_var,
            bounds=(1, 100),
            label_prefix="Quality",
            width=5,
            enable_condition=lambda: self.out_fmt.get().lower() in (".jpg", ".jpeg"),
            trace_vars=[self.out_fmt],
        )
        self.quality_labeled_entry.pack(side="left", padx=(4, 4))


        self.dpi_var = tk.IntVar(value=300)
        self.dpi_labeled_entry = LabeledValidatedEntry(
            bitmap_fmt_row,
            var=self.dpi_var,
            bounds=(100, 600),
            label_prefix="DPI",
            width=6,
        )
        self.dpi_labeled_entry.pack(side="left", padx=(4, 4))

        ttk.Button(
            bitmap_fmt_row,
            text="Convert",
            command=lambda: self.batch_convert(
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.out_fmt.get(),
                quality=self.quality_var.get(),
                dpi=self.dpi_var.get(),
            ),
        ).pack(side="right", padx=8)
