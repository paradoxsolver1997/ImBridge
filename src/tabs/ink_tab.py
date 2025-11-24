import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame
import src.utils.inker as ik


class InkTab(BaseTab):
    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "ink_output")
        self.build_content()

    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Ink Magic",
            comment_text="Turn your image into grayscale, black & white, or vector sketch",
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
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")

        convert_frame = ttk.Frame(self)
        convert_frame.pack(padx=(0, 0), pady=(8, 4), fill="x")

        # The Grayscale option
        option_1_frame = ttk.LabelFrame(
            convert_frame, text="Option 1. Grayscale", style="Bold.TLabelframe"
        )
        option_1_frame.pack(side="left", padx=8, pady=0, fill="both", expand=True)


        # DPI enable checkbox and setting
        self.binarize_flag = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            option_1_frame,
            text="Binarize",
            variable=self.binarize_flag,
            onvalue=True,
            offvalue=False
        ).pack(side="left", padx=(6, 2))

        ttk.Button(
            option_1_frame,
            text="Preview",
            command=lambda: ik.grayscale_image(
                in_path=self.io_frame.files_var.get().strip().split("\n")[0],
                out_dir=self.io_frame.out_dir_var.get(),
                binarize=self.binarize_flag.get(),
                preview_callback=self.preview_frame.show_image,
                save_image=False,
                logger=self.logger,
            )
        ).pack(side="left", padx=(6, 8), pady=8)

        ttk.Button(
            option_1_frame,
            text="Save",
            command=lambda: ik.grayscale_image(
                in_path=self.io_frame.files_var.get().strip().split("\n")[0],
                out_dir=self.io_frame.out_dir_var.get(),
                binarize=self.binarize_flag.get(),
                preview_callback=self.preview_frame.show_image,
                save_image=True,
                logger=self.logger,
            )
        ).pack(side="left", padx=(6, 8), pady=8)

        # The Grayscale option
        option_2_frame = ttk.LabelFrame(
            convert_frame, text="Option 2. Vectorize", style="Bold.TLabelframe"
        )
        option_2_frame.pack(side="left", padx=8, pady=0, fill="both", expand=True)

        ttk.Button(
            option_2_frame,
            text="Preview",
            command=lambda: ik.trace_image(
                in_path=self.io_frame.files_var.get().strip().split("\n")[0],
                out_dir=self.io_frame.out_dir_var.get(),
                preview_callback=self.preview_frame.show_image,
                save_image=False,
                logger=self.logger,
            )
        ).pack(side="left", padx=(6, 8), pady=8)

        ttk.Button(
            option_2_frame,
            text="Save",
            command=lambda: ik.trace_image(
                in_path=self.io_frame.files_var.get().strip().split("\n")[0],
                out_dir=self.io_frame.out_dir_var.get(),
                preview_callback=self.preview_frame.show_image,
                save_image=True,
                logger=self.logger,
            )
        ).pack(side="left", padx=(6, 8), pady=8)
