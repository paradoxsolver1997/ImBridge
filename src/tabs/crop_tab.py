import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
import src.utils.scaler as sc
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame
from src.utils.commons import bitmap_formats


class CropTab(BaseTab):

    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "transform_output")
        self.mode_var = tk.IntVar(value=1)
        self.build_content()


    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Resize & Crop Tool",
            comment_text="Quickly resize and crop your image",
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

        self.io_frame = InputOutputFrame(self, **parameters)
        self.io_frame.pack(padx=4, pady=(4, 2), fill="x")
        '''
        self.io_frame.files_var.trace_add("write", self.on_files_var_changed)
        '''

        # Row 2: Settings

        parameter_row = ttk.Frame(self)
        parameter_row.pack(padx=(0, 0), pady=(4, 4), fill="x")

        frm_5 = ttk.LabelFrame(parameter_row, text="Parameters", style="Bold.TLabelframe")
        frm_5.pack(side="left", padx=8, pady=8, fill="y",expand=True)

        # --- Crop 选项 ---
        crop_row = ttk.Frame(frm_5)
        crop_row.pack(side="top", fill="x", padx=4, pady=(4, 2))

        self.crop_flag_var = tk.BooleanVar(value=False)
        crop_check = ttk.Checkbutton(crop_row, text="Crop after Resize", variable=self.crop_flag_var)
        crop_check.pack(side="left", padx=(0, 8))

        cord_row = ttk.Frame(frm_5)
        cord_row.pack(side="top", fill="x", padx=4, pady=(4, 2))

        self.crop_x_var = tk.IntVar(value=0)
        self.crop_x_entry = LabeledValidatedEntry(
            cord_row,
            var=self.crop_x_var,
            bounds=(0, 10000),
            label_prefix="X",
            width=5,
        )
        self.crop_x_entry.pack(side="left", padx=(2, 2))

        self.crop_y_var = tk.IntVar(value=0)
        self.crop_y_entry = LabeledValidatedEntry(
            cord_row,
            var=self.crop_y_var,
            bounds=(0, 10000),
            label_prefix="Y",
            width=5,
        )
        self.crop_y_entry.pack(side="left", padx=(2, 2))

        size_row = ttk.Frame(frm_5)
        size_row.pack(side="top", fill="x", padx=4, pady=(4, 2))

        self.crop_w_var = tk.IntVar(value=100)
        self.crop_w_entry = LabeledValidatedEntry(
            size_row,
            var=self.crop_w_var,
            bounds=(1, 10000),
            label_prefix="W",
            width=5,
        )
        self.crop_w_entry.pack(side="left", padx=(2, 2))

        self.crop_h_var = tk.IntVar(value=100)
        self.crop_h_entry = LabeledValidatedEntry(
            size_row,
            var=self.crop_h_var,
            bounds=(1, 10000),
            label_prefix="H",
            width=5,
        )
        self.crop_h_entry.pack(side="left", padx=(2, 2))

        

        frm_7 = ttk.LabelFrame(parameter_row, text="Parameters", style="Bold.TLabelframe")
        frm_7.pack(side="left", padx=8, pady=8, fill="y",expand=True)

        # --- Preview 按钮 ---
        preview_btn_row = ttk.Frame(frm_7)
        preview_btn_row.pack(fill="x", padx=8, pady=(8, 12), anchor="e")
        ttk.Button(
            preview_btn_row,
            text="Preview",
            command=lambda: self.on_resize(save_flag=False)
        ).pack(side="right", padx=(2, 8))

        save_btn_row = ttk.Frame(frm_7)
        save_btn_row.pack(fill="x", padx=8, pady=(8, 12), anchor="e")
        ttk.Button(
            save_btn_row,
            text="Save",
            command=lambda: self.on_resize(save_flag=True)
        ).pack(side="left", padx=8)


    '''
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


    def on_resize(self, save_flag=False):

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
        if self.crop_flag_var.get():
            params.update({
                "crop_box": (
                    self.crop_x_var.get(),
                    self.crop_y_var.get(),
                    self.crop_x_var.get() + self.crop_w_var.get(),
                    self.crop_y_var.get() + self.crop_h_var.get(),
                )
            })

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

        if self.flip_horizontal_var.get():
            params.update({
                "flip_lr": True,
            })
        else:
            params.update({
                "flip_lr": False,
            })

        if self.flip_vertical_var.get():
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
                project_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        elif ext == '.svg':
            sc.transform_svg(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                project_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        elif ext == '.pdf':
            params.update({"dpi": self.preview_frame.dpi})
            sc.transform_pdf(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                project_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        elif ext in ['.eps', '.ps']:
            params.update({"dpi": self.preview_frame.dpi})
            sc.transform_eps_ps(
                in_path, 
                self.io_frame.out_dir_var.get(),
                save_image=save_flag,
                project_callback=self.preview_frame.show_image, 
                logger=self.logger, 
                **params)
        else:
            self.logger.error("Unsupported file format for resizing.")
        return

        

    def on_files_var_changed(self, *args):
        files = self.io_frame.files_var.get().strip().split("\n")
        files = [f for f in files if f.strip()]
        vector_exts = ('.svg', '.pdf', '.eps', '.ps')
        is_vector = False
        if files:
            # 只要有一个是矢量图就算矢量
            for f in files:
                if f.lower().endswith(vector_exts):
                    is_vector = True
                    break
        if is_vector:
            self.sharpness_entry.deactivate()
            self.blur_radius_entry.deactivate()
            self.median_size_entry.deactivate()
        else:
            self.sharpness_entry.activate()
            self.blur_radius_entry.activate()
            self.median_size_entry.activate()
        '''