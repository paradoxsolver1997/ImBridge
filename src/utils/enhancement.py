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
    in_path: str, out_path: str, scale_factor: float = 2.0, log_fun=None, **kwargs
) -> None:
    img = Image.open(in_path)
    width, height = img.size
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    if scale_factor > 1.0: 
        return resize_image(in_path, out_path, new_width, new_height, enhance_flag=True, log_fun=log_fun, **kwargs)
    else:
        return resize_image(in_path, out_path, new_width, new_height, log_fun=log_fun, **kwargs)


def resize_image(
    in_path: str,
    out_path: str,
    new_width: int,
    new_height: int,
    enhance_flag: bool = False,
    log_fun=None,
    **kwargs
) -> None:

    img = Image.open(in_path)
    if log_fun:
        log_fun(f"[enhance] resize to: {(new_width, new_height)}")

    # Separate alpha channel
    if img.mode == "RGBA":
        rgb = img.convert("RGB")
        alpha = img.getchannel("A").resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )
        img_2 = rgb.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        img_2 = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        alpha = None

    if enhance_flag:
        if log_fun:
            log_fun("[enhance] sharpen")
        enhancer = ImageEnhance.Sharpness(img_2)
        img_2 = enhancer.enhance(kwargs.get('sharpness', 5.0))
        if log_fun:
            log_fun("[enhance] gaussian blur")
        img_2 = img_2.filter(ImageFilter.GaussianBlur(radius=kwargs.get('blur_radius', 1.0)))
        if log_fun:
            log_fun("[enhance] median filter")
        img_2 = img_2.filter(ImageFilter.MedianFilter(size=kwargs.get('median_size', 3)))
        if log_fun:
            log_fun("[enhance] enhance contrast")
        # Merge alpha channel
        if alpha is not None:
            img_2 = img_2.convert("RGBA")
            img_2.putalpha(alpha)
        if log_fun:
            log_fun("Upscale finished.")
    
    if kwargs.get('crop_flag', False):
        crop_box = (
            kwargs.get('crop_x', 0),
            kwargs.get('crop_y', 0),
            kwargs.get('crop_x', 0) + kwargs.get('crop_w', 0),
            kwargs.get('crop_y', 0) + kwargs.get('crop_h', 0),
        )
        if log_fun:
            log_fun(f"[resize] crop box: {crop_box}")
        img_2 = img_2.crop(crop_box)

    if kwargs.get('save_flag', True):
        img_2.save(out_path)
        if log_fun:
            log_fun(f"[enhance] saved to: {out_path}")

    if kwargs.get('preview_flag'):
        return img_2
    else:
        return None


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
        resize_svg(in_path, out_path, new_width, new_height, log_fun=log_fun, **kwargs)
    elif ext == ".pdf":
        resize_pdf(in_path, out_path, new_width, new_height, log_fun=log_fun, **kwargs)
    elif ext in (".eps", ".ps"):
        # --- Warn user about possible loss ---
        import tkinter.messagebox as messagebox
        proceed = messagebox.askyesno(
            "Format Conversion Warning",
            "Converting EPS/PS to PDF for cropping/resizing and then back to EPS/PS may cause loss of fidelity, features, or formatting. Do you want to continue?"
        )
        if not proceed:
            if log_fun:
                log_fun("[vector] EPS/PS conversion cancelled by user.")
            return
        # --- Use converter.py functions ---
        from src.utils.converter import ps_eps_to_pdf, pdf_to_eps, pdf_to_ps
        tmp_pdf = out_path + ".tmp.pdf"
        # 1. EPS/PS -> PDF
        ps_eps_to_pdf(in_path, tmp_pdf)
        # 2. Resize PDF (in place)
        resize_pdf(tmp_pdf, tmp_pdf, new_width, new_height, log_fun=log_fun, **kwargs)
        # 3. PDF -> EPS/PS
        out_ext = os.path.splitext(out_path)[1].lower()
        if out_ext == ".eps":
            pdf_to_eps(tmp_pdf, out_path)
        else:
            pdf_to_ps(tmp_pdf, out_path)
        if os.path.exists(tmp_pdf):
            os.remove(tmp_pdf)
        if log_fun:
            log_fun(f"[vector] EPS/PS converted via PDF and saved to {out_path}")
    else:
        raise ValueError(f"Unsupported vector file type: {ext}")

    # --- Preview and Save logic ---
    img = None
    if kwargs.get('preview_flag'):
        # Convert out_path (vector) to bitmap for preview
        from src.utils.converter import vector_to_bitmap
        # vector_to_bitmap returns PIL.Image
        img = vector_to_bitmap(out_path, width=new_width, height=new_height)
    if not kwargs.get('save_flag', True):
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception as e:
            if log_fun:
                log_fun(f"[vector] Failed to remove temp file {out_path}: {e}")
    if kwargs.get('preview_flag'):
        return img
    else:
        return None
    

def resize_svg(in_path: str, out_path: str, new_width: int, new_height: int, log_fun=None, **kwargs) -> None:
    crop_flag = kwargs.get('crop_flag', False)
    if crop_flag:
        x = kwargs.get('crop_x', 0)
        y = kwargs.get('crop_y', 0)
        w = kwargs.get('crop_w', 0)
        h = kwargs.get('crop_h', 0)

    try:
        tree = ET.parse(in_path)
        root = tree.getroot()
        svg_ns = "http://www.w3.org/2000/svg"
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0][1:]
        else:
            ns = svg_ns
        # 裁剪viewBox
        if crop_flag:
            if log_fun:
                log_fun(f"[vector] Cropping SVG viewBox to ({x},{y},{w},{h})")
            root.set("viewBox", f"{x} {y} {w} {h}")
            root.set("width", str(new_width))
            root.set("height", str(new_height))
        else:
            root.set("width", str(new_width))
            root.set("height", str(new_height))
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        if log_fun:
            log_fun(f"[vector] SVG saved to {out_path}")
    except Exception as e:
        raise RuntimeError(f"SVG crop/resize failed: {e}")

def resize_pdf(in_path: str, out_path: str, new_width: int, new_height: int, log_fun=None, **kwargs) -> None:

    crop_flag = kwargs.get('crop_flag', False)
    if crop_flag:
        x = kwargs.get('crop_x', 0)
        y = kwargs.get('crop_y', 0)
        w = kwargs.get('crop_w', 0)
        h = kwargs.get('crop_h', 0)
    # PDF: 用PyPDF2设置CropBox/MediaBox，保持为PDF输出
    try:
        reader = PdfReader(in_path)
        writer = PdfWriter()
        for page in reader.pages:
            if crop_flag:
                if log_fun:
                    log_fun(f"[vector] Cropping PDF to ({x},{y},{w},{h})")
                # 设置CropBox和MediaBox
                page.mediabox.lower_left = (x, y)
                page.mediabox.upper_right = (x + w, y + h)
                page.cropbox.lower_left = (x, y)
                page.cropbox.upper_right = (x + w, y + h)
            # 缩放：设置UserUnit或让用户用渲染器指定输出像素
            writer.add_page(page)
        with open(out_path, "wb") as f:
            writer.write(f)
        if log_fun:
            log_fun(f"[vector] PDF saved to {out_path}")
    except Exception as e:
        raise RuntimeError(f"PDF crop/resize failed: {e}")
    

def scale_vector(
    in_path: str, out_path: str, scale_factor: float = 2.0, log_fun=None, **kwargs
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
                new_width = int(float(width) * scale_factor)
                new_height = int(float(height) * scale_factor)
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
