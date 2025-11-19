import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk
import logging
import tempfile
from src.utils import converter
from src.utils import enhancement

from src.frames.base_frame import BaseFrame

bitmap_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
vector_formats = [".svg", ".pdf", ".eps", ".ps"]

def confirm_overwrite(out_path):
    if os.path.exists(out_path):
        return messagebox.askyesno(
            "File Exists", f"File already exists:\n{out_path}\nOverwrite?"
        )
    return True


def acknowledge_overwrite():
    """
    Show a dialog warning that file overwrite will not prompt again during conversion.
    Returns True if user chooses to continue, False to cancel.
    """
    try:
        return messagebox.askyesno(
            "Overwrite Warning",
            "After conversion starts, existing files may be overwritten without further prompts. Continue?",
        )
    except Exception:
        return True  # Default to continue if no GUI context


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

    
    def batch_convert2(self, mode, file_list, out_dir=None, out_ext=None, **kwargs):
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
        self.log(f"[New Task]: {mode}, {len(file_list)} files", logging.INFO)
        if not file_list or (len(file_list) == 1 and file_list[0].strip() == ""):
            self.log("No input files selected", logging.ERROR)
            return
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        self.preview_frame.clear_file_queue()
        for f in file_list:
            base = os.path.splitext(os.path.basename(f))[0]
            if mode == "b2v":
                out_path = os.path.join(out_dir, base + out_ext)
                if confirm_overwrite(out_path):
                    converter.embed_bitmap_to_vector(
                        in_path=f,
                        out_path=out_path,
                        dpi=kwargs.get('dpi', 300),
                        log_fun=self.log,
                    )
            elif mode == "b2b":
                out_path = os.path.join(out_dir, base + out_ext)
                if confirm_overwrite(out_path):
                    converter.bitmap_to_bitmap(
                        in_path=f,
                        out_path=out_path,
                        quality=kwargs.get('quality', 95),
                        log_fun=self.log,
                    )
            elif mode == "v2b":
                out_path = os.path.join(out_dir, base + out_ext)
                if confirm_overwrite(out_path):
                    converter.vector_to_bitmap(
                        in_path=f,
                        out_path=out_path,
                        dpi=kwargs.get('dpi', 300),
                        log_fun=self.log,
                    )
            elif mode == "v2v":
                out_path = os.path.join(out_dir, base + out_ext)
                if confirm_overwrite(out_path):
                    converter.vector_to_vector(
                        in_path=f, out_path=out_path, log_fun=self.log
                    )
                '''
            elif mode == "upscale":
                out_path = os.path.join(out_dir, 'upscaled_' + os.path.basename(f))
                if confirm_overwrite(out_path):
                    enhancement.upscale_image(
                        f,
                        out_path=out_path,
                        scale_factor=kwargs.get('scale_factor', 2),
                        log_fun=self.log,
                    )
                '''
            elif mode == "grayscale":
                out_path = os.path.join(out_dir, 'grayscale_' + os.path.basename(f))
                if confirm_overwrite(out_path):
                    enhancement.grayscale_image(
                        f, 
                        out_path=out_path, 
                        log_fun=self.log
                    )
            elif mode == "binarize":
                out_path = os.path.join(out_dir, 'binarize_' + os.path.basename(f))
                if confirm_overwrite(out_path):
                    enhancement.grayscale_image(
                        f, 
                        out_path=out_path, 
                        log_fun=self.log,
                        binarize=True
                    )
            elif mode == "potrace":
                if os.path.getsize(f) > 200 * 1024:
                    raise RuntimeError(f"File too large (>200K): {os.path.basename(f)}")
                bmp_path = os.path.join(out_dir, base + "_potrace.bmp")
                out_path = os.path.join(out_dir, 'traced_' + base + out_ext)
                if confirm_overwrite(out_path):
                    enhancement.grayscale_image(
                        f, bmp_path, log_fun=self.log, binarize=True
                    )
                    converter.bmp_to_vector(bmp_path, out_path, log_fun=self.log)
                    try:
                        os.remove(bmp_path)
                        self.log(f"Temporary BMP removed: {bmp_path}", logging.INFO)
                    except Exception as e:
                        self.log(
                            f"Warning: failed to remove temp BMP: {bmp_path}, {e}",
                            logging.WARNING,
                        )
            else:
                out_path = None
                raise ValueError("Unsupported conversion mode")
            if out_path and os.path.exists(out_path):
                self.preview_frame.add_file_to_queue(out_path)

        self.log("[Task Completed]", logging.INFO)



    def batch_convert(self, mode, file_list, out_dir=None, out_ext=None, **kwargs):
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
        self.log(f"[New Task]: {mode}, {len(file_list)} files", logging.INFO)
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
            if mode == "convert":
                if out_ext in bitmap_formats:
                    # Bitmap output
                    out_path = os.path.join(out_dir, base + out_ext)
                    if confirm_overwrite(out_path):
                        if in_ext in vector_formats:
                            converter.vector_to_bitmap(
                                in_path=f,
                                out_path=out_path,
                                dpi=kwargs.get('dpi', 300),
                                log_fun=self.log,
                            )
                        else:
                            converter.bitmap_to_bitmap(
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
                            converter.vector_to_vector(
                                in_path=f,
                                out_path=out_path,
                                log_fun=self.log,
                            )
                        else:
                            converter.embed_bitmap_to_vector(
                                in_path=f,
                                out_path=out_path,
                                dpi=kwargs.get('dpi', 300),
                                log_fun=self.log,
                            )
                else:
                    self.log(f"Unsupported output format: {out_ext}", logging.ERROR)
                    continue
            
            elif mode == "grayscale":
                out_path = os.path.join(out_dir, 'grayscale_' + os.path.basename(f))
                if confirm_overwrite(out_path):
                    enhancement.grayscale_image(
                        f, 
                        out_path=out_path, 
                        log_fun=self.log
                    )
            elif mode == "binarize":
                out_path = os.path.join(out_dir, 'binarize_' + os.path.basename(f))
                if confirm_overwrite(out_path):
                    enhancement.grayscale_image(
                        f, 
                        out_path=out_path, 
                        log_fun=self.log,
                        binarize=True
                    )
            elif mode == "potrace":
                if os.path.getsize(f) > 200 * 1024:
                    raise RuntimeError(f"File too large (>200K): {os.path.basename(f)}")
                bmp_path = os.path.join(out_dir, base + "_potrace.bmp")
                out_path = os.path.join(out_dir, 'traced_' + base + out_ext)
                if confirm_overwrite(out_path):
                    enhancement.grayscale_image(
                        f, bmp_path, log_fun=self.log, binarize=True
                    )
                    converter.bmp_to_vector(bmp_path, out_path, log_fun=self.log)
                    try:
                        os.remove(bmp_path)
                        self.log(f"Temporary BMP removed: {bmp_path}", logging.INFO)
                    except Exception as e:
                        self.log(
                            f"Warning: failed to remove temp BMP: {bmp_path}, {e}",
                            logging.WARNING,
                        )
            else:
                out_path = None
                raise ValueError("Unsupported conversion mode")
            if out_path and os.path.exists(out_path):
                self.preview_frame.add_file_to_queue(out_path)

        self.log("[Task Completed]", logging.INFO)