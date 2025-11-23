import tkinter as tk
import os

import src.utils.converter as cv
from src.frames.base_frame import BaseFrame
from src.utils.commons import bitmap_formats, script_formats


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

            # 位图 -> 位图
            if in_ext in bitmap_formats and out_ext in bitmap_formats:
                out_path = cv.raster_convert(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    quality=kwargs.get('quality', 95),
                    logger=self.logger,
                )
            # 位图 -> 脚本(pdf/eps/ps)
            elif in_ext in bitmap_formats and out_ext in script_formats:
                out_path = cv.raster2script(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    dpi=kwargs.get('dpi', 300),
                    logger=self.logger,
                )
            # 位图 -> svg
            elif in_ext in bitmap_formats and out_ext == ".svg":
                out_path = cv.raster2svg(
                    in_path=f,
                    out_dir=out_dir,
                    logger=self.logger,
                )
            # 脚本(pdf/eps/ps) -> 位图
            elif in_ext in script_formats and out_ext in bitmap_formats:
                out_path = cv.script2raster(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    dpi=kwargs.get('dpi', 300),
                    logger=self.logger,
                )
            # 脚本(pdf/eps/ps) -> 脚本(pdf/eps/ps)
            elif in_ext in script_formats and out_ext in script_formats:
                out_path = cv.script_convert(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    logger=self.logger,
                )
            # 脚本(pdf/eps/ps) -> svg
            elif in_ext in script_formats and out_ext == ".svg":
                out_path = cv.script2svg(
                    in_path=f,
                    out_dir=out_dir,
                    logger=self.logger,
                )
            # svg -> 位图
            elif in_ext == ".svg" and out_ext in bitmap_formats:
                out_path = cv.svg2raster(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    logger=self.logger,
                )
            # svg -> 脚本(pdf/eps/ps)
            elif in_ext == ".svg" and out_ext in script_formats:
                out_path = cv.svg2script(
                    in_path=f,
                    out_dir=out_dir,
                    out_fmt=out_ext,
                    dpi=kwargs.get('dpi', 300),
                    logger=self.logger,
                )
            # svg -> svg
            elif in_ext == ".svg" and out_ext == ".svg":
                # 直接拷贝
                import shutil
                out_path = os.path.join(out_dir, base + out_ext)
                shutil.copy2(f, out_path)
                self.logger.info(f"Copied {f} to {out_path}")
            else:
                self.logger.info(f"Unsupported conversion: {in_ext} -> {out_ext}")
                continue
            if out_path and os.path.exists(out_path):
                self.preview_frame.add_file_to_queue(out_path)
        self.logger.info("[Task Completed]")