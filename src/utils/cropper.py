from typing import Optional, Tuple, Callable
from PIL import Image, ImageDraw
import os
import fitz  # PyMuPDF
import math
import xml.etree.ElementTree as ET

from src.utils.logger import Logger

from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_single_page
from src.utils.commons import confirm_dir_existence
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_cropbox
from src.utils.commons import get_script_size, get_svg_size

from src.utils.transformer import change_bbox, update_matrix


def display_crop(img, crop_box, eps_coordinate=False, box_color="white", box_width=3, mask_opacity=120):
    """
    在图像上绘制裁剪框，并在其外部加半透明遮罩。
    
    参数:
        img: Image.Image
        crop_box: (x, y, w, h) - 左上角 + 宽高
        box_color: 裁剪框颜色 (默认白色更清晰)
        box_width: 边框宽度
        mask_opacity: 遮罩透明度，范围 0-255（越大越暗）
    """
    x, y, x2, y2 = crop_box
    if eps_coordinate:
        # EPS 坐标系，y 轴向上
        y, y2 = img.height - y2, img.height - y

    # 复制一份图像，不修改原图
    img_out = img.copy().convert("RGBA")

    # 创建一个与图像大小相同的透明图层，用于添加遮罩
    mask_layer = Image.new("RGBA", img_out.size, (0, 0, 0, 0))
    mask_draw = ImageDraw.Draw(mask_layer)

    # 半透明遮罩（框外）
    width, height = img_out.size

    # 绘制四个方向的遮罩
    mask_draw.rectangle([(0, 0), (width, y)], fill=(0, 0, 0, mask_opacity))               # 上
    mask_draw.rectangle([(0, y2), (width, height)], fill=(0, 0, 0, mask_opacity))        # 下
    mask_draw.rectangle([(0, y), (x, y2)], fill=(0, 0, 0, mask_opacity))                 # 左
    mask_draw.rectangle([(x2, y), (width, y2)], fill=(0, 0, 0, mask_opacity))            # 右

    # 将遮罩层叠加到图像
    img_out = Image.alpha_composite(img_out, mask_layer)

    # 最后画裁剪框（为了更突出，建议白色）
    draw = ImageDraw.Draw(img_out)
    draw.rectangle([x, y, x2, y2], outline=box_color, width=box_width)

    return img_out.convert("RGB")


def crop_image(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    image_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[str]:

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

        # 自动获取目标尺寸
        img = Image.open(in_path)
        if confirm_cropbox(crop_box, (img.width, img.height)):
            logger.info(f"[crop] crop box: {crop_box}") if logger else None
            img = img.crop(crop_box)
            img.save(out_path)
        else:
            out_path = None
        msg = f"[crop] saved to: {out_path}"
        image_preview_callback(img) if image_preview_callback else None
    else:
        image_preview_callback(display_crop(Image.open(in_path), crop_box)) if image_preview_callback else None
        msg = f"[crop] see preview frame for cropping effect"
        out_path = None
    logger.info(msg) if logger else None
    return out_path


def crop_svg(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:

    def show_crop(img):
        return display_crop(img, crop_box=crop_box)

    if save_image:

        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            orig_width, orig_height = get_svg_size(in_path)    
            try:
                tree = ET.parse(in_path)
                root = tree.getroot()
                if confirm_cropbox(crop_box, (orig_width, orig_height)):
                    # crop_box: (left, top, right, bottom)
                    x = crop_box[0]
                    y = crop_box[1]
                    w = crop_box[2] - crop_box[0]
                    h = crop_box[3] - crop_box[1]
                    logger.info(f"[vector] Cropping SVG viewBox to ({x},{y},{w},{h})") if logger else None
                    root.set("viewBox", f"{x} {y} {w} {h}")
                    root.set("width", str(w))
                    root.set("height", str(h))
                else:
                    logger.info("[vector] Crop box invalid, skipping crop.") if logger else None
                    root.set("viewBox", f"0 0 {orig_width} {orig_height}")
                    return None
                
                tree.write(out_path, encoding="utf-8", xml_declaration=True)
                file_preview_callback(out_path) if file_preview_callback else None
                msg = f"[vector] SVG saved to {out_path}"
            except Exception as e:
                raise RuntimeError(f"SVG crop/resize failed: {e}")
    else:
        out_path = None
        file_preview_callback(in_path, show_crop) if file_preview_callback else None
        msg = f"[crop] see preview frame for cropping effect"
    logger.info(msg) if logger else None
    return out_path

def crop_pdf(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    
    dpi = kwargs.get("dpi", 96)

    def show_crop(img):    
        display_crop_box = (
            max(math.floor(crop_box[0] / 72 * dpi), 0),
            max(math.floor(crop_box[1] / 72 * dpi), 0),
            math.floor(crop_box[2] / 72 * dpi),
            math.floor(crop_box[3] / 72 * dpi),
        )
        return display_crop(img, crop_box=display_crop_box)

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

        if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            try:
                with fitz.open(in_path) as doc:
                    with fitz.open() as new_doc:
                        for page in doc:
                            rect = page.rect
                            orig_width = rect.width
                            orig_height = rect.height
                            new_page = new_doc.new_page(width=orig_width, height=orig_height)
                            new_page.show_pdf_page(
                                new_page.rect,  # 目标矩形
                                doc,  # 源文档
                                page.number,  # 源页码
                                clip=None,  # 不裁剪
                                rotate=0,  # 不旋转
                                keep_proportion=False,  # 不保持比例(使用我们的缩放)
                                overlay=True
                            )
                            
                            if confirm_cropbox(crop_box, (orig_width, orig_height)):
                                # crop_box: (left, top, right, bottom)
                                # page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                                new_page.set_cropbox(fitz.Rect(*crop_box))
                                logger.info(f"[vector] Set cropbox to {crop_box}") if logger else None
                            else:
                                page.set_cropbox(fitz.Rect(0, 0, orig_width, orig_height))
                        new_doc.save(out_path)
                file_preview_callback(out_path) if file_preview_callback else None
                msg = f"[vector] PDF saved to {out_path}"
            except Exception as e:
                raise RuntimeError(f"PDF crop/resize failed: {e}")
    else:
        out_path = None
        file_preview_callback(in_path, show_crop) if file_preview_callback else None
        msg = f"[crop] see preview frame for cropping effect"
    logger.info(msg) if logger else None
    return out_path

def crop_script(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    """
    Resize or crop EPS/PS file by editing BoundingBox and HiResBoundingBox.
    逻辑：
      1. 用 wash_eps_ps 清洗文件（标准化 EPS/PS）
      2. 如果指定 crop_box，直接修改 %%BoundingBox 和 %%HiResBoundingBox
      3. 完全二进制安全，支持包含二进制数据的 EPS
      只支持裁剪，不支持缩放
    """
    dpi = kwargs.get("dpi", 96)

    def show_crop_script(img):
        display_crop_box = (
            max(math.floor(crop_box[0] / 72 * dpi), 0),
            max(math.floor(crop_box[1] / 72 * dpi), 0),
            math.floor(crop_box[2] / 72 * dpi),
            math.floor(crop_box[3] / 72 * dpi),
        )
        return display_crop(img, crop_box=display_crop_box, eps_coordinate=True)
    
    if save_image:

        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
        
        if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            orig_width, orig_height = get_script_size(in_path)
            if confirm_cropbox(crop_box, (orig_width, orig_height)):
                sz = get_script_size(in_path)
                # Translate to origin, avoiding negative coordinates
                # 先平移到原点，再裁剪，再平移回去
                # 否则，可能出现负坐标，导致部分查看器无法正确显示
                # 因此，必须分两步修改矩阵和 BoundingBox，不能合并为一步
                change_bbox(
                    in_path=in_path, 
                    out_path=out_path,
                    old_bbox=(0, 0, orig_width, orig_height),
                    new_bbox=(0, 0, max(orig_width, orig_height), max(orig_width, orig_height)), 
                    logger=logger
                )
                update_matrix(
                    in_path, 
                    out_path, 
                    translate=[0, crop_box[3] - sz[1]],  # y 方向平移
                )
                change_bbox(
                    in_path=in_path, 
                    out_path=out_path,
                    old_bbox=(0, 0, max(orig_width, orig_height), max(orig_width, orig_height)),
                    new_bbox=(0, 0, crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]), 
                    logger=logger
                )
                update_matrix(
                    out_path, 
                    out_path, 
                    translate=[-crop_box[0], -crop_box[1]],  # y 方向平移
                )
            else:
                logger.error("[vector] Crop box invalid, skipping crop.")
            
            file_preview_callback(out_path) if file_preview_callback else None
            msg = f"[vector] EPS saved to {out_path}"
    else:
        out_path = None
        file_preview_callback(in_path, show_crop_script) if file_preview_callback else None     
        msg = f"[crop] see preview frame for cropping effect"
    logger.info(msg) if logger else None
    return out_path
