import tkinter as tk
from tkinter import ttk
import os
from src.tabs.base_tab import BaseTab
from src.utils.ink import scale_image, resize_image
from src.frames.labeled_validated_entry import LabeledValidatedEntry
from src.frames.input_output_frame import InputOutputFrame
from src.frames.title_frame import TitleFrame

from PIL import Image


class ResizeVectorTab(BaseTab):

    def __init__(self, parent, title=None):
        super().__init__(parent, title=title)

        self._preview_imgtk = None
        self.output_dir = os.path.join(self.output_dir, "resize_output")
        self.mode_var = tk.IntVar(value=1)
        self.build_content()
        self.update_mode()

    def build_content(self):

        self.title_frame = TitleFrame(
            self,
            title_text="Resize & Crop Tool",
            comment_text="Quickly resize and crop your image",
        )
        self.title_frame.pack(padx=4, pady=(4, 2), fill="x")

        self.io_frame = InputOutputFrame(
            self,
            title="Resize Input/Output",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")],
            multi=False,
        )
        self.io_frame.pack(padx=4, pady=(4, 2), fill="x")

        self.io_frame.out_dir_var.set(value=self.output_dir)
        if not os.path.exists(self.io_frame.out_dir_var.get()):
            os.makedirs(self.io_frame.out_dir_var.get(), exist_ok=True)

        option_row = ttk.Frame(self)
        option_row.pack(padx=(0, 0), pady=(4, 4), fill="x")

        # Row 1: Mode Selection
        # The Upscale options
        frm_1 = ttk.LabelFrame(option_row, text="Option 1. Original", style="Bold.TLabelframe")
        frm_1.pack(side="left", padx=8, pady=8, fill="both",expand=True)
        
        ttk.Radiobutton(
            frm_1, 
            text='Original Size', 
            variable=self.mode_var, 
            value=1, 
            command=self.update_mode
        ).pack(side="left", padx=(6, 8))

        # The Upscale options
        frm_2 = ttk.LabelFrame(option_row, text="Option 2. Scale", style="Bold.TLabelframe")
        frm_2.pack(side="left", padx=8, pady=8, fill="both",expand=True)
        
        ttk.Radiobutton(
            frm_2, 
            text='Scale', 
            variable=self.mode_var, 
            value=2, 
            command=self.update_mode
        ).pack(side="left", padx=(6, 8))
        
        self.scale_factor_var = tk.DoubleVar(value=2.0)
        self.scale_factor_labeled_entry = LabeledValidatedEntry(
            frm_2,
            var=self.scale_factor_var,
            bounds=(1.0, 2.0),
            label_prefix="Factor",
            width=6,
        )
        self.scale_factor_labeled_entry.pack(side="left", padx=(6, 8))

        # The Upscale options
        frm_3 = ttk.LabelFrame(option_row, text="Option 3. Resize", style="Bold.TLabelframe")
        frm_3.pack(side="left", padx=8, pady=8, fill="both",expand=True)

        ttk.Radiobutton(
            frm_3, 
            text='Resize', 
            variable=self.mode_var, 
            value=3, 
            command=self.update_mode
        ).pack(side="left", padx=(6, 8))

        row_2 = ttk.Frame(frm_3)
        row_2.pack(padx=(0, 0), pady=(4, 4), fill="x")

        self.width_var = tk.IntVar(value=1024)
        self.width_entry = LabeledValidatedEntry(
            row_2,
            var=self.width_var,
            bounds=(1, 10000),
            label_prefix="Width",
            width=6,
        )
        self.width_entry.pack(side="left", padx=(6, 2))

        self.height_var = tk.IntVar(value=1024)
        self.height_entry = LabeledValidatedEntry(
            row_2,
            var=self.height_var,
            bounds=(1, 10000),
            label_prefix="Height",
            width=6,
        )
        self.height_entry.pack(side="left", padx=(2, 2))

        # Row 2: Settings

        parameter_row = ttk.Frame(self)
        parameter_row.pack(padx=(0, 0), pady=(4, 4), fill="x")

        # The Parameter Settings
        frm_4 = ttk.LabelFrame(parameter_row, text="Parameters", style="Bold.TLabelframe")
        frm_4.pack(side="left", padx=8, pady=8, fill="y",expand=True)

        self.sharpness_var = tk.DoubleVar(value=5.0)
        self.sharpness_entry = LabeledValidatedEntry(
            frm_4,
            var=self.sharpness_var,
            bounds=(0.0, 10.0),
            label_prefix="Sharpness",
            width=6,
        )
        self.sharpness_entry.pack(side="top", fill="x", padx=(2, 2))

        self.blur_radius_var = tk.DoubleVar(value=1.0)
        self.blur_radius_entry = LabeledValidatedEntry(
            frm_4,
            var=self.blur_radius_var,
            bounds=(0.0, 10.0),
            label_prefix="Blur Radius",
            width=6,
        )
        self.blur_radius_entry.pack(side="top", fill="x", padx=(2, 2))

        self.median_size_var = tk.IntVar(value=3)
        self.median_size_entry = LabeledValidatedEntry(
            frm_4,
            var=self.median_size_var,
            bounds=(1, 15),
            label_prefix="Median Size",
            width=6,
        )
        self.median_size_entry.pack(side="top", fill="x", padx=(2, 8))

        

        frm_5 = ttk.LabelFrame(parameter_row, text="Parameters", style="Bold.TLabelframe")
        frm_5.pack(side="left", padx=8, pady=8, fill="y",expand=True)

        # --- Crop 选项 ---
        crop_row = ttk.Frame(frm_5)
        crop_row.pack(side="top", fill="x", padx=4, pady=(4, 2))

        self.crop_flag_var = tk.BooleanVar(value=False)
        crop_check = ttk.Checkbutton(crop_row, text="Crop", variable=self.crop_flag_var)
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

        frm_6 = ttk.LabelFrame(parameter_row, text="Parameters", style="Bold.TLabelframe")
        frm_6.pack(side="left", padx=8, pady=8, fill="y",expand=True)

        # --- Preview 按钮 ---
        preview_btn_row = ttk.Frame(frm_6)
        preview_btn_row.pack(fill="x", padx=8, pady=(8, 12), anchor="e")
        ttk.Button(
            preview_btn_row,
            text="Preview",
            command=self.on_preview
        ).pack(side="right", padx=(2, 8))

        save_btn_row = ttk.Frame(frm_6)
        save_btn_row.pack(fill="x", padx=8, pady=(8, 12), anchor="e")
        ttk.Button(
            save_btn_row,
            text="Upscale & Save",
            command=lambda: self.batch_convert(
                mode="upscale",
                file_list=self.io_frame.files_var.get().strip().split("\n"),
                out_dir=self.io_frame.out_dir_var.get(),
                scale_factor=self.scale_factor_var.get()
            ),
        ).pack(side="left", padx=8)



    def update_mode(self):
        if self.mode_var.get() == 2:
            self.scale_factor_labeled_entry.activate()
            self.width_entry.deactivate()
            self.height_entry.deactivate()
        elif self.mode_var.get() == 3:
            self.scale_factor_labeled_entry.deactivate()
            self.width_entry.activate()
            self.height_entry.activate()
        else:
            self.scale_factor_labeled_entry.deactivate()
            self.width_entry.deactivate()
            self.height_entry.deactivate()


    def on_preview(self):

        file_list = self.io_frame.load_file_list()
        if not file_list:
            # 这里可以弹窗、日志或直接 return
            return
        img = Image.open(file_list[0])
        
        params = {
            "sharpness": self.sharpness_var.get(),
            "blur_radius": self.blur_radius_var.get(),
            "median_size": self.median_size_var.get(),
        }
        if self.mode_var.get() == 2:
            img = scale_image(
                img,
                scale_factor=self.scale_factor_var.get(),
                log_fun=self.logger.info,
                **params
            )
        elif self.mode_var.get() == 3:
            
            new_width = self.width_var.get()
            new_height = self.height_var.get()

            enhance_flag = new_width > img.width and new_height > img.height
            img = resize_image(
                img,
                width=new_width,
                height=new_height,
                enhance_flag=enhance_flag,
                log_fun=self.logger.info,
                **params
            )

        if self.crop_flag_var.get():
            crop_box = (
                self.crop_x_var.get(),
                self.crop_y_var.get(),
                self.crop_x_var.get() + self.crop_w_var.get(),
                self.crop_y_var.get() + self.crop_h_var.get(),
            )
            self.logger.info(f"[resize] crop box: {crop_box}")
            img = img.crop(crop_box)
        
        self.preview_frame.clear_preview()
        self.preview_frame.show_image(img)