import tkinter as tk
from tkinter import ttk, filedialog
import os
import logging
from src.frames.base_frame import BaseFrame
import subprocess
from src.frames.file_details_frame import FileDetailsFrame

class InputOutputFrame(BaseFrame):
    
    def __init__(
        self, parent, title='', filetypes=None, multi=True, *args, **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        # Input files
        self.title = title
        frame = ttk.LabelFrame(
            self, text="Input/Output Settings", style="Bold.TLabelframe"
        )
        frame.pack(fill="x", padx=(4, 4), pady=4)

        input_row = ttk.Frame(frame)
        input_row.pack(fill="x", padx=0, pady=(4, 2))
        self.files_var = tk.StringVar()
        self.files_var.trace_add("write", self.on_files_var_changed)
            
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
                multi=multi,
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
            self.logger.error(
                f"The following files exceed {max_size_mb}MB and will not be loaded:\n"
                + "\n".join(oversize)
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
            self.logger.error("Invalid Folder. Please select a valid output folder first.")
            return
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', path])
            else:
                self.logger.info("Open Folder", f"Please open the folder manually: {path}")
        except Exception as e:
            self.logger.error(f"Failed to open folder:\n{e}")


    def open_file_list(self):

        self.list_window = tk.Toplevel(self)
        self.list_window.title(f"文件详细信息 - {self.title}")
        self.list_window.geometry(self.set_list_geometry())

        self.file_details_frame = FileDetailsFrame(
            self.list_window,
            file_list = self.files_var.get().strip().split("\n"),
        )
        self.file_details_frame.pack(fill="both", expand=True)
        # Initialize size, scaling, and scrollbars
        self.logger.info("File details frame created.")


    def set_list_geometry(self):
        main_x = self.winfo_toplevel().winfo_x()
        main_y = self.winfo_toplevel().winfo_y()
        main_w = self.winfo_toplevel().winfo_width()
        main_h = self.winfo_toplevel().winfo_height()
        popup_w = 400
        popup_h = 600
        # Make the popup window stick to the right side of the main window
        popup_x = main_x + main_w
        popup_y = main_y

        return f"{popup_w}x{popup_h}+{popup_x}+{popup_y}"
    
    def on_files_var_changed(self, *args):
        # 当文件列表变化时，若详情窗口存在且未销毁，则刷新
        if hasattr(self, "file_details_frame") and hasattr(self, "list_window"):
            if self.list_window.winfo_exists():
                # 重新加载文件列表
                file_list = self.files_var.get().strip().split("\n")
                # 重新构建 file_details_frame
                self.file_details_frame.destroy()
                self.file_details_frame = FileDetailsFrame(
                    self.list_window,
                    file_list=file_list,
                )
                self.file_details_frame.pack(fill="both", expand=True)
                self.logger.info("File details frame refreshed due to file list change.")

    def load_file_list(self):
        try:
            file_list = [f for f in self.files_var.get().strip().split("\n") if f.strip()]
            if not file_list or not all(os.path.isfile(f) for f in file_list):
                self.logger.error("No valid input file selected.")
                return
            return file_list
        except Exception as e:
            self.logger.error(f"Failed to open image: {e}")
            return