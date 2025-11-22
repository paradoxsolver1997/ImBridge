from typing import Optional
from PIL import Image, ImageEnhance, ImageFilter
import os
import tempfile
import numpy as np

from src.utils.converter import vector_to_bitmap, remove_temp, wash_eps_ps, bmp_to_svg
from src.utils.commons import confirm_overwrite



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
    
    
def resize_eps_ps(
    in_path: str,
    out_path: str,
    log_fun=None,
    **kwargs
) -> None:
    """
    Resize or crop EPS/PS file by editing BoundingBox and HiResBoundingBox.
    逻辑：
      1. 用 wash_eps_ps 清洗文件（标准化 EPS/PS）
      2. 如果指定 crop_box，直接修改 %%BoundingBox 和 %%HiResBoundingBox
      3. 完全二进制安全，支持包含二进制数据的 EPS
      只支持裁剪，不支持缩放
    """
    import re
    from src.utils.converter import wash_eps_ps

    # 获取 crop_box
    crop_box = kwargs.get("crop_box", None)
    dpi = kwargs.get("dpi", None)

    # 1. 先用 wash_eps_ps 清洗，输出到 out_path
    wash_eps_ps(in_path, out_path)

    # 2. 如果有 crop_box，修改 BoundingBox
    if crop_box is not None:
        x0, y0, x1, y1 = crop_box

        # 二进制模式读取 EPS
        with open(out_path, "rb") as f:
            content = f.read()

        # bytes 正则，允许行首空格
        pattern_bbox = re.compile(br"^\s*(%%BoundingBox: )(-?\d+) (-?\d+) (-?\d+) (-?\d+)", re.MULTILINE)
        pattern_hires = re.compile(
            br"^\s*(%%HiResBoundingBox: )(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)",
            re.MULTILINE,
        )

        # 替换函数
        def repl_bbox(m):
            return b"%s%d %d %d %d" % (m.group(1), x0, y0, x1, y1)

        def repl_hires(m):
            return b"%s%.2f %.2f %.2f %.2f" % (m.group(1), float(x0), float(y0), float(x1), float(y1))

        content, n_bbox = pattern_bbox.subn(repl_bbox, content)
        content, n_hires = pattern_hires.subn(repl_hires, content)

        # 写回文件
        with open(out_path, "wb") as f:
            f.write(content)

        if log_fun:
            log_fun(f"Cropped BoundingBox to {x0} {y0} {x1} {y1} "
                    f"(bbox lines: {n_bbox}, hires lines: {n_hires})")
    else:
        # 未指定 crop_box，直接复制原文件
        if log_fun:
            log_fun(f"[vector] EPS/PS copied without crop, saved to {out_path}")

    # 可选生成预览图
    img = vector_to_image(out_path, dpi) if kwargs.get("preview_flag", True) else None
    # 如果不保存原文件，删除临时文件
    if not kwargs.get("save_flag", True):
        remove_temp(out_path)

    return img

        

# --- EPS/PS 直接缩放（修改scale和BoundingBox，无需格式转换） ---
def resize_eps_ps2(in_path: str, out_path: str, log_fun=None, **kwargs) -> None:
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
        
        crop_eps_ps_for_gs(in_path, out_path, crop_box, dpi, log_fun)
        
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

def crop_eps_ps(in_path: str, out_path: str, crop_box, dpi, log_fun=None):
    """
    彻底裁剪 EPS/PS 文件（真正修改绘图区域）
    crop_box: (left, top, right, bottom)  —— 像素坐标
    dpi: 输入图像的 DPI，用来换算 PS 点坐标
    """
    import re
    print("XXXXXXXXXXXXXXXX")
    # 读入 EPS
    with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 查找 BoundingBox
    bbox_pat = re.compile(r"^%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
    bbox_idx = None
    bbox_vals = None
    for idx, line in enumerate(lines):
        m = bbox_pat.match(line)
        if m:
            bbox_idx = idx
            bbox_vals = list(map(int, m.groups()))
            break

    if bbox_idx is None:
        raise ValueError("未找到 %%BoundingBox，无法裁剪 EPS/PS 文件。")

    # 像素坐标 → PS 坐标 (points)
    left, top, right, bottom = crop_box  # 像素坐标
    llx = left   / dpi * 72
    lly = bottom / dpi * 72
    urx = right  / dpi * 72
    ury = top    / dpi * 72

    # 新的 BoundingBox
    new_bbox_line = f"%%BoundingBox: {int(llx)} {int(lly)} {int(urx)} {int(ury)}\n"
    lines[bbox_idx] = new_bbox_line

    # 插入 PostScript 裁切命令：
    # 1. translate：将原点平移到裁剪框左下角
    # 2. rectclip：定义裁剪区域
    clip_width = urx - llx
    clip_height = ury - lly

    clip_code = f"""
    %%BeginCrop
    gsave
    {llx} {lly} translate
    0 0 {clip_width} {clip_height} rectclip
    %%EndCrop
    """

    # 在 %%EndComments 后插入裁剪
    insert_pos = None
    for idx, line in enumerate(lines):
        if line.startswith("%%EndComments"):
            insert_pos = idx + 1
            break

    # 如果找不到 EndComments，就在 BoundingBox 后插入
    if insert_pos is None:
        insert_pos = bbox_idx + 1

    lines.insert(insert_pos, clip_code)

    # 写新文件
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    if log_fun:
        log_fun(f"[vector] EPS/PS cropped with real clipping, saved to {out_path}")

    return out_path

def crop_eps_ps_for_gs(in_path, out_path, crop_box, dpi, log_fun=None):
    """
    彻底裁剪 EPS/PS，兼容 Ghostscript/GIMP/Inkscape/Illustrator。
    解决 rectclip 在 GS png 设备中不生效的问题。
    """
    import re

    with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 查找 BoundingBox
    bbox_pat = re.compile(r"^%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
    bbox_idx = None
    for i, line in enumerate(lines):
        m = bbox_pat.match(line)
        if m:
            bbox_idx = i
            break

    if bbox_idx is None:
        raise ValueError("No %%BoundingBox found")

    left, top, right, bottom = crop_box

    # convert pixel to points
    llx = left   / dpi * 72
    lly = bottom / dpi * 72
    urx = right  / dpi * 72
    ury = top    / dpi * 72

    new_bbox_line = f"%%BoundingBox: {int(llx)} {int(lly)} {int(urx)} {int(ury)}\n"
    lines[bbox_idx] = new_bbox_line

    width  = urx - llx
    height = ury - lly

    # 强制裁剪指令——Ghostscript 100% 处理 clip path
    clip_code = f"""
%%BeginCrop
gsave
{llx} {lly} translate
newpath
0 0 moveto
{width} 0 lineto
{width} {height} lineto
0 {height} lineto
closepath
clip
%%EndCrop
"""

    # 插到 EndComments 后面
    insert_idx = None
    for i, l in enumerate(lines):
        if l.startswith("%%EndComments"):
            insert_idx = i + 1
            break

    if insert_idx is None:
        insert_idx = bbox_idx + 1

    lines.insert(insert_idx, clip_code)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    if log_fun:
        log_fun("[vector] Cropped EPS written to " + out_path)

    return out_path


def vector_to_image(in_path: str, dpi: Optional[int] = None) -> Image.Image:
    img = None
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_png:
        png_path = tmp_png.name
    try:
        vector_to_bitmap(in_path, png_path, dpi=dpi)
        img = Image.open(png_path)
        img.load()  # 强制读取到内存
    finally:
        remove_temp(png_path)
    return img