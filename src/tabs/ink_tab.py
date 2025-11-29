import tkinter as tk
from tkinter import ttk
import os
import tempfile

from src.tabs.base_tab import BaseTab
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame
import src.utils.vector as vec
import src.utils.raster as rst
import src.utils.converter as cv
from src.utils.commons import confirm_dir_existence


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

        self.io_frame = InputOutputFrame(self, title="Input-Output Settings", **parameters)
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")
        self.io_frame.files_var.trace_add("write", self.on_files_var_changed)

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
            command=lambda: rst.grayscale_image(
                in_path=self.io_frame.files_var.get().strip().split("\n")[0],
                out_dir=self.io_frame.out_dir_var.get(),
                binarize=self.binarize_flag.get(),
                preview_callback=self.preview_frame.show_image,
                save_image=False,
                logger=self.logger,
            ),
            width=12
        ).pack(side="left", padx=(18, 4), pady=8)

        ttk.Button(
            option_1_frame,
            text="Save",
            command=lambda: rst.grayscale_image(
                in_path=self.io_frame.files_var.get().strip().split("\n")[0],
                out_dir=self.io_frame.out_dir_var.get(),
                binarize=self.binarize_flag.get(),
                preview_callback=self.preview_frame.show_image,
                save_image=True,
                logger=self.logger,
            ),
            width=12
        ).pack(side="left", padx=(4, 12), pady=8)

        # The Grayscale option
        option_2_frame = ttk.LabelFrame(
            convert_frame, text="Option 2. Vectorize", style="Bold.TLabelframe"
        )
        option_2_frame.pack(side="left", padx=8, pady=0, fill="both", expand=True)

        ttk.Button(
            option_2_frame,
            text="Preview",
            command=lambda: self.trace_image(save_image=False),
            width=12
        ).pack(side="left", padx=(18, 4), pady=8)

        ttk.Button(
            option_2_frame,
            text="Save",
            command=lambda: self.trace_image(save_image=True),
            width=12
        ).pack(side="left", padx=(4, 12), pady=8)


    def trace_image(self, save_image: bool = True):
        
        in_path = self.io_frame.files_var.get().strip().split("\n")[0]
        out_dir = self.io_frame.out_dir_var.get()

        if confirm_dir_existence(out_dir):
            if os.path.getsize(in_path) > 200 * 1024:
                raise RuntimeError(f"File too large (>200K): {os.path.basename(in_path)}")
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                in_fmt = os.path.splitext(in_path)[1].lower()
                if in_fmt != '.bmp':
                    # Automatically convert to bmp temporary file
                    temp_bmp = cv.raster_convert(in_path, tmp_dir, out_fmt='.bmp', logger=self.logger)
                    bmp_path = rst.grayscale_image(temp_bmp, tmp_dir, binarize=True, save_image=True, logger=self.logger)
                else:
                    bmp_path = rst.grayscale_image(in_path, tmp_dir, binarize=True, save_image=True, logger=self.logger)
                if save_image:
                    out_path = vec.trace_bmp_to_svg(bmp_path, out_dir, logger=self.logger)
                    self.preview_frame.show_file(out_path)
                    self.logger.info(f'Tracing {os.path.basename(in_path)} successful, saved to {os.path.basename(out_path)}.')
                else:
                    temp_bmp = vec.trace_bmp_to_svg(bmp_path, tmp_dir, logger=self.logger)
                    self.preview_frame.show_file(temp_bmp)
                    self.logger.info(f'Tracing {os.path.basename(in_path)} successful.')
                    out_path = None
            return out_path
        

    def on_files_var_changed(self, *args):
        self.preview_frame.clear_preview()
        