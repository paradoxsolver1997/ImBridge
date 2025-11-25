import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
import src.utils.cropper as cr
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame
from src.utils.commons import bitmap_formats, script_formats
from src.utils.commons import get_script_size, get_svg_size, get_raster_size


class CropTab(BaseTab):

    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "crop_output")
        self.mode_var = tk.IntVar(value=1)
        self.build_content()
        self.on_files_var_changed()
        self.on_crop(save_flag=False)

    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Crop Tool",
            comment_text="Quickly crop your image with preview",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")

        input_filetypes=[
                ("Images & Vectors", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.svg;*.pdf;*.eps;*.ps"),
                ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff"),
                ("Vectors", "*.svg;*.pdf;*.eps;*.ps"),
            ]
        parameters = {
            "input_label": "Input Image",
            "input_filetypes": input_filetypes,
            "multiple_input_files": False,
            "output_label": "Output Folder",
            "default_output_dir": self.output_dir,
        }

        self.io_frame = InputOutputFrame(self, title="Input-Output Settings", **parameters)
        self.io_frame.pack(padx=4, pady=(4, 2), fill="x")
        self.io_frame.files_var.trace_add("write", self.on_files_var_changed)
        
        # Row 2: Settings

        parameter_row = ttk.Frame(self)
        parameter_row.pack(padx=(0, 0), pady=(4, 4), fill="x")

        frm_5 = ttk.LabelFrame(parameter_row, text="Parameters", style="Bold.TLabelframe")
        frm_5.pack(side="left", padx=8, pady=8, fill="x", expand=True)

        cord_row = ttk.Frame(frm_5)
        cord_row.pack(side="left", fill="x", padx=(6, 8), pady=(4, 8), expand=True)

        self.crop_x_var = tk.IntVar(value=0)
        self.crop_x_entry = LabeledValidatedEntry(
            cord_row,
            var=self.crop_x_var,
            bounds=(0, 65535),
            label_text="X",
            width=5,
        )
        self.crop_x_entry.pack(side="left", padx=(2, 2))
        self.crop_x_entry.entry.bind("<FocusOut>", lambda e: self.on_crop(save_flag=False))

        self.crop_y_var = tk.IntVar(value=0)
        self.crop_y_entry = LabeledValidatedEntry(
            cord_row,
            var=self.crop_y_var,
            bounds=(0, 65535),
            label_text="Y",
            width=5,
        )
        self.crop_y_entry.pack(side="left", padx=(2, 2))
        self.crop_y_entry.entry.bind("<FocusOut>", lambda e: self.on_crop(save_flag=False))

        self.crop_w_var = tk.IntVar(value=1)
        self.crop_w_entry = LabeledValidatedEntry(
            cord_row,
            var=self.crop_w_var,
            bounds=(1, 65536),
            label_text="W",
            width=5,
        )
        self.crop_w_entry.pack(side="left", padx=(2, 2))
        self.crop_w_entry.entry.bind("<FocusOut>", lambda e: self.on_crop(save_flag=False))

        self.crop_h_var = tk.IntVar(value=1)
        self.crop_h_entry = LabeledValidatedEntry(
            cord_row,
            var=self.crop_h_var,
            bounds=(1, 65536),
            label_text="H",
            width=5,
        )
        self.crop_h_entry.pack(side="left", padx=(2, 2))
        self.crop_h_entry.entry.bind("<FocusOut>", lambda e: self.on_crop(save_flag=False))

        ttk.Button(
            cord_row,
            text="Confirm",
            command=lambda: self.on_crop(save_flag=False)
        ).pack(side="left", padx=(2, 8))

        ttk.Button(
            cord_row,
            text="Save",
            command=lambda: self.on_crop(save_flag=True)
        ).pack(side="right", fill='x', padx=8)


    def on_crop(self, save_flag=False):

        file_list = self.io_frame.load_file_list()
        if not file_list:
            # 这里可以弹窗、日志或直接 return
            return
        
        crop_box = (
            self.crop_x_var.get(),
            self.crop_y_var.get(),
            self.crop_x_var.get() + self.crop_w_var.get(),
            self.crop_y_var.get() + self.crop_h_var.get(),
        )

        # 根据文件类型选择不同的resize方法
        in_path = file_list[0]
        ext = os.path.splitext(in_path)[1].lower()
        self.preview_frame.clear_preview()
        params = {
            "dpi": self.preview_frame.dpi
        }
        if ext in bitmap_formats:
            cr.crop_image(
                in_path, 
                self.io_frame.out_dir_var.get(),
                crop_box=crop_box,
                save_image=save_flag,
                image_preview_callback=self.preview_frame.show_image, 
                logger=self.logger
            )
        elif ext == '.svg':
            cr.crop_svg(
                in_path, 
                self.io_frame.out_dir_var.get(),
                crop_box=crop_box,
                save_image=save_flag,
                file_preview_callback=self.preview_frame.show_file, 
                logger=self.logger
            )
        elif ext == '.pdf':
            cr.crop_pdf(
                in_path, 
                self.io_frame.out_dir_var.get(),
                crop_box=crop_box,
                save_image=save_flag,
                file_preview_callback=self.preview_frame.show_file, 
                logger=self.logger,
                kwargs=params
            )
        elif ext in ['.eps', '.ps']:
            cr.crop_script(
                in_path, 
                self.io_frame.out_dir_var.get(),
                crop_box=crop_box,
                save_image=save_flag,
                file_preview_callback=self.preview_frame.show_file, 
                logger=self.logger,
                kwargs=params
            )
        else:
            self.logger.error("Unsupported file format for resizing.")
        return


    def on_files_var_changed(self, *args):
        file = self.io_frame.files_var.get().strip().split("\n")[0]
        if file:
            self.io_frame.show_file_list()
            ext = os.path.splitext(file)[1].lower()

            unit = 'pt' if ext in script_formats else 'px'
            self.crop_w_entry.label.config(text=f"W ({unit})")
            self.crop_h_entry.label.config(text=f"H ({unit})")
            self.crop_x_entry.label.config(text=f"X ({unit})")
            self.crop_y_entry.label.config(text=f"Y ({unit})")

            if ext == '.svg':
                sz = get_svg_size(file)
            elif ext in script_formats:
                sz = get_script_size(file)
            else:
                sz = get_raster_size(file)

            self.crop_x_var.set(value=0)
            self.crop_y_var.set(value=0)
            self.crop_w_var.set(value=int(sz[0]))
            self.crop_h_var.set(value=int(sz[1]))
            self.on_crop(save_flag=False)