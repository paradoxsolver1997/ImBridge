from typing import Optional
from PIL import Image, ImageEnhance, ImageFilter
import os
import tempfile
import numpy as np

from src.utils.converter import vector_to_bitmap, remove_temp



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
        return img_gray
    else:
        img.save(out_path)
        if log_fun:
            log_fun(
                f"{os.path.basename(in_path)} is already grayscale. Directly copy to {os.path.basename(out_path)}."
            )
        return img


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
    return img_2

def resize_svg(in_path: str, out_path: str, log_fun=None, **kwargs) -> None:
    
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(in_path)
        root = tree.getroot()
        width = int(float(root.get("width")))
        height = int(float(root.get("height")))
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")
    
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
            root.set("width", str(w))
            root.set("height", str(h))
        else:
            root.set("width", str(w))
            root.set("height", str(h))
        log_fun(f"[vector] Scaling SVG to ({w},{h})") if log_fun else None
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        log_fun(f"[vector] SVG saved to {out_path}") if log_fun else None
        img = vector_to_image(out_path) if kwargs.get('preview_flag', True) else None
        remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        return img

    except Exception as e:
        raise RuntimeError(f"SVG crop/resize failed: {e}")


def resize_pdf(in_path: str, out_path: str, log_fun=None, **kwargs) -> None:
    dpi = kwargs.get('dpi')
    # 用PyMuPDF整体缩放纯矢量PDF内容
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(in_path)
        new_doc = fitz.open()

        for page in doc:
            rect = page.rect
            orig_width = rect.width
            orig_height = rect.height
            # 计算缩放因子
 
            if 'new_width' in kwargs and 'new_height' in kwargs:
                target_width = float(kwargs['new_width']) / dpi * 72
                target_height = float(kwargs['new_height']) / dpi * 72
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
                target_width = orig_width
                target_height = orig_height
            mat = fitz.Matrix(scale_x, scale_y)

            new_page = new_doc.new_page(width=target_width, height=target_height)
            new_page.show_pdf_page(
                new_page.rect,  # 目标矩形
                doc,  # 源文档
                page.number,  # 源页码
                clip=None,  # 不裁剪
                rotate=0,  # 不旋转
                keep_proportion=False,  # 不保持比例(使用我们的缩放)
                overlay=True
            )

            # page.set_mediabox(fitz.Rect(0, 0, target_width, target_height))
            # 支持单独设置cropbox
            if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
                crop_box = kwargs['crop_box']
                # crop_box: (left, top, right, bottom)
                x = float(crop_box[0])  / dpi * 72
                y = float(crop_box[1])  / dpi * 72
                w = float(crop_box[2] - crop_box[0]) / dpi * 72
                h = float(crop_box[3] - crop_box[1]) / dpi * 72
                # page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                new_page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                if log_fun:
                    log_fun(f"[vector] Set cropbox to ({x},{y},{w},{h})")
            #else:
                #page.set_cropbox(fitz.Rect(0, 0, target_width, target_height))
            # page.get_pixmap(mat)
            if log_fun:
                log_fun(f"[vector] Page scaled: {orig_width}x{orig_height}pt -> {target_width}x{target_height}pt, scale=({scale_x:.2f},{scale_y:.2f})")
        new_doc.save(out_path)
        doc.close()
        new_doc.close()
        if log_fun:
            log_fun(f"[vector] PDF saved to {out_path}")
        img = vector_to_image(out_path, kwargs.get('dpi')) if kwargs.get('preview_flag', True) else None
        remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        return img
    except Exception as e:
        raise RuntimeError(f"PDF crop/resize failed: {e}")
    


# --- EPS/PS 直接缩放（修改scale和BoundingBox，无需格式转换） ---
def resize_eps_ps(in_path: str, out_path: str, log_fun=None, **kwargs) -> None:
    """
    直接对EPS/PS文件进行等比缩放：
    1. 解析并缩放%%BoundingBox
    2. 在PostScript主体前插入scale操作符
    3. 写入新文件
    """
    dpi = kwargs.get('dpi')
    import re
    with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    # 查找并解析BoundingBox
    bbox_pat = re.compile(r"^%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
    bbox_idx = None
    for idx, line in enumerate(lines):
        m = bbox_pat.match(line)
        if m:
            bbox_idx = idx
            break
    # 仅支持crop_box裁剪
    if 'crop_box' in kwargs and kwargs['crop_box'] is not None and dpi:
        crop_box = kwargs['crop_box']
        # crop_box: (left, top, right, bottom)
        new_llx = float(crop_box[0]) / dpi * 72
        new_lly = float(crop_box[1]) / dpi * 72
        new_urx = float(crop_box[2]) / dpi * 72
        new_ury = float(crop_box[3]) / dpi * 72
        new_bbox = f"%%BoundingBox: {int(new_llx)} {int(new_lly)} {int(new_urx)} {int(new_ury)}\n"
        lines[bbox_idx] = new_bbox
        # 不再插入scale操作符
        # 写入新文件
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        log_fun(f"[vector] EPS/PS cropped to BoundingBox {new_bbox.strip()}, saved to {out_path}") if log_fun else None
        img = vector_to_image(out_path, kwargs.get('dpi')) if kwargs.get('preview_flag', True) else None
        remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        return img
    else:
        # 未指定crop_box，直接复制原文件
        with open(out_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        log_fun(f"[vector] EPS/PS copied without crop, saved to {out_path}") if log_fun else None
        img = vector_to_image(out_path, kwargs.get('dpi')) if kwargs.get('preview_flag', True) else None
        remove_temp(out_path) if not kwargs.get('save_flag', True) else None
        return img


def vector_to_image(in_path: str, dpi: Optional[int] = None) -> Image.Image:
    img = None
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_png:
        png_path = tmp_png.name
    try:
        vector_to_bitmap(in_path, png_path, dpi=dpi)
        img = Image.open(png_path)
        img.load()  # 强制读取到内存
    finally:
        if os.path.exists(png_path):
            os.remove(png_path)
    return img