import tkinter as tk
import os
from PIL import Image, ImageTk
import logging
import tempfile
from src.utils import converter


def file_preview(img_path):
    try:
        ext = os.path.splitext(img_path)[1].lower()
        # Support vector preview: svg/pdf/eps/ps

        if ext in (".svg", ".pdf", ".eps", ".ps"):
            self.log("Vector file detected, converting to bitmap for preview...")
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as tmp_png:
                png_path = tmp_png.name
            try:
                converter.vector_to_bitmap(img_path, png_path, dpi=60)
                with Image.open(png_path) as img:
                    img.thumbnail((100, 100))
            except Exception as ve:
                raise
            finally:
                if os.path.exists(png_path):
                    os.remove(png_path)
        else:
            img = Image.open(img_path)
        self.log("Displaying preview image...")
        self.image_preview(img)
    except Exception as e:
        self.winfo_toplevel().clear_preview()
        if self.preview_frame:
            tk.Label(self.preview_frame, text="No Preview Available").pack(
                expand=True
            )

def image_preview(img):
    """
    Display imgtk in preview_frame and keep reference to prevent GC.
    """

    try:
        img.thumbnail((100, 100))
        imgtk = ImageTk.PhotoImage(img)
        label = tk.Label(self.preview_frame, image=imgtk)
        label.image = imgtk
        label.pack(expand=True)
    except Exception as e:
        tk.Label(self.preview_frame, text="Preview failed").pack(expand=True)