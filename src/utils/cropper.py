from typing import Optional, Tuple, Callable
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
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
from src.utils.commons import get_script_size
from src.utils.commons import compute_trans_matrix


def crop_image(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    image_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[str]:

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "cropped"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    # 自动获取目标尺寸
    img = Image.open(in_path)
    if confirm_cropbox(crop_box, (img.width, img.height)):
        logger.info(f"[crop] crop box: {crop_box}") if logger else None
        img = img.crop(crop_box)
    if save_image:
        img.save(out_path)
    else:
        out_path = None
    msg = f"[crop] saved to: {out_path}" if save_image else "[crop] image cropped without saving"
    logger.info(msg) if logger else None
    if save_image:
        image_preview_callback(img) if image_preview_callback else None
    else:
        image_preview_callback(display_crop(Image.open(in_path), crop_box)) if image_preview_callback else None
    return out_path


def crop_svg(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "cropped"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    try:
        tree = ET.parse(in_path)
        root = tree.getroot()
        orig_width = int(float(root.get("width")))
        orig_height = int(float(root.get("height")))
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")
    
    try:
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
            root.set("viewBox", f"0 0 {orig_width} {orig_height}")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, "temp.svg")
            tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
            file_preview_callback(tmp_path) if file_preview_callback else None
            out_path = shutil.move(tmp_path, out_path) if save_image else None
            msg = f"[vector] SVG saved to {out_path}" if save_image else "[vector] SVG resized without saving"
            logger.info(msg) if logger else None
        return out_path
    except Exception as e:
        raise RuntimeError(f"SVG crop/resize failed: {e}")


def crop_pdf(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[str]:
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "cropped"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):

        # 用PyMuPDF整体缩放纯矢量PDF内容
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. 先用 wash_eps_ps 清洗，输出到 out_path
            tmp_out = cv.script_convert(in_path, tmp_dir)
            try:
                with fitz.open(tmp_out) as doc:
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
                            
                        tmp_path = os.path.join(tmp_dir, "temp.pdf")
                        new_doc.save(tmp_path)
                file_preview_callback(tmp_path) if file_preview_callback else None
                out_path = shutil.move(tmp_path, out_path) if save_image else None
                msg = f"[vector] PDF saved to {out_path}" if save_image else "[vector] PDF resized without saving"
                logger.info(msg) if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f"PDF crop/resize failed: {e}")


def crop_script(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[str]:
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
    suffix = "cropped"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
    
    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
        orig_width, orig_height = get_script_size(in_path)

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_out_0 = os.path.join(tmp_dir, "temp_0.eps")
            tmp_out_1 = os.path.join(tmp_dir, "temp_1.eps")
            tmp_out_2 = os.path.join(tmp_dir, "temp_2.eps")
            tmp_out_3 = os.path.join(tmp_dir, "temp_3.eps")
            
            if confirm_cropbox(crop_box, (orig_width, orig_height)):
                change_bbox(
                    in_path=in_path, 
                    out_path=tmp_out_0,
                    old_bbox=(0, 0, orig_width, orig_height),
                    new_bbox=crop_box, 
                    logger=logger
                )
                update_matrix(
                    tmp_out_0, 
                    tmp_out_0, 
                    translate=[crop_box[0], crop_box[1]]
                )
            
            file_preview_callback(tmp_out_0) if file_preview_callback else None
            out_path = shutil.move(tmp_out_0, out_path) if save_image else None
        return out_path

def update_matrix(in_path: str, out_path: str, logger = None, **kwarg):

    with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # 匹配六元组（a b c d e f cm 或 [a b c d e f]） 
    
    pattern = re.compile(
        r"""
        ^(?!\s*/)                                              # 不允许以 / 开头（跳过命令行）

        (?P<prefix>.*?)                                        # 前导内容

        (?:
            (?P<vals1>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+
                    [-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s+cm
            |
            \[\s*(?P<vals2>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+
                        [-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s*\]
        )

        (?P<suffix>.*)$                                        # 后缀
        """,
        re.VERBOSE
    )

    mat_line_idx, mat = None, None
    prefix, suffix, vals = "", "", ""
    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            prefix = match.group("prefix")
            suffix = match.group("suffix")
            # 可能是 cm 形式，也可能是 [ ] 形式
            #vals = match.group("vals1") or match.group("vals2")
            vals = match.group("vals2")
            a, b, c, d, e, f = map(float, vals.split())
            mat = [a, b, c, d, e, f]
            mat_line_idx = i
            logger.info(f"[vector] Original EPS/PS transform matrix: {mat}") if logger else None
            break

    if mat is not None and mat_line_idx is not None:
        mat = compute_trans_matrix(mat, **kwarg)            
        if False: #pattern.match(lines[mat_line_idx]):
            # 替换为 a b c d e f cm
            new_line = f"{prefix}" + "{} {} {} {} {} {} cm".format(*mat) + f"{suffix}\n"
            lines[mat_line_idx] = new_line
        else:
            # 替换为 [a b c d e f]
            new_line = f"{prefix}" + "[{} {} {} {} {} {}]".format(*mat) + f"{suffix}"
            # 保留原行其他内容
            lines[mat_line_idx] = pattern.sub(new_line, lines[mat_line_idx])
        logger.info(f"[vector] EPS/PS transform matrix replaced: {mat}") if logger else None
        logger.info("[vector] Applied transforms: " + f"{mat}") if logger else None
        with open(out_path, "w", encoding="utf-8") as f:
            f.writelines(lines)


def change_bbox(
    in_path: str, out_path: str, old_bbox: tuple[float, float, float, float], new_bbox: tuple[float, float, float, float], logger: Optional[Logger] = None, tolerate: float = 1.5
) -> Optional[str]:
    """
    修改 EPS 文件中所有 W H 对（整数或浮点，带容差），精确替换为 new_w, new_h。
    同时保留 %%BoundingBox 和 %%HiResBoundingBox 的替换。

    参数:
        in_path: 输入 EPS 文件路径
        out_path: 输出 EPS 文件路径
        new_w: 新的宽度
        new_h: 新的高度
        logger: 可选 logger
        tolerate: 匹配 W H 的容差
    """
    _, _, old_w, old_h = old_bbox
    new_x, new_y, new_w, new_h = new_bbox
    with open(in_path, "rb") as f:
        content = f.read()

    # ----------------- 正则模式 -----------------
    # 匹配 W H 对（整数或浮点），前后有空格或开始结束边界
    pattern_wh_int = re.compile(
        br"(?<!\d)"          # 左边不是数字
        br"(-?\d+)"          # W
        br"\s+"              # 间隔
        br"(-?\d+)"          # H
        br"(?!\d)"           # 右边不是数字
    )

    pattern_wh_float = re.compile(
        br"(?<![\d.])"          # 左边不是数字或小数点
        br"([-+]?\d+(?:\.\d+)?)" # W: 整数或带小数
        br"\s+"                 # 空格
        br"([-+]?\d+(?:\.\d+)?)" # H: 整数或带小数
        br"(?![\d.])"           # 右边不是数字或小数点
    )

    # 匹配 %%BoundingBox
    pattern_bbox = re.compile(
        br"^\s*(%%BoundingBox: )(-?\d+) (-?\d+) (-?\d+) (-?\d+)", re.MULTILINE
    )

    # 匹配 %%HiResBoundingBox
    pattern_hires = re.compile(
        br"^\s*(%%HiResBoundingBox: )(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)",
        re.MULTILINE,
    )

    # ----------------- 替换函数 -----------------
    def repl_wh(m):
        orig_w = float(m.group(1))
        orig_h = float(m.group(2))
        
        # 判断是否在容差内
        if abs(orig_w - old_w) <= tolerate and abs(orig_h - old_h) <= tolerate:
            return b"%d %d" % (new_w, new_h)
        else:
            return m.group(0)


    def repl_bbox(m):
        x0, y0, x1, y1 = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        return b"%s%d %d %d %d" % (m.group(1), int(new_x), int(new_y), int(new_w), int(new_h))

    def repl_hires(m):
        x0, y0, x1, y1 = float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
        return b"%s%.2f %.2f %.2f %.2f" % (m.group(1), float(new_x), float(new_y), float(new_w), float(new_h))

    # ----------------- 执行替换 -----------------
    content, n_bbox = pattern_bbox.subn(repl_bbox, content)
    content, n_hires = pattern_hires.subn(repl_hires, content)
    content, n_wh = pattern_wh_float.subn(repl_wh, content)


    # ----------------- 写回文件 -----------------
    with open(out_path, "wb") as f:
        f.write(content)

    if logger:
        logger.info(
            f"Replaced width/height to {new_w} {new_h} "
            f"(WH pairs: {n_wh}, BoundingBox lines: {n_bbox}, HiRes lines: {n_hires})"
        )

    return (new_w, new_h)


def display_crop(img, crop_box, box_color="white", box_width=3, mask_opacity=120):
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