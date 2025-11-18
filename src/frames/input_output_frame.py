import tkinter as tk
from tkinter import ttk, filedialog
import os
import logging
from src.frames.base_frame import BaseFrame
import subprocess
from src.frames.file_details_frame import FileDetailsFrame

class InputOutputFrame(BaseFrame):
    
    def __init__(
        self, parent, filetypes=None, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        # Input files

        frame = ttk.LabelFrame(
            self, text="Input/Output Settings", style="Bold.TLabelframe"
        )
        frame.pack(fill="x", padx=(4, 4), pady=4)

        input_row = ttk.Frame(frame)
        input_row.pack(fill="x", padx=0, pady=(4, 2))
        self.files_var = tk.StringVar()
        ttk.Label(input_row, text="Input files:").pack(
            side="left", padx=(6, 8), anchor="w"
        )
        ttk.Entry(input_row, textvariable=self.files_var).pack(
            side="left", padx=(2, 0), expand=True, fill="x"
        )
        ttk.Button(
            input_row,
            text="Browse...",
            command=lambda: self.browse_files(
                var=self.files_var,
                filetypes=filetypes or [("All Files", "*.*")],
                max_size_mb=None,
                multi=True,
                title="Select files",
            ),
        ).pack(side="left", padx=4)
        ttk.Button(
            input_row, text="File Details...", command=lambda: self.open_file_list()
        ).pack(side="left", padx=4)

        # Output directory
        output_row = ttk.Frame(frame)
        output_row.pack(fill="x", padx=0, pady=(2, 4))
        self.out_dir_var = tk.StringVar()
        ttk.Label(output_row, text="Output folder:").pack(side="left", padx=(6, 8))
        ttk.Entry(output_row, textvariable=self.out_dir_var).pack(
            side="left", padx=(0, 0), expand=True, fill="x"
        )
        ttk.Button(
            output_row, text="Select...", command=lambda: self.select_out_dir()
        ).pack(side="left", padx=4)
        ttk.Button(
            output_row, text="Open Folder...", command=lambda: self.open_out_dir()
        ).pack(side="left", padx=4)

    def browse_files(
        self, var, filetypes, max_size_mb=None, multi=True, title="Select files"
    ):
        """
        General file selection, supports multi-select, type filter, size limit.
        var: tk.StringVar bound variable
        filetypes: [('Images', '*.png;*.jpg'), ...]
        max_size_mb: max file size in MB, popup if exceeded
        multi: allow multi-select
        title: dialog title
        """
        dlg = filedialog.askopenfilenames if multi else filedialog.askopenfilename
        sel = dlg(title=title, filetypes=filetypes)
        if not sel:
            return
        files = sel if isinstance(sel, (list, tuple)) else [sel]
        oversize = []
        if max_size_mb:
            for f in files:
                try:
                    if os.path.getsize(f) > max_size_mb * 1024 * 1024:
                        oversize.append(f)
                except Exception:
                    pass
        if oversize:
            self.log(
                f"The following files exceed {max_size_mb}MB and will not be loaded:\n"
                + "\n".join(oversize), logging.ERROR
            )
            files = [f for f in files if f not in oversize]
        if files:
            var.set("\n".join(files))

    def select_out_dir(self, title="Select output folder"):
        sel = filedialog.askdirectory(title=title)
        if sel:
            self.out_dir_var.set(sel)

    def open_out_dir(self):
        path = self.out_dir_var.get()
        if not path or not os.path.isdir(path):
            self.log("Invalid Folder. Please select a valid output folder first.", logging.ERROR)
            return
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', path])
            else:
                self.log("Open Folder", f"Please open the folder manually: {path}")
        except Exception as e:
            self.log(f"Failed to open folder:\n{e}", logging.ERROR)


    def open_file_list(self):

        self.list_window = tk.Toplevel(self)
        self.list_window.title("文件详细信息")
        self.list_window.geometry(self.set_list_geometry())

        self.file_details_frame = FileDetailsFrame(
            self.list_window,
            file_list = self.files_var.get().strip().split("\n"),
        )
        self.file_details_frame.pack(fill="both", expand=True)
        # Initialize size, scaling, and scrollbars
        self.log("File details frame created.", logging.INFO)


    def set_list_geometry(self):
        main_x = self.winfo_toplevel().winfo_x()
        main_y = self.winfo_toplevel().winfo_y()
        main_w = self.winfo_toplevel().winfo_width()
        main_h = self.winfo_toplevel().winfo_height()
        popup_w = 400
        popup_h = 400
        # Make the popup window stick to the right side of the main window
        popup_x = main_x + main_w
        popup_y = main_y

        return f"{popup_w}x{popup_h}+{popup_x}+{popup_y}"