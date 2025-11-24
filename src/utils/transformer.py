from typing import Optional, Tuple, Callable
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
from src.utils.commons import get_script_size, get_svg_size
from src.utils.commons import compute_trans_matrix


pattern_cm_sim = re.compile(
    r"""
    ^                                      # 行首
    (                                     # 开始捕获组
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第一个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第二个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第三个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第四个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第五个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第六个数字
    )
    \s+cm                                 # 空格 + cm
    """,
    re.VERBOSE
)

# 匹配：[a b c d e f] ...（只匹配括号内的6个数字）
pattern_br_sim = re.compile(
    r"""
    ^\[\s*                               # 行首的 [ 和可能的空间
    (                                     # 开始捕获组
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第一个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第二个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第三个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第四个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第五个数字
        \s+                               # 空格分隔
        [-+]?\d*\.?\d+([eE][-+]?\d+)?     # 第六个数字
    )
    \s*\]                                # 可能的空间 + ]
    """,
    re.VERBOSE
)


pattern_in_byte = re.compile(
        br"""
        ^(?!\s*/)

        (?P<prefix>.*?)

        (?:
            (?P<vals1>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+
                    [-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s+cm
            |
            \[\s*(?P<vals2>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+
                        [-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s*\]
        )

        (?P<suffix>.*)$
        """,
        re.VERBOSE
    )

def transform_image(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    image_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

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

    img = transform_raster(img, (new_width, new_height), logger=logger, **kwargs)
    
    if save_image:
        img.save(out_path)
    else:
        out_path = None
    msg = f"[crop] saved to: {out_path}" if save_image else "[crop] image cropped without saving"
    logger.info(msg) if logger else None
    image_preview_callback(img) if image_preview_callback else None
    return out_path


def transform_raster(
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

    if 'rotate_angle' in kwargs:
        angle = kwargs.get('rotate_angle')
        logger.info(f"[crop] rotate image by {angle} degrees") if logger else None
        img_2 = img_2.rotate(angle, expand=True)

    if 'flip' in kwargs and kwargs['flip'] in ['LR', 'TB']:
        flip = kwargs.get('flip')
        direction = Image.FLIP_LEFT_RIGHT if flip == 'LR' else Image.FLIP_TOP_BOTTOM
        img_2 = img_2.transpose(direction)
        logger.info(f"[crop] flip image {flip}") if logger else None

    return img_2


def transform_svg(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    
    def mat2str(mat: list[float, float, float, float, float, float]) -> str:
        return "matrix(" + " ".join(f"{x}" for x in mat) + ")"

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    orig_width, orig_height = get_svg_size(in_path)
    mat = compute_trans_matrix()

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

    with tempfile.TemporaryDirectory() as tmp_dir:

        mat = compute_trans_matrix(mat, scale=(scale_x, scale_y))

        try:
            tree = ET.parse(in_path)
            root = tree.getroot()
        except Exception:
            raise RuntimeError("Failed to parse SVG dimensions.")
        
        root.set("viewBox", f"0 0 {target_width} {target_height}")
        root.set("width", str(target_width))
        root.set("height", str(target_height))

        if 'flip_lr' in kwargs and kwargs['flip_lr']:
            mat = compute_trans_matrix(mat, flip_lr=True, translate=[target_width, 0])
        if 'flip_tb' in kwargs and kwargs['flip_tb']:
            mat = compute_trans_matrix(mat, flip_tb=True, translate=[0, target_height])

        if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
            angle = kwargs['rotate_angle'] % 360
            # 如果旋转90或270度，需要交换width和height
            if angle in [90, 270]:
                temp_value = target_width
                target_width = target_height
                target_height = temp_value
                root.set("viewBox", f"0 0 {target_width} {target_height}")
                root.set("width", str(target_width))
                root.set("height", str(target_height))
            angle_map = {
                0: [0, 0],
                90: [0, target_height],
                180: [target_width, target_height],
                270: [target_width, 0],
            }
            mat = compute_trans_matrix(
                mat, 
                rotate_angle=angle, 
                translate=angle_map.get(angle, [0, 0])
            )
            logger.info(f"[vector] Rotating SVG by {angle} degrees") if logger else None

        try:
            g = ET.Element("g")
            for child in list(root):
                g.append(child)
                root.remove(child)
            g.set("transform", " ".join([mat2str(mat)]))
            root.append(g)
        except Exception as e:
            raise RuntimeError(f"SVG transform failed: {e}")

    try:       
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


def transform_pdf(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    file_preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
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
                            logger.info(f"[vector] Page scaled: {orig_width}x{orig_height}pt -> {target_width}x{target_height}pt, scale=({scale_x:.2f},{scale_y:.2f})") if logger else None
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
                            if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
                                angle = kwargs.get('rotate_angle')
                                logger.info(f"[vector] Rotating PDF page by {angle} degrees") if logger else None
                                new_page.set_rotation(angle)

                            if 'flip_lr' in kwargs or 'flip_tb' in kwargs:
                                logger.error(f"[vector] Flipping PDF page is not supported.") if logger else None

                        tmp_path = os.path.join(tmp_dir, "temp.pdf")
                        new_doc.save(tmp_path)
                file_preview_callback(tmp_path) if file_preview_callback else None
                out_path = shutil.move(tmp_path, out_path) if save_image else None
                msg = f"[vector] PDF saved to {out_path}" if save_image else "[vector] PDF resized without saving"
                logger.info(msg) if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f"PDF crop/resize failed: {e}")


def transform_script(
    in_path: str,
    out_dir: str,
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

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
    
    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
        orig_width, orig_height = get_script_size(in_path)
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

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_out_0 = os.path.join(tmp_dir, "temp_0.eps")
            
            # if 'rotate_angle' in kwargs and (kwargs.get('rotate_angle') % 360 in [90, 270]):
            target_size = max(target_width, target_height)

            update_matrix(in_path, tmp_out_0, scale=(scale_x, scale_y))   
            new_bbox = change_bbox(
                    in_path=tmp_out_0, 
                    out_path=tmp_out_0, 
                    old_bbox=(0, 0, orig_width, orig_height),
                    new_bbox=(0, 0, target_size, target_size),
                    logger=logger
                )

            if 'flip_lr' in kwargs and kwargs['flip_lr']:
                update_matrix(tmp_out_0, tmp_out_0, flip_lr=True, translate=[target_width, 0])

            if 'flip_tb' in kwargs and kwargs['flip_tb']: 
                update_matrix(tmp_out_0, tmp_out_0, flip_tb=True, translate=[0, target_height])           

            if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
                angle = kwargs.get('rotate_angle') % 360
                # 如果旋转90或270度，需要交换width和height
                if angle in [90, 270]:
                    temp_value = target_width
                    target_width = target_height
                    target_height = temp_value
                angle_map = {
                    0: [0, 0],
                    90: [0, target_height],
                    180: [target_width, target_height],
                    270: [target_width, 0],
                }
                update_matrix(
                    tmp_out_0, 
                    tmp_out_0, 
                    rotate_angle=angle, 
                    translate=angle_map.get(angle, [0, 0])
                )
                logger.info(f"[vector] Rotating EPS by {angle} degrees") if logger else None

            change_bbox(
                in_path=tmp_out_0, 
                out_path=tmp_out_0, 
                old_bbox=(0, 0, orig_width, orig_height),
                new_bbox=(0, 0, target_width, target_height),
                logger=logger
            )

            file_preview_callback(tmp_out_0) if file_preview_callback else None
            out_path = shutil.move(tmp_out_0, out_path) if save_image else None
        return out_path


def update_matrix(in_path: str, out_path: str, logger=None, **kwargs):
    """
    更新 EPS/PS 文件中的变换矩阵
    """
    with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    mat = None

    # 查找并处理匹配的行
    for i, line in enumerate(lines):
        match = pattern_cm_sim.search(line) or pattern_br_sim.search(line)
        if match:
            # 提取并处理数字
            numbers_str = match.group(1)
            orig_mat = list(map(float, numbers_str.split()))
            mat = compute_trans_matrix(orig_mat, **kwargs)
            
            # 构建新值并替换
            new_vals_str = " ".join(f"{int(x)}" for x in mat)
            if pattern_cm_sim.search(line):
                new_vals_str = new_vals_str + " cm"
                lines[i] = pattern_cm_sim.sub(new_vals_str, line)
                format_type = "cm"
            else:
                new_vals_str = "[" + new_vals_str + "]"
                lines[i] = pattern_br_sim.sub(new_vals_str, line)
                format_type = "bracket"
            
            # 记录日志
            if logger:
                logger.info(f"[vector] Original matrix ({format_type}): {orig_mat}")
                logger.info(f"[vector] Replaced matrix: {mat}")
                logger.info(f"[vector] Applied transforms: {mat}")
            break

    # 如果没有找到匹配项
    if mat is None and logger:
        logger.warning("[vector] No transform matrix found in the file")

    # 写入文件
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def change_bbox(
    in_path: str, out_path: str, old_bbox: tuple[float, float, float, float], new_bbox: tuple[float, float, float, float], logger: Optional[Logger] = None, tolerate: float = 2
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

    pattern_wh_cairo = re.compile(
        br"(?<!\d)"          # 左边不是数字
        br"(-?\d+)"          # W (捕获组1)
        br"\s+"              # 间隔
        br"(-?\d+)"          # H (捕获组2)
        br"\s*"              # 可选空格
        br"(cairo.*)"        # cairo及后面的所有内容 (捕获组3)
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
            return b"%d %d" % (int(new_w), int(new_h))
        else:
            return m.group(0)
        
    def repl_wh_cairo(m):        
        suffix = m.group(3)
        return b"%d %d " % (int(new_w), int(new_h)) + suffix


    def repl_bbox(m):
        x0, y0, x1, y1 = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        return b"%s%d %d %d %d" % (m.group(1), int(new_x), int(new_y), int(new_w), int(new_h))

    def repl_hires(m):
        x0, y0, x1, y1 = float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
        return b"%s%.2f %.2f %.2f %.2f" % (m.group(1), float(new_x), float(new_y), float(new_w), float(new_h))

    # ----------------- 执行替换 -----------------
    content, n_bbox = pattern_bbox.subn(repl_bbox, content)
    content, n_hires = pattern_hires.subn(repl_hires, content)
    content, n_wh = pattern_wh_cairo.subn(repl_wh_cairo, content)
    lines = content.split(b"\n")
    new_lines = []

    for line in lines:
        # 跳过 cm / bracket matrix 行
        if pattern_in_byte.match(line):
            new_lines.append(line)
            continue
        
        # 对其他行做 W H 匹配替换
        new_line, n_wh = pattern_wh_int.subn(repl_wh, line)
        new_lines.append(new_line)

    content = b"\n".join(new_lines)


    # ----------------- 写回文件 -----------------
    with open(out_path, "wb") as f:
        f.write(content)

    if logger:
        logger.info(
            f"Replaced width/height to {new_w} {new_h} "
            f"(WH pairs: {n_wh}, BoundingBox lines: {n_bbox}, HiRes lines: {n_hires})"
        )

    return new_bbox
