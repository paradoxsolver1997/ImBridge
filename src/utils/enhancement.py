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

def resize_image(
    in_path: str, out_path: str, log_fun=None, **kwargs
) -> None:

    # 自动获取目标尺寸
    img = Image.open(in_path)
    if 'new_width' in kwargs and 'new_height' in kwargs:
        new_width = int(kwargs['new_width'])
        new_height = int(kwargs['new_height'])
    elif 'scale_x' in kwargs and 'scale_y' in kwargs:
        scale_x = float(kwargs['scale_x'])
        scale_y = float(kwargs['scale_y'])
        new_width = int(img.width * scale_x)
        new_height = int(img.height * scale_y)
    else:
        new_width = img.width
        new_height = img.height

    img = resize_raster(
        img,
        new_width,
        new_height,
        log_fun=log_fun,
        **kwargs)
    
    if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
        crop_box = kwargs['crop_box']
        if log_fun:
            log_fun(f"[resize] crop box: {crop_box}")
        img = img.crop(crop_box)

    if kwargs.get('save_flag', True):
        img.save(out_path)
        if log_fun:
            log_fun(f"[enhance] saved to: {out_path}")
    if kwargs.get('preview_flag', True):
        return img
    else:
        return None


def resize_raster(
    img: Image.Image,
    new_width: int,
    new_height: int,
    log_fun=None,
    **kwargs):
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

    if new_height > img.height and new_width > img.width:
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

def resize_svg(in_path: str, out_path: str, log_fun=None, **kwargs) -> None:
    
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(in_path)
        root = tree.getroot()
        width = int(float(root.get("width")))
        height = int(float(root.get("height")))
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")

    if 'new_width' in kwargs and 'new_height' in kwargs:
        new_width = int(kwargs['new_width'])
        new_height = int(kwargs['new_height'])
        scale_x = new_width / width
        scale_y = new_height / height
    elif 'scale_x' in kwargs and 'scale_y' in kwargs:
        scale_x = float(kwargs['scale_x'])
        scale_y = float(kwargs['scale_y'])
        new_width = int(width * scale_x)
        new_height = int(height * scale_y)
    else:
        scale_x = 1.0
        scale_y = 1.0
        new_width = width
        new_height = height
    
    try:
        svg_ns = "http://www.w3.org/2000/svg"
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0][1:]
        else:
            ns = svg_ns
        # 裁剪viewBox
        if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
            crop_box = kwargs['crop_box']
            # crop_box: (left, top, right, bottom)
            x = crop_box[0]
            y = crop_box[1]
            w = crop_box[2] - crop_box[0]
            h = crop_box[3] - crop_box[1]
            if log_fun:
                log_fun(f"[vector] Cropping SVG viewBox to ({x},{y},{w},{h})")
            root.set("viewBox", f"{x} {y} {w} {h}")
            root.set("width", str(new_width))
            root.set("height", str(new_height))
        else:
            root.set("width", str(new_width))
            root.set("height", str(new_height))
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        log_fun(f"[vector] SVG saved to {out_path}") if log_fun else None
        img = vector_to_image(out_path) if kwargs.get('preview_flag', True) else None
        remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        return img

    except Exception as e:
        raise RuntimeError(f"SVG crop/resize failed: {e}")


def resize_pdf(in_path: str, out_path: str, new_width: int, new_height: int, log_fun=None, **kwargs) -> None:

    # 用PyMuPDF整体缩放纯矢量PDF内容
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(in_path)
        for page in doc:
            rect = page.rect
            orig_width = rect.width
            orig_height = rect.height
            # 计算缩放因子
            if 'new_width' in kwargs and 'new_height' in kwargs:
                target_width = float(kwargs['new_width'])
                target_height = float(kwargs['new_height'])
                scale_x = target_width / orig_width
                scale_y = target_height / orig_height
            elif 'scale_x' in kwargs and 'scale_y' in kwargs:
                scale_x = float(kwargs['scale_x'])
                scale_y = float(kwargs['scale_y'])
                target_width = orig_width * scale_x
                target_height = orig_height * scale_y
            else:
                scale_x = 1.0
                scale_y = 1.0
                target_width = new_width
                target_height = new_height
            mat = fitz.Matrix(scale_x, scale_y)
            page.set_mediabox(fitz.Rect(0, 0, target_width, target_height))
            # 支持单独设置cropbox
            if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
                crop_box = kwargs['crop_box']
                # crop_box: (left, top, right, bottom)
                x = float(crop_box[0])
                y = float(crop_box[1])
                w = float(crop_box[2]) - float(crop_box[0])
                h = float(crop_box[3]) - float(crop_box[1])
                page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                if log_fun:
                    log_fun(f"[vector] Set cropbox to ({x},{y},{w},{h})")
            else:
                page.set_cropbox(fitz.Rect(0, 0, target_width, target_height))
            page.apply_transform(mat)
            if log_fun:
                log_fun(f"[vector] Page scaled: {orig_width}x{orig_height}pt -> {target_width}x{target_height}pt, scale=({scale_x:.2f},{scale_y:.2f})")
        doc.save(out_path)
        if log_fun:
            log_fun(f"[vector] PDF saved to {out_path}")
        img = vector_to_image(out_path) if kwargs.get('preview_flag', True) else None
        remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        return img
    except Exception as e:
        raise RuntimeError(f"PDF crop/resize failed: {e}")
    


# --- EPS/PS 直接缩放（修改scale和BoundingBox，无需格式转换） ---
def resize_eps_ps(in_path: str, out_path: str, log_fun=None):
    """
    直接对EPS/PS文件进行等比缩放：
    1. 解析并缩放%%BoundingBox
    2. 在PostScript主体前插入scale操作符
    3. 写入新文件
    """
    import re
    with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    # 查找并解析BoundingBox
    bbox_pat = re.compile(r"^%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
    bbox_idx = None
    bbox_vals = None
    for idx, line in enumerate(lines):
        m = bbox_pat.match(line)
        if m:
            bbox_idx = idx
            bbox_vals = [int(m.group(i)) for i in range(1, 5)]
            break
    if bbox_vals is None:
        raise ValueError("No %%BoundingBox found in EPS/PS file.")
    llx, lly, urx, ury = bbox_vals
    width = urx - llx
    height = ury - lly
    # 计算缩放因子
    import math
    import sys
    kwargs = locals().get('kwargs', {})
    if 'new_width' in kwargs and 'new_height' in kwargs:
        new_width = int(kwargs['new_width'])
        new_height = int(kwargs['new_height'])
        scale_x = new_width / width if width != 0 else 1.0
        scale_y = new_height / height if height != 0 else 1.0
    elif 'scale_x' in kwargs and 'scale_y' in kwargs:
        scale_x = float(kwargs['scale_x'])
        scale_y = float(kwargs['scale_y'])
        new_width = int(width * scale_x)
        new_height = int(height * scale_y)
    else:
        scale_x = 1.0
        scale_y = 1.0
        new_width = width
        new_height = height
    # 计算新BoundingBox
    new_llx = int(llx * scale_x)
    new_lly = int(lly * scale_y)
    new_urx = int(urx * scale_x)
    new_ury = int(ury * scale_y)
    new_bbox = f"%%BoundingBox: {new_llx} {new_lly} {new_urx} {new_ury}\n"
    # 替换BoundingBox
    lines[bbox_idx] = new_bbox
    # 查找插入点：通常在%%EndComments后或%%EndProlog后插入scale
    insert_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("%%EndProlog"):
            insert_idx = idx + 1
            break
    if insert_idx is None:
        for idx, line in enumerate(lines):
            if line.strip().startswith("%%EndComments"):
                insert_idx = idx + 1
                break
    if insert_idx is None:
        # fallback: after BoundingBox
        insert_idx = bbox_idx + 1
    # scale操作符
    scale_cmd = f"{scale_x} {scale_y} scale\n"
    lines.insert(insert_idx, scale_cmd)
    # 写入新文件
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    log_fun(f"[vector] EPS/PS scaled by ({scale_x},{scale_y}), BoundingBox updated to {new_bbox.strip()}, saved to {out_path}") if log_fun else None
    img = vector_to_image(out_path) if kwargs.get('preview_flag', True) else None
    remove_temp(out_path) if not kwargs.get('save_flag', True) else None
    return img

def vector_to_image(in_path: str):
    img = None
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_png:
        png_path = tmp_png.name
    try:
        vector_to_bitmap(in_path, png_path)
        img = Image.open(png_path)
        img.load()  # 强制读取到内存
    finally:
        if os.path.exists(png_path):
            os.remove(png_path)
    return img


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