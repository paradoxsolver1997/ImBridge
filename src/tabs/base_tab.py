import tkinter as tk
import os
import logging
import src.utils.converter as cv
import src.utils.scaler as sc

from src.frames.base_frame import BaseFrame
from src.utils.commons import confirm_overwrite
from src.utils.commons import bitmap_formats, vector_formats



class BaseTab(BaseFrame):
    """
    Generic Tab base class, encapsulates common layout, logging, title, etc.
    Subclasses only need to implement custom widgets and business logic.
    """

    def __init__(self, parent, title=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.logger = getattr(self.winfo_toplevel(), "logger", None)
        self.preview_frame = getattr(self.winfo_toplevel(), "preview_frame", None)

        self.output_dir = getattr(self.winfo_toplevel(), "output_dir", None)
        self.out_dir = tk.StringVar(value=self.output_dir)

    # Subclasses can override this method to add custom widgets
    def build_content(self):
        pass


    def batch_convert(self, file_list, out_dir=None, out_ext=None, **kwargs):
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
        self.log(f"[New Convertion Task]: {len(file_list)} files", logging.INFO)
        if not file_list or (len(file_list) == 1 and file_list[0].strip() == ""):
            self.log("No input files selected", logging.ERROR)
            return
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        self.preview_frame.clear_file_queue()
        out_ext = out_ext.lower()
        for f in file_list:
            base = os.path.splitext(os.path.basename(f))[0]
            in_ext = os.path.splitext(f)[1].lower()
            if out_ext in bitmap_formats:
                # Bitmap output
                out_path = os.path.join(out_dir, base + out_ext)
                if confirm_overwrite(out_path):
                    if in_ext in vector_formats:
                        cv.vector_to_bitmap(
                            in_path=f,
                            out_path=out_path,
                            dpi=kwargs.get('dpi', 300),
                            log_fun=self.log,
                        )
                    else:
                        cv.bitmap_to_bitmap(
                            in_path=f,
                            out_path=out_path,
                            quality=kwargs.get('quality', 95),
                            log_fun=self.log,
                        )
            elif out_ext in vector_formats:
                # Vector output
                out_path = os.path.join(out_dir, base + out_ext)
                if confirm_overwrite(out_path):
                    if in_ext in vector_formats:
                        cv.vector_to_vector(
                            in_path=f,
                            out_path=out_path,
                            log_fun=self.log,
                        )
                    else:
                        cv.embed_bitmap_to_vector(
                            in_path=f,
                            out_path=out_path,
                            dpi=kwargs.get('dpi', 300),
                            log_fun=self.log,
                        )
            else:
                self.log(f"Unsupported output format: {out_ext}", logging.ERROR)
                continue
            if out_path and os.path.exists(out_path):
                self.preview_frame.add_file_to_queue(out_path)
        self.log("[Task Completed]", logging.INFO)