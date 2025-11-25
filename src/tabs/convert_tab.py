import tkinter as tk
from tkinter import ttk
import os
import shutil

import src.utils.converter as cv
from src.utils.commons import bitmap_formats, script_formats

from src.tabs.base_tab import BaseTab
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame


class ConvertTab(BaseTab):

    def __init__(self, parent, title=None, logger=None):
        super().__init__(parent, title=title, logger=logger)
        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "convert_output")
        self.build_content()
        self.on_files_var_changed()

    def build_content(self):
        # Tool check (ghostscript, pstoedit, cairosvg)

        self.title_frame = TitleFrame(
            self,
            title_text="Format Conversion (Batch)",
            comment_text="Convert formats between bitmaps and vectors",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")

        input_filetypes=[
                ("Images & Vectors", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.heic;*.heif;*.svg;*.pdf;*.eps;*.ps"),
                ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.heic;*.heif"),
                ("Vectors", "*.svg;*.pdf;*.eps;*.ps"),
            ]
        parameters = {
            "input_label": "Input Images",
            "input_filetypes": input_filetypes,
            "multiple_input_files": True,
            "output_label": "Output Folder",
            "default_output_dir": self.output_dir,
        }
        self.io_frame = InputOutputFrame(self, title="Input-Output Settings", **parameters)
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")
        self.io_frame.files_var.trace_add("write", self.on_files_var_changed)

        convert_row = ttk.Frame(self)
        convert_row.pack(side="top", padx=(0, 0), pady=(0, 4), fill="x", expand=True, anchor="n")

        # Bitmap format selection
        convert_frame = ttk.LabelFrame(
            convert_row, text="Out Format", style="Bold.TLabelframe"
        )
        convert_frame.pack(side="left", padx=(6, 8), pady=(8, 4), fill="both", expand=True)
        bitmap_fmt_row = ttk.Frame(convert_frame)
        bitmap_fmt_row.pack(fill="x", padx=0, pady=4)
        self.out_fmt = tk.StringVar(value=".png")
        self.out_fmt.trace_add("write", self.on_files_var_changed)

        ttk.Label(bitmap_fmt_row, text="Ext:").pack(
            side="left", padx=(8, 8), pady=8, anchor="w"
        )
        ttk.Combobox(
            bitmap_fmt_row,
            textvariable=self.out_fmt,
            values=[".jpg", ".png", ".bmp", ".tiff", ".jpeg", ".svg", ".pdf", ".eps", ".ps"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(8, 8), pady=8)

        parameter_frame = ttk.LabelFrame(
            convert_row, text="Parameters", style="Bold.TLabelframe"
        )
        parameter_frame.pack(side="left", padx=(6, 8), pady=(8, 4), fill="both", expand=True, anchor="n")
        sub_frame = ttk.Frame(parameter_frame)
        sub_frame.pack(side="top", pady=(4, 4), fill="x", expand=True, anchor="n")
        # Quality setting
        self.quality_var = tk.IntVar(value=95)
        self.quality_labeled_entry = LabeledValidatedEntry(
            sub_frame,
            var=self.quality_var,
            bounds=(1, 100),
            label_text="Quality",
            width=5,
        )
        self.quality_labeled_entry.pack(side="left", padx=(4, 4), pady=(8,8))


        self.dpi_var = tk.IntVar(value=300)
        self.dpi_labeled_entry = LabeledValidatedEntry(
            sub_frame,
            var=self.dpi_var,
            bounds=(100, 600),
            label_text="DPI",
            width=6,
        )
        self.dpi_labeled_entry.pack(side="left", padx=(4, 4), pady=(8, 8))

        control_frame = ttk.LabelFrame(
            convert_row, text="Out Format", style="Bold.TLabelframe"
        )
        control_frame.pack(side="left", padx=(6, 8), pady=(8, 4), fill="both", expand=True)

        ttk.Button(
            control_frame,
            text="Convert",
            command=lambda: self.batch_convert(
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                out_ext=self.out_fmt.get(),
                quality=self.quality_var.get(),
                dpi=self.dpi_var.get(),
            ),
            width=16
        ).pack(padx=8, pady=(8, 12))


    def batch_convert(self, file_list, out_dir, out_ext, **kwargs):
        """
        General batch conversion template.
        Args:
            process_func: single file handler, signature process_func(infile, outfile, **extra_args)
            log_prefix: log prefix (optional)
            extra_args: extra argument dict (optional)
        Automatically collects input files, output directory, batch processes, counts success and failure.
        Supports analysis-type handler (no output file), in which case process_func returns None.
        """
        # Treat [''] (from empty entry) as no input files
        self.logger.info(f"[New Convertion Task]: {len(file_list)} files")
        if not file_list or (len(file_list) == 1 and file_list[0].strip() == ""):
            self.logger.error("No input files selected")
            return
        self.preview_frame.clear_file_queue()
        out_ext = out_ext.lower()
        for f in file_list:
            base = os.path.splitext(os.path.basename(f))[0]
            in_ext = os.path.splitext(f)[1].lower()

            # Bitmap -> Bitmap
            if in_ext in bitmap_formats and out_ext in bitmap_formats:
                out_path = cv.raster_convert(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    quality=kwargs.get('quality', 95),
                    logger=self.logger,
                )
            # Bitmap -> Script (pdf/eps/ps)
            elif in_ext in bitmap_formats and out_ext in script_formats:
                out_path = cv.raster2script(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    dpi=kwargs.get('dpi', 300),
                    logger=self.logger,
                )
            # Bitmap -> SVG
            elif in_ext in bitmap_formats and out_ext == ".svg":
                out_path = cv.raster2svg(
                    in_path=f,
                    out_dir=out_dir,
                    logger=self.logger,
                )
            # Script (pdf/eps/ps) -> Bitmap
            elif in_ext in script_formats and out_ext in bitmap_formats:
                out_path = cv.script2raster(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    dpi=kwargs.get('dpi', 300),
                    logger=self.logger,
                )
            # Script (pdf/eps/ps) -> Script (pdf/eps/ps)
            elif in_ext == ".pdf" and out_ext in [".eps", ".ps"]:
                out_path = cv.pdf2script(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    logger=self.logger,
                )
            elif in_ext in script_formats and out_ext in script_formats:

                if in_ext == out_ext:
                    out_path = os.path.join(out_dir, base + "_copied" + out_ext)
                    shutil.copy2(f, out_path)
                    self.logger.info(f"Copied {f} to {out_path}")
                else:
                    out_path = cv.script_convert(
                        in_path=f,
                        out_dir=out_dir,
                        out_fmt=out_ext,
                        logger=self.logger,
                    )
            # Script (pdf/eps/ps) -> SVG
            elif in_ext in script_formats and out_ext == ".svg":
                out_path = cv.script2svg(
                    in_path=f,
                    out_dir=out_dir,
                    logger=self.logger,
                )
            # SVG -> Bitmap
            elif in_ext == ".svg" and out_ext in bitmap_formats:
                out_path = cv.svg2raster(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    logger=self.logger,
                )
            # SVG -> Script (pdf/eps/ps)
            elif in_ext == ".svg" and out_ext in script_formats:
                out_path = cv.svg2script(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    dpi=kwargs.get('dpi', 300),
                    logger=self.logger,
                )               
            else:
                self.logger.info(f"Unsupported conversion: {in_ext} -> {out_ext}")
                continue
            if out_path and os.path.exists(out_path):
                self.preview_frame.add_file_to_queue(out_path)
        self.logger.info("[Task Completed]")

    def on_files_var_changed(self, *args):
        if self.out_fmt.get().lower() in (".jpg", ".jpeg"):
            self.quality_labeled_entry.activate()
        else:
            self.quality_labeled_entry.deactivate()


        