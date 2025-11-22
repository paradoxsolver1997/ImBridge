from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import os
import tempfile
import re
import fitz  # PyMuPDF
import shutil
import xml.etree.ElementTree as ET

from src.utils.logger import Logger
import src.utils.converter as cv

from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_single_page
from src.utils.commons import confirm_dir_existence
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_cropbox
from src.utils.commons import get_ps_size_pt


def crop_image(
    in_path: str,
    out_path: str,
    show_image: bool = False,
    save_image: bool = True,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:

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

    img = resize_raster(img, (new_width, new_height), logger=logger, **kwargs)
    crop_box = kwargs.get('crop_box', None)
    if crop_box is not None and confirm_cropbox(crop_box, (img.width, img.height)):
        logger.info(f"[crop] crop box: {crop_box}") if logger else None
        img = img.crop(crop_box)
    img.save(out_path) if save_image else out_path = None
    msg = f"[crop] saved to: {out_path}" if save_image else "[crop] image cropped without saving"
    logger.info(msg) if logger else None
    img = img if show_image else None
    return out_path, img


def resize_raster(
    img: Image.Image,
    new_size: Tuple[int, int],
    logger: Optional[Logger] = None,
    **kwargs
) -> Image.Image:
    """Crop and enhance raster image."""
    new_width, new_height = new_size
    logger.info(f"[enhance] resize to: {(new_width, new_height)}") if logger else None

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
        logger.info("[enhance] sharpen") if logger else None
        enhancer = ImageEnhance.Sharpness(img_2)
        img_2 = enhancer.enhance(kwargs.get('sharpness', 5.0))
        logger.info("[enhance] gaussian blur") if logger else None
        img_2 = img_2.filter(ImageFilter.GaussianBlur(radius=kwargs.get('blur_radius', 1.0)))
        logger.info("[enhance] median filter") if logger else None
        img_2 = img_2.filter(ImageFilter.MedianFilter(size=kwargs.get('median_size', 3)))
        logger.info("[enhance] enhance contrast") if logger else None
        # Merge alpha channel
        if alpha is not None:
            img_2 = img_2.convert("RGBA")
            img_2.putalpha(alpha)
        logger.info("Upscale finished.") if logger else None
    return img_2


def crop_svg(
    in_path: str,
    out_dir: str,
    show_image: bool = False,
    save_image: bool = True,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    try:
        tree = ET.parse(in_path)
        root = tree.getroot()
        width = int(float(root.get("width")))
        height = int(float(root.get("height")))
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")
    
    try:
        crop_box = kwargs.get('crop_box', None)
        if crop_box is not None and confirm_cropbox(crop_box, (width, height)):
            # crop_box: (left, top, right, bottom)
            x = crop_box[0]
            y = crop_box[1]
            w = crop_box[2] - crop_box[0]
            h = crop_box[3] - crop_box[1]
            if logger:
                logger.info(f"[vector] Cropping SVG viewBox to ({x},{y},{w},{h})")
            root.set("viewBox", f"{x} {y} {w} {h}")
            root.set("width", str(w))
            root.set("height", str(h))
        else:
            root.set("width", str(w))
            root.set("height", str(h))
        logger.info(f"[vector] Scaling SVG to ({w},{h})") if logger else None
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, "temp.svg")
            tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
            img = cv.svg2raster(tmp_path) if show_image else None
            shutil.move(tmp_path, out_path) if save_image else out_path = None
            msg = f"[vector] SVG saved to {out_path}" if save_image else "[vector] SVG resized without saving"
            logger.info(msg) if logger else None
        return out_path, img
    except Exception as e:
        raise RuntimeError(f"SVG crop/resize failed: {e}")


def crop_pdf(
    in_path: str,
    out_dir: str,
    show_image: bool = False,
    save_image: bool = True,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
        dpi = kwargs.get('dpi')
        # 用PyMuPDF整体缩放纯矢量PDF内容
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. 先用 wash_eps_ps 清洗，输出到 out_path
            tmp_out = cv.script_convert(in_path, tmp_dir)
            try:
                doc = fitz.open(tmp_out)
                new_doc = fitz.open()
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
                        target_width = orig_width
                        target_height = orig_height

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
                    crop_box = kwargs.get("crop_box", None)
                    if crop_box is not None and confirm_cropbox(crop_box, (target_width, target_height)):
                        # crop_box: (left, top, right, bottom)
                        x = float(crop_box[0])
                        y = float(crop_box[1])
                        w = float(crop_box[2] - crop_box[0])
                        h = float(crop_box[3] - crop_box[1])
                        # page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                        new_page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                        if logger:
                            logger.info(f"[vector] Set cropbox to ({x},{y},{w},{h})")
                    #else:
                        #page.set_cropbox(fitz.Rect(0, 0, target_width, target_height))
                    # page.get_pixmap(mat)
                    if logger:
                        logger.info(f"[vector] Page scaled: {orig_width}x{orig_height}pt -> {target_width}x{target_height}pt, scale=({scale_x:.2f},{scale_y:.2f})")
                tmp_path = os.path.join(tmp_dir, "temp.pdf")
                new_doc.save(tmp_path)
                doc.close()
                new_doc.close()

                img = cv.show_script(tmp_path, dpi=dpi) if show_image else None
                shutil.move(tmp_path, out_path) if save_image else out_path = None
                msg = f"[vector] PDF saved to {out_path}" if save_image else "[vector] PDF resized without saving"
                logger.info(msg) if logger else None
                return out_path, img
            except Exception as e:
                raise RuntimeError(f"PDF crop/resize failed: {e}")
    
    
def crop_eps_ps(
    in_path: str,
    out_dir: str,
    show_image: bool = False,
    save_image: bool = True,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    """
    Resize or crop EPS/PS file by editing BoundingBox and HiResBoundingBox.
    逻辑：
      1. 用 wash_eps_ps 清洗文件（标准化 EPS/PS）
      2. 如果指定 crop_box，直接修改 %%BoundingBox 和 %%HiResBoundingBox
      3. 完全二进制安全，支持包含二进制数据的 EPS
      只支持裁剪，不支持缩放
    """

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
        # 获取 crop_box
        crop_box = kwargs.get("crop_box", None)
        dpi = kwargs.get("dpi", None)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. 先用 wash_eps_ps 清洗，输出到 out_path
            tmp_out = cv.script_convert(in_path, tmp_dir)

            # 2. 如果有 crop_box，修改 BoundingBox
            if (crop_box is not None) and confirm_cropbox(crop_box, get_ps_size_pt(in_path)):
                x0, y0, x1, y1 = crop_box
                # 二进制模式读取 EPS
                with open(tmp_out, "rb") as f:
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
                with open(tmp_out, "wb") as f:
                    f.write(content)
                if logger:
                    logger.info(f"Cropped BoundingBox to {x0} {y0} {x1} {y1} "
                                f"(bbox lines: {n_bbox}, hires lines: {n_hires})")
                img = cv.show_script(tmp_out, dpi=dpi) if show_image else None
                shutil.move(tmp_out, out_path) if save_image else out_path = None
            else:
                # 未指定 crop_box，直接复制原文件
                img = cv.show_script(in_path, dpi=dpi) if show_image else None
                shutil.move(in_path, out_path) if save_image else out_path = None
                if logger:
                    logger.info(f"[vector] EPS/PS copied without crop, saved to {out_path}")

        return out_path, img
