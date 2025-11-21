import tkinter as tk
from tkinter import ttk, filedialog
import os
import logging
from src.frames.base_frame import BaseFrame
import subprocess
from src.frames.file_details_frame import FileDetailsFrame

class InputOutputFrame(BaseFrame):
    
    def __init__(
        self, parent, title='Input & Output', *args, **kwargs
    ):
        self.title = title
        self.multiple_input_files = kwargs.pop("multiple_input_files", False)
        self.input_filetypes = kwargs.pop("input_filetypes", [("All Files", "*.*")])
        self.input_label = kwargs.pop("input_label", "Input Images" if self.multiple_input_files else "Input Image")
        self.output_label = kwargs.pop("output_label", "Output Folder")
        self.default_output_dir = kwargs.pop("default_output_dir", "")
        self.max_size_mb = kwargs.pop("max_size_mb", None)
        super().__init__(parent, *args, **kwargs)
        # Input files
        
        self.list_window = getattr(self.winfo_toplevel(), "list_window", None)
        self.file_details_frame = getattr(self.winfo_toplevel(), "file_details_frame", None)
        frame = ttk.LabelFrame(
            self, text=self.title, style="Bold.TLabelframe"
        )
        frame.pack(fill="x", padx=(4, 4), pady=4)

        input_row = ttk.Frame(frame)
        input_row.pack(fill="x", padx=0, pady=(4, 2))
        self.files_var = tk.StringVar()
        self.files_var.trace_add("write", self.refresh_file_list)
            
        ttk.Label(
            input_row, 
            text=self.input_label, 
            width=14
        ).pack(side="left", padx=(6, 2), expand=False)

        ttk.Entry(input_row, textvariable=self.files_var).pack(
            side="left", padx=(2, 2), expand=True, fill="x"
        )
        ttk.Button(
            input_row,
            text="Browse...",
            command=self.browse_files,
        ).pack(side="left", padx=2)
        ttk.Button(
            input_row, text="Details...", command=self.show_file_list
        ).pack(side="left", padx=2)

        # Output directory
        output_row = ttk.Frame(frame)
        output_row.pack(fill="x", padx=0, pady=(2, 4))
        self.out_dir_var = tk.StringVar(value=self.default_output_dir)
        ttk.Label(
            output_row, 
            text=self.output_label, 
            width=14
        ).pack(side="left", padx=(6, 2), expand=False)
        self.out_dir_entry = ttk.Entry(output_row, textvariable=self.out_dir_var)
        self.out_dir_entry.pack(side="left", padx=(2, 2), expand=True, fill="x")
        self.out_dir_var.trace_add("write", self.shift_entry_to_end)
        self.shift_entry_to_end()
        
        ttk.Button(
            output_row, text="Select...", command=self.select_out_dir
        ).pack(side="left", padx=2)
        ttk.Button(
            output_row, text="Open...", command=self.open_out_dir
        ).pack(side="left", padx=2)

    def browse_files(self):
        """
        General file selection, supports multi-select, type filter, size limit.
        var: tk.StringVar bound variable
        filetypes: [('Images', '*.png;*.jpg'), ...]
        max_size_mb: max file size in MB, popup if exceeded
        multi: allow multi-select
        title: dialog title
        """
        dlg = filedialog.askopenfilenames if self.multiple_input_files else filedialog.askopenfilename
        sel = dlg(title=f"Select {self.input_label}", filetypes=self.input_filetypes)
        if not sel:
            return
        files = sel if isinstance(sel, (list, tuple)) else [sel]
        oversize = []
        if self.max_size_mb:
            for f in files:
                try:
                    if os.path.getsize(f) > self.max_size_mb * 1024 * 1024:
                        oversize.append(f)
                except Exception:
                    pass
        if oversize:
            self.logger.error(
                f"The following files exceed {self.max_size_mb}MB and will not be loaded:\n"
                + "\n".join(oversize)
            )
            files = [f for f in files if f not in oversize]
        if files:
            self.files_var.set("\n".join(files))

    def select_out_dir(self):
        sel = filedialog.askdirectory(title=f"Select {self.output_label}")
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


    def show_file_list(self):
        self.list_window.geometry(self.set_list_geometry())
        self.list_window.deiconify() 
        # Initialize size, scaling, and scrollbars
        self.refresh_file_list()

    
    def refresh_file_list(self, *args):
        # 当文件列表变化时，若详情窗口存在且未销毁，则刷新
        if hasattr(self, "file_details_frame") and hasattr(self, "list_window"):
            if self.list_window.winfo_exists():
                # 重新加载文件列表
                self.file_details_frame.populate_file_list(self.load_file_list())
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
            return []
        
    def shift_entry_to_end(self, *args):
        if not os.path.exists(self.out_dir_var.get()):
            os.makedirs(self.out_dir_var.get(), exist_ok=True)
        try:
            self.out_dir_entry.xview_moveto(1.0)
        except Exception:
            pass


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