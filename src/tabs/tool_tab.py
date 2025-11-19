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

        self.io_frame = InputOutputFrame(
            self,
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")]
        )
        self.io_frame.pack(padx=4, pady=(4, 2), fill="x")

        self.io_frame.out_dir_var.set(value=self.output_dir)
        if not os.path.exists(self.io_frame.out_dir_var.get()):
            os.makedirs(self.io_frame.out_dir_var.get(), exist_ok=True)

        row_1 = ttk.Frame(self)
        row_1.pack(padx=(0, 0), pady=(4, 4), fill="x")

        # The Upscale options
        frm_0 = ttk.LabelFrame(row_1, text="Option 1. Upscaling", style="Bold.TLabelframe")
        frm_0.pack(side="left", padx=8, pady=8, fill="both",expand=True)
        self.scale_factor_var = tk.DoubleVar(value=2.0)
        self.scale_factor_labeled_entry = LabeledValidatedEntry(
            frm_0,
            var=self.scale_factor_var,
            bounds=(1.0, 2.0),
            label_prefix="Scale Factor",
            width=6,
        )
        self.scale_factor_labeled_entry.pack(side="left", padx=(6, 8))
        ttk.Button(
            frm_0,
            text="Upscale & Save",
            command=lambda: self.batch_convert(
                mode="upscale",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                scale_factor=self.scale_factor_var.get()
            ),
        ).pack(side="left", padx=8)

        # The Grayscale option
        frm_1 = ttk.LabelFrame(
            row_1, text="Option 2. Grayscale", style="Bold.TLabelframe"
        )
        frm_1.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        ttk.Button(
            frm_1,
            text="Grayscale & Save",
            command=lambda: self.batch_convert(
                mode="grayscale",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
            ),
        ).pack(side="left", padx=(6, 8), pady=8)


        row_2 = ttk.Frame(self)
        row_2.pack(padx=(0, 0), pady=(4, 4), fill="x")

        # The Vectorize option
        frm_2 = ttk.LabelFrame(
            row_2, text="Option 3. Vectorization", style="Bold.TLabelframe"
        )
        frm_2.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        self.vector_fmt = tk.StringVar(value=".pdf")
        ttk.Label(frm_2, text="Output format:").pack(
            side="left", padx=(8, 4), pady=8
        )
        ttk.Combobox(
            frm_2,
            textvariable=self.vector_fmt,
            values=[".svg", ".pdf", ".eps", ".ps"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(6, 4))
        ttk.Button(
            frm_2,
            text="Vectorize & Save",
            command=lambda: self.batch_convert(
                mode="potrace",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.vector_fmt.get(),
            ),
        ).pack(side="left", padx=4)
        
        frm_3 = ttk.LabelFrame(
            row_2, text="Tool Check", style="Bold.TLabelframe"
        )
        frm_3.pack(side="left", padx=8, pady=8, fill="both", expand=True)
        status = "✔️" if converter.check_tool("potrace") else "❌"
        ttk.Label(frm_3, text=f"Potrace: {status}").pack(
            side="left", padx=(8, 4), pady=8
        )