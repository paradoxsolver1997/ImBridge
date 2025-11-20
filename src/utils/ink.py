"""Image enhancement utilities (refactored from enhance_img_300dpi.py).

Exports:
- enhance_image(input_image_path, output_image_path, target_dpi=300)
- enhance_contrast(PIL.Image) -> PIL.Image
- image_to_pdf(input_image_path, output_pdf_path)
- batch_enhance_jpgs(in_folder_path, out_folder_path)
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageChops
import numpy as np
import os
import tempfile
import xml.etree.ElementTree as ET
import shutil
import subprocess
from PyPDF2 import PdfReader, PdfWriter
import tempfile
from src.utils.converter import vector_to_bitmap
from PIL import Image

from src.utils.converter import remove_temp


def grayscale_image(
    in_path: str, out_path: str, log_fun=None, binarize: bool = False
) -> Image.Image:
    """
    Turn image into grayscale, with optional contrast enhancement and binarization.
    If the input has an alpha channel, it will be separated and restored at the end.
    """

    img = Image.open(in_path)

    is_bw = img.mode == "1" or (img.mode == "L" and set(img.getextrema()) <= {0, 255})
    if not is_bw:

        if img.mode == "RGBA":
            if log_fun:
                log_fun("  [contrast] split alpha channel")
            rgb = img.convert("RGB")
            alpha = img.getchannel("A")
        else:
            rgb = img
            alpha = None

        if log_fun:
            log_fun("  [contrast] convert to grayscale")
        img_gray = rgb.convert("L")
        img_array = np.array(img_gray, dtype=np.float32)

        if binarize:

            def sigmoid(x, threshold=220, gain=20):
                x = np.clip(x, 0, 255)
                x = 255 / (1 + np.exp(-gain * (x - threshold) / 255.0))
                x = x + 100
                x = np.clip(x, 0, 255)
                return x

            if log_fun:
                log_fun("  [contrast] apply sigmoid")
            enhanced_array = sigmoid(img_array)
            enhanced_array = np.clip(enhanced_array, 0, 255)
            # Binarization
            threshold = 128
            bw_array = (enhanced_array > threshold) * 255
            img_gray = Image.fromarray(bw_array.astype(np.uint8))
        else:
            img_gray = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))

        # Restore alpha channel
        if alpha is not None:
            img_gray = img_gray.convert("L")
            img_gray = Image.merge("LA", (img_gray, alpha))

        img_gray.save(out_path)
        if log_fun:
            log_fun(
                f"Grayscale {os.path.basename(in_path)} -> {os.path.basename(out_path)} completed."
            )
    else:
        img.save(out_path)
        if log_fun:
            log_fun(
                f"{os.path.basename(in_path)} is already grayscale. Directly copy to {os.path.basename(out_path)}."
            )

'''
def enhance_image(
    input_image_path: str, output_image_path: str, target_dpi: int = 300, log_fun=None
) -> None:
    if log_fun:
        log_fun(f"[enhance] open image: {input_image_path}")
    img = Image.open(input_image_path)
    original_dpi = img.info.get("dpi", (72, 72))[0]
    if log_fun:
        log_fun(f"[enhance] original size: {img.size}, dpi: {original_dpi}")
    img_smooth = scale_image(img, scale_factor=target_dpi / original_dpi, log_fun=log_fun)
    if log_fun:
        log_fun(f"[enhance] save to: {output_image_path}")
    img_contrasted = grayscale_image(img_smooth, log_fun=log_fun)
    img_contrasted.save(output_image_path)
    if log_fun:
        log_fun("[enhance] done")


def scale_image(
    in_path: str, out_path: str, scale_x: float = 1.0, scale_y: float = 1.0, log_fun=None, **kwargs
) -> None:
    img = Image.open(in_path)
    width, height = img.size
    new_width = int(width * scale_x)
    new_height = int(height * scale_y)
    return resize_image(in_path, out_path, new_width, new_height, log_fun=log_fun, **kwargs)
'''


'''
def save_with_enhance(img: Image.Image, filepath: str, dpi: int = 300):
    """
    Crop the signature and enhance the resolution, keeping the transparent background, and save as various bitmap formats (png/jpg/jpeg/bmp/tiff, etc.).
    img: PIL.Image (RGBA)
    filepath: Save path
    dpi: Target DPI
    """
    # Crop the blank area
    bg = Image.new("RGBA", img.size, (255, 255, 255, 0))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    cropped = img.crop(bbox) if bbox else img
    # Temporarily save the cropped image
    ext = os.path.splitext(filepath)[1].lower()
    if ext in [".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
        tmp_suffix = ext
    else:
        tmp_suffix = ".png"
    with tempfile.NamedTemporaryFile(suffix=tmp_suffix, delete=False) as tmp:
        tmp_path = tmp.name
        # jpg does not support alpha
        save_img = (
            cropped.convert("RGB") if ext in [".jpg", ".jpeg", ".bmp"] else cropped
        )
        save_img.save(tmp_path, format=ext.lstrip(".").upper() if ext else "PNG")
    # Call enhance to improve resolution
    enhance_image(tmp_path, filepath, target_dpi=dpi)
    os.remove(tmp_path)
'''


'''
def resize_vector(in_path: str, out_path: str, new_width: int, new_height: int, log_fun=None, **kwargs) -> None:
    """
    Resize vector file (SVG, PDF, EPS, PS) to new pixel size, output as PNG or PDF.
    Requires cairosvg (for SVG), PyPDF2 (for PDF), Ghostscript (for EPS/PS/PDF).
    """

    ext = os.path.splitext(in_path)[1].lower()
    # Check tool availability
    def check_tool(tool):
        return shutil.which(tool) is not None

    if ext == ".svg":
        resize_svg(in_path, out_path, log_fun=log_fun, **kwargs)
    elif ext == ".pdf":
        resize_pdf(in_path, out_path, log_fun=log_fun, **kwargs)
    elif ext in (".eps", ".ps"):
        resize_eps_ps(in_path, out_path, log_fun=log_fun, **kwargs)
    else:
        raise ValueError(f"Unsupported vector file type: {ext}")

    remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        
    if kwargs.get('preview_flag', True):
        # Convert out_path (vector) to bitmap for preview
        from src.utils.converter import vector_to_bitmap
        # vector_to_bitmap returns PIL.Image
        vector_to_bitmap(out_path)
        return Image.open(out_path)
    else:
        return None
'''



'''
def scale_vector(
    in_path: str, out_path: str, scale_x: float = 2.0, scale_y: float = 2.0, log_fun=None, **kwargs
) -> None:
    """
    Scale a vector file (SVG, PDF, EPS, PS) by a given factor.
    """
    # 读取原始宽高
    ext = os.path.splitext(in_path)[1].lower()
    new_width = None
    new_height = None
    if ext == ".svg":
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(in_path)
            root = tree.getroot()
            width = root.get("width")
            height = root.get("height")
            if width and height:
                new_width = int(float(width) * scale_x)
                new_height = int(float(height) * scale_y)
        except Exception:
            pass
    elif ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(in_path)
            page = reader.pages[0]
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            new_width = int(w * scale_factor)
            new_height = int(h * scale_factor)
        except Exception:
            pass
    # EPS/PS等，无法直接获取宽高，需用户保证
    if new_width is None or new_height is None:
        if 'orig_width' in kwargs and 'orig_height' in kwargs:
            new_width = int(kwargs['orig_width'] * scale_factor)
            new_height = int(kwargs['orig_height'] * scale_factor)
        else:
            raise ValueError("Cannot determine original size for vector file. Please provide orig_width and orig_height in kwargs.")
    return resize_vector(in_path, out_path, new_width, new_height, log_fun=log_fun, **kwargs)
'''