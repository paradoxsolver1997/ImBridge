import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame


class BitmapTab(BaseTab):
    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)
        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "bitmap_output")
        self.build_content()

    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Bitmap Format Conversion (Batch)",
            comment_text="Convert bitmaps to bitmaps or vectors",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")

        self.io_frame = InputOutputFrame(
            self,
            title='Bitmap',
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.heic;*.heif;*.bmp;*.tiff")]
        )
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")

        self.io_frame.out_dir_var.set(value=self.output_dir)
        if not os.path.exists(self.io_frame.out_dir_var.get()):
            os.makedirs(self.io_frame.out_dir_var.get(), exist_ok=True)

        # Output format
        frm_2 = ttk.LabelFrame(
            self, text="Option 1. Convert to Bitmaps", style="Bold.TLabelframe"
        )
        frm_2.pack(padx=8, pady=(4, 4), fill="x")

        format_row = ttk.Frame(frm_2)
        format_row.pack(fill="x", padx=0, pady=(8, 8))
        ext_options = [".jpg", ".png", ".bmp", ".tiff", ".jpeg"]
        ttk.Label(format_row, text="Output Format:").pack(side="left", padx=(6, 8))
        self.bitmap_fmt = tk.StringVar(value=".jpg")
        ttk.Combobox(
            format_row,
            textvariable=self.bitmap_fmt,
            values=ext_options,
            width=8,
            state="readonly",
        ).pack(side="left", padx=(8, 4))

        self.quality_var = tk.IntVar(value=95)
        self.quality_labeled_entry = LabeledValidatedEntry(
            format_row,
            var=self.quality_var,
            bounds=(1, 100),
            label_prefix="Quality",
            width=5,
            enable_condition=lambda: self.bitmap_fmt.get().lower() in (".jpg", ".jpeg"),
            trace_vars=[self.bitmap_fmt],
        )
        self.quality_labeled_entry.pack(side="left", padx=(4, 4))

        ttk.Button(
            format_row,
            text="Convert",
            command=lambda: self.batch_convert(
                mode="b2b",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.bitmap_fmt.get(),
                quality=self.quality_var.get(),
            ),
        ).pack(side="right", padx=4)

        frm_3 = ttk.LabelFrame(
            self, text="Option 2. Convert to Vectors (Embedding)", style="Bold.TLabelframe"
        )
        frm_3.pack(padx=8, pady=(8, 4), fill="x")

        # Vector format selection and embedding button
        vector_fmt_row = ttk.Frame(frm_3)
        vector_fmt_row.pack(fill="x", padx=0, pady=(8, 8))
        self.vector_fmt = tk.StringVar(value=".svg")
        vector_options = [".svg", ".pdf", ".eps", ".ps"]
        ttk.Label(vector_fmt_row, text="Output Format:").pack(
            side="left", padx=(6, 8), anchor="w"
        )
        ttk.Combobox(
            vector_fmt_row,
            textvariable=self.vector_fmt,
            values=vector_options,
            width=8,
            state="readonly",
        ).pack(side="left", padx=(4, 4))

        # DPI entry
        self.dpi_var = tk.IntVar(value=300)
        self.dpi_labeled_entry = LabeledValidatedEntry(
            vector_fmt_row,
            var=self.dpi_var,
            bounds=(100, 600),
            label_prefix="DPI",
            width=6,
            enable_condition=lambda: self.vector_fmt.get().lower() != ".svg",
            trace_vars=[self.vector_fmt],
        )
        self.dpi_labeled_entry.pack(side="left", padx=(4, 4))

        ttk.Button(
            vector_fmt_row,
            text="Convert",
            command=lambda: self.batch_convert(
                mode="b2v",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.vector_fmt.get(),
                dpi=self.dpi_var.get(),
            ),
        ).pack(side="right", padx=4)
