import tkinter as tk
from tkinter import ttk
import os

from src.tabs.base_tab import BaseTab
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame
from src.frames.check_frame import CheckFrame
from src.utils.commons import bitmap_formats, vector_formats, script_formats
import src.utils.vector as vec
import src.utils.raster as rst
import src.utils.transformer as sc

class TransformTab(BaseTab):

    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "transform_output")
        self.mode_var = tk.IntVar(value=1)
        #self.mode_var.trace_add("write", lambda *args: self.on_transform())
        self.build_content()
        self.update_mode()

    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Transform Tool",
            comment_text="Rescale, flip, and rotate your image",
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
        self.io_frame.pack(padx=4, pady=(2, 4), fill="x")
        self.io_frame.files_var.trace_add("write", self.on_files_var_changed)
        

        option_row = ttk.LabelFrame(self, text="Rescale Options", style="Bold.TLabelframe")
        option_row.pack(padx=(8, 8), pady=(4, 4), fill="x")

        # Row 1: Mode Selection
        # The Upscale options
        frm_1 = ttk.Frame(option_row)
        frm_1.pack(side="left", padx=8, pady=0, fill="both",expand=True)
        
        ttk.Radiobutton(
            frm_1, 
            text='Original', 
            variable=self.mode_var, 
            value=1, 
            command=self.update_mode
        ).pack(side="left", padx=(6, 8))

        # The Upscale options
        frm_2 = ttk.Frame(option_row)
        frm_2.pack(side="left", padx=8, pady=0, fill="both",expand=True)
        
        ttk.Radiobutton(
            frm_2, 
            text='Scale', 
            variable=self.mode_var, 
            value=2, 
            command=self.update_mode
        ).pack(side="left", padx=(6, 8))
        
        self.scale_x_factor_var = tk.DoubleVar(value=1.0)
        #self.scale_x_factor_var.trace_add("write", lambda *args: self.on_transform())
        self.scale_x_factor_labeled_entry = LabeledValidatedEntry(
            frm_2,
            var=self.scale_x_factor_var,
            bounds=(0.001, 8.0),
            label_text="X",
            width=4,
        )
        self.scale_x_factor_labeled_entry.pack(side="left", padx=(4, 4))

        self.scale_y_factor_var = tk.DoubleVar(value=1.0)
        #self.scale_y_factor_var.trace_add("write", lambda *args: self.on_transform())
        self.scale_y_factor_labeled_entry = LabeledValidatedEntry(
            frm_2,
            var=self.scale_y_factor_var,
            bounds=(0.001, 8.0),
            label_text="Y",
            width=4,
        )
        self.scale_y_factor_labeled_entry.pack(side="left", padx=(4, 4))

        # The Upscale options
        frm_3 = ttk.Frame(option_row)
        frm_3.pack(side="left", padx=8, pady=0, fill="both",expand=True)

        self.resize_radio = ttk.Radiobutton(
            frm_3, 
            text='Resize (px)', 
            variable=self.mode_var, 
            value=3, 
            command=self.update_mode
        )
        self.resize_radio.pack(side="left", padx=(4, 4))

        row_2 = ttk.Frame(frm_3)
        row_2.pack(padx=(0, 0), pady=(4, 4), fill="x")

        self.width_var = tk.IntVar(value=1024)
        self.width_entry = LabeledValidatedEntry(
            row_2,
            var=self.width_var,
            bounds=(1, 65536),
            label_text="W",
            width=6,
        )
        self.width_entry.pack(side="left", padx=(6, 2))
        #self.width_entry.var.trace_add("write", lambda *args: self.on_transform())

        self.height_var = tk.IntVar(value=1024)
        self.height_entry = LabeledValidatedEntry(
            row_2,
            var=self.height_var,
            bounds=(1, 65536),
            label_text="H",
            width=6,
        )
        self.height_entry.pack(side="left", padx=(2, 2))
        #self.height_var.trace_add("write", lambda *args: self.on_transform())
        # Row 2: Settings

        parameter_row = ttk.Frame(self)
        parameter_row.pack(side="left", padx=(8, 8), pady=(4, 4), fill="both", expand=True)

        # The Parameter Settings
        upscale_frame = ttk.LabelFrame(parameter_row, text="Upscale Parameters", style="Bold.TLabelframe")
        upscale_frame.pack(side="left", padx=(0, 2), pady=0, fill="both", expand=True)

        self.sharpness_var = tk.DoubleVar(value=5.0)
        self.sharpness_entry = LabeledValidatedEntry(
            upscale_frame,
            var=self.sharpness_var,
            bounds=(0.0, 10.0),
            label_text="Sharpness",
            width=6,
        )
        self.sharpness_entry.pack(side="top", fill="x", padx=(8, 4), pady=(2, 1))

        self.blur_radius_var = tk.DoubleVar(value=1.0)
        self.blur_radius_entry = LabeledValidatedEntry(
            upscale_frame,
            var=self.blur_radius_var,
            bounds=(0.0, 10.0),
            label_text="Blur Radius",
            width=5,
        )
        self.blur_radius_entry.pack(side="top", fill="x", padx=(8, 4), pady=1)

        self.median_size_var = tk.IntVar(value=3)
        self.median_size_entry = LabeledValidatedEntry(
            upscale_frame,
            var=self.median_size_var,
            bounds=(1, 15),
            label_text="Median Size",
            width=4,
        )
        self.median_size_entry.pack(side="top", fill="x", padx=(8, 4), pady=1)

        flip_frame = ttk.LabelFrame(parameter_row, text="Flip", style="Bold.TLabelframe")
        flip_frame.pack(side="left", padx=8, pady=0, fill="both",expand=True)

        self.flip_horizontal_check = CheckFrame(flip_frame, title='Left-Right')
        self.flip_horizontal_check.pack(side="top", fill="x", padx=6, pady=(12,2))
        #self.flip_horizontal_check.var.trace_add("write", lambda *args: self.on_transform())

        self.flip_vertical_check = CheckFrame(flip_frame, title='Top-Bottom')
        self.flip_vertical_check.pack(side="top", anchor="w", padx=6, pady=(0,2))
        #self.flip_vertical_check.var.trace_add("write", lambda *args: self.on_transform())

        rotate_frame = ttk.LabelFrame(parameter_row, text="Rotate", style="Bold.TLabelframe")
        rotate_frame.pack(side="left", padx=8, pady=0, fill="both",expand=True)

        # 旋转角度下拉菜单
        self.rotate_angle_var = tk.IntVar(value=0)
        ttk.Label(rotate_frame, text="Angle [°]").pack(side="top", anchor="w", padx=6, pady=(4, 2))
        ttk.Label(rotate_frame, text="(anti-clockwise)").pack(side="top", anchor="w", padx=6, pady=(2, 6))
        self.rotate_angle_combo = ttk.Combobox(
            rotate_frame,
            textvariable=self.rotate_angle_var,
            values=[0, 90, 180, 270],
            state="readonly",
            width=6
        )
        self.rotate_angle_combo.pack(side="top", anchor="w", padx=6, pady=(0,8))
        #self.rotate_angle_var.trace_add("write", lambda *args: self.on_transform())

        control_frame = ttk.LabelFrame(parameter_row, text="Control", style="Bold.TLabelframe")
        control_frame.pack(side="left", padx=8, pady=0, fill="both",expand=True)

        # --- Preview 按钮 ---
        preview_btn_row = ttk.Frame(control_frame)
        preview_btn_row.pack(fill="x", padx=8, pady=(12, 6), anchor="e")
        ttk.Button(
            preview_btn_row,
            text="Preview",
            command=lambda: self.on_transform(save_flag=False)
        ).pack(padx=8)

        save_btn_row = ttk.Frame(control_frame)
        save_btn_row.pack(fill="x", padx=8, pady=(6, 12), anchor="e")
        ttk.Button(
            save_btn_row,
            text="Save",
            command=lambda: self.on_transform(save_flag=True)
        ).pack(padx=8)

    def update_mode(self):
        if self.mode_var.get() == 2:
            self.scale_x_factor_labeled_entry.activate()
            self.scale_y_factor_labeled_entry.activate()
            self.width_entry.deactivate()
            self.height_entry.deactivate()
        elif self.mode_var.get() == 3:
            self.scale_x_factor_labeled_entry.deactivate()
            self.scale_y_factor_labeled_entry.deactivate()
            self.width_entry.activate()
            self.height_entry.activate()
        else:
            self.scale_x_factor_labeled_entry.deactivate()
            self.scale_y_factor_labeled_entry.deactivate()
            self.width_entry.deactivate()
            self.height_entry.deactivate()


    def on_transform(self, save_flag=False):

        file_list = self.io_frame.load_file_list()
        if not file_list:
            # 这里可以弹窗、日志或直接 return
            return
        
        params = {
            "sharpness": self.sharpness_var.get(),
            "blur_radius": self.blur_radius_var.get(),
            "median_size": self.median_size_var.get(),
            "save_flag": save_flag,
            "preview_flag": True
        }
        
        if self.mode_var.get() == 2:
            params.update({
                "scale_x": self.scale_x_factor_var.get(),
                "scale_y": self.scale_y_factor_var.get(),
            })
        elif self.mode_var.get() == 3:
            params.update({
                "new_width": self.width_var.get(),
                "new_height": self.height_var.get(),
            })

        if self.rotate_angle_var.get() != 0:
            params.update({
                "rotate_angle": self.rotate_angle_var.get(),
            })

        if self.flip_horizontal_check.var.get():
            params.update({
                "flip_lr": True,
            })
        else:
            params.update({
                "flip_lr": False,
            })

        if self.flip_vertical_check.var.get():
            params.update({
                "flip_tb": True,
            })
        else:
            params.update({
                "flip_tb": False,
            })

        # 根据文件类型选择不同的resize方法
        in_path = file_list[0]
        ext = os.path.splitext(in_path)[1].lower()
        self.preview_frame.clear_preview()
        if ext in bitmap_formats:
            sc.transform_image(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                preview_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        elif ext == '.svg':
            params.update({"dpi": self.preview_frame.dpi})
            sc.transform_svg(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                preview_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        elif ext == '.pdf':
            params.update({"dpi": self.preview_frame.dpi})
            sc.transform_pdf(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                preview_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        elif ext in ['.eps', '.ps']:
            params.update({"dpi": self.preview_frame.dpi})
            sc.transform_script(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                preview_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        else:
            self.logger.error("Unsupported file format for resizing.")
        return


    def on_files_var_changed(self, *args):
        self.preview_frame.clear_preview()
        file = self.io_frame.files_var.get().strip().split("\n")[0]
        if file and os.path.isfile(file):
            ext = os.path.splitext(file)[1].lower()
            if ext in vector_formats:
                self.sharpness_entry.deactivate()
                self.blur_radius_entry.deactivate()
                self.median_size_entry.deactivate()
            else:
                self.sharpness_entry.activate()
                self.blur_radius_entry.activate()
                self.median_size_entry.activate()

            self.sharpness_entry.var.set(5.0)
            self.blur_radius_entry.var.set(1.0)
            self.median_size_entry.var.set(3)

            self.scale_x_factor_var.set(1.0)
            self.scale_y_factor_var.set(1.0)

            if ext == '.svg':
                sz = vec.get_svg_size(file)
            elif ext == '.pdf':
                sz = vec.get_pdf_size(file)
            elif ext in ['.eps', '.ps']:
                sz = vec.get_script_size(file)
            else:
                sz = rst.get_raster_size(file)
                
            self.width_entry.var.set(value=sz[0])
            self.height_entry.var.set(value=sz[1])

            unit = 'pt' if ext in script_formats else 'px'
            self.resize_radio.config(text=f'Resize ({unit})')

            if ext == '.pdf':
                self.flip_horizontal_check.deactivate()
                self.flip_vertical_check.deactivate()
            else:
                self.flip_horizontal_check.activate()
                self.flip_vertical_check.activate()
            self.flip_horizontal_check.var.set(False)
            self.flip_vertical_check.var.set(False)
            self.rotate_angle_var.set(0)
            
