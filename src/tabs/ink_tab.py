import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame
import src.utils.scaler as sc


class InkTab(BaseTab):
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

        input_filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")]
        parameters = {
            "input_label": "Input Image",
            "input_filetypes": input_filetypes,
            "multiple_input_files": False,
            "output_label": "Output Folder",
            "default_output_dir": self.output_dir,
        }

        self.io_frame = InputOutputFrame(self, **parameters)
        self.io_frame.pack(padx=4, pady=(4, 2), fill="x")

        row_1 = ttk.Frame(self)
        row_1.pack(padx=(0, 0), pady=(4, 4), fill="x")

        # The Grayscale option
        frm_1 = ttk.LabelFrame(
            row_1, text="Option 1. Grayscale", style="Bold.TLabelframe"
        )
        frm_1.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        ttk.Button(
            frm_1,
            text="Grayscale & Save",
            command=lambda: sc.grayscale_image(
                        in_path=self.io_frame.files_var.get().strip().split("\n")[0], 
                        out_path=os.path.join(
                            self.io_frame.out_dir_var.get(), 
                            'grayscale_' + os.path.basename(
                                self.io_frame.files_var.get().strip().split("\n")[0]
                            )
                        ), 
                        log_fun=self.log,
                        binarize=False
                    )
        ).pack(side="left", padx=(6, 8), pady=8)

        # The Grayscale option
        frm_1 = ttk.LabelFrame(
            row_1, text="Option 2. Binarize", style="Bold.TLabelframe"
        )
        frm_1.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        ttk.Button(
            frm_1,
            text="Binarize & Save",
            command=lambda: sc.grayscale_image(
                        in_path=self.io_frame.files_var.get().strip().split("\n")[0], 
                        out_path=os.path.join(
                            self.io_frame.out_dir_var.get(), 
                            'binarize_' + os.path.basename(
                                self.io_frame.files_var.get().strip().split("\n")[0]
                            )
                        ), 
                        log_fun=self.log,
                        binarize=True
                    )
        ).pack(side="left", padx=(6, 8), pady=8)

        row_2 = ttk.Frame(self)
        row_2.pack(padx=(0, 0), pady=(4, 4), fill="x")

        # The Vectorize option
        frm_2 = ttk.LabelFrame(
            row_2, text="Option 3. Vectorization", style="Bold.TLabelframe"
        )
        frm_2.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        ttk.Button(
            frm_2,
            text="Vectorize & Save",
            command=lambda: self.batch_convert(
                mode="potrace",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=".svg",
            ),
        ).pack(side="left", padx=4)
        