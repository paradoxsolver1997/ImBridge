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
from src.utils.commons import confirm_cropbox
from src.utils.commons import get_script_size
from src.utils.commons import compute_trans_matrix


def transform_image(
    in_path: str,
    out_path: str,
    save_image: bool = True,
    project_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:

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
    
    if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
        crop_box = kwargs.get('crop_box')
        if confirm_cropbox(crop_box, (img.width, img.height)):
            logger.info(f"[crop] crop box: {crop_box}") if logger else None
            img = img.crop(crop_box)
    
    if 'rotate_angle' in kwargs:
        angle = kwargs.get('rotate_angle')
        logger.info(f"[crop] rotate image by {angle} degrees") if logger else None
        img = img.rotate(angle, expand=True)

    if 'flip' in kwargs and kwargs['flip'] in ['LR', 'TB']:
        flip = kwargs.get('flip')
        direction = Image.FLIP_LEFT_RIGHT if flip == 'LR' else Image.FLIP_TOP_BOTTOM
        img = img.transpose(direction)
        logger.info(f"[crop] flip image {flip}") if logger else None
    
    if save_image:
        img.save(out_path)
    else:
        out_path = None
    msg = f"[crop] saved to: {out_path}" if save_image else "[crop] image cropped without saving"
    logger.info(msg) if logger else None
    project_callback(img) if project_callback else None
    return out_path


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


def transform_svg(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    project_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    
    def mat2str(mat: list[float, float, float, float, float, float]) -> str:
        return "matrix(" + " ".join(f"{x}" for x in mat) + ")"

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    try:
        tree = ET.parse(in_path)
        root = tree.getroot()
        orig_width = int(float(root.get("width")))
        orig_height = int(float(root.get("height")))
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")
    
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
    
    mat = compute_trans_matrix(mat, scale=(scale_x, scale_y))
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
        if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
            crop_box = kwargs.get('crop_box')
            if confirm_cropbox(crop_box, (target_width, target_height)):
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
            root.set("viewBox", f"0 0 {target_width} {target_height}")
            root.set("width", str(target_width))
            root.set("height", str(target_height))
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, "temp.svg")
            tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
            project_callback(cv.show_svg(tmp_path)) if project_callback else None
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
    project_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    
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

                            # page.set_mediabox(fitz.Rect(0, 0, target_width, target_height))
                            # 支持单独设置cropbox
                            if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
                                crop_box = kwargs.get("crop_box")
                                if confirm_cropbox(crop_box, (target_width, target_height)):
                                    # crop_box: (left, top, right, bottom)
                                    x = float(crop_box[0])
                                    y = float(crop_box[1])
                                    w = float(crop_box[2] - crop_box[0])
                                    h = float(crop_box[3] - crop_box[1])
                                    # page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                                    new_page.set_cropbox(fitz.Rect(x, y, x + w, y + h))
                                    logger.info(f"[vector] Set cropbox to ({x},{y},{w},{h})") if logger else None
                                else:
                                    page.set_cropbox(fitz.Rect(0, 0, target_width, target_height))
                                logger.info(f"[vector] Page scaled: {orig_width}x{orig_height}pt -> {target_width}x{target_height}pt, scale=({scale_x:.2f},{scale_y:.2f})") if logger else None                            

                        tmp_path = os.path.join(tmp_dir, "temp.pdf")
                        new_doc.save(tmp_path)
                project_callback(cv.show_script(tmp_path, dpi=dpi)) if project_callback else None
                out_path = shutil.move(tmp_path, out_path) if save_image else None
                msg = f"[vector] PDF saved to {out_path}" if save_image else "[vector] PDF resized without saving"
                logger.info(msg) if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f"PDF crop/resize failed: {e}")
    
    
def transform_eps_ps(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    project_callback: Optional[Callable] = None,
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
        # 获取 crop_box
        
        dpi = kwargs.get("dpi", None)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. 先用 wash_eps_ps 清洗，输出到 out_path
            # tmp_out = cv.script_convert(in_path, tmp_dir)
            tmp_out = os.path.join(tmp_dir, "washed.eps")
            # 2. 如果有 crop_box，修改 BoundingBox
            if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
                crop_box = kwargs.get("crop_box", None)
                if confirm_cropbox(crop_box, get_script_size(in_path)):
                    x0, y0, x1, y1 = crop_box
                    # 二进制模式读取 EPS
                    with open(in_path, "rb") as f:
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
                    with open(in_path, "wb") as f:
                        f.write(content)
                    if logger:
                        logger.info(f"Cropped BoundingBox to {x0} {y0} {x1} {y1} "
                                    f"(bbox lines: {n_bbox}, hires lines: {n_hires})")
            else:
                shutil.copy(in_path, tmp_out)
            
            # ======== 读取 EPS 内容，准备替换变换矩阵 ========
            with open(tmp_out, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            width, height = get_script_size(tmp_out)

            # 匹配六元组（a b c d e f cm 或 [a b c d e f]）
            import re
            mat_line_idx = None
            orig_mat = None
            mat_pattern_cm = re.compile(r"^\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+cm\b")
            mat_pattern_bracket = re.compile(r"\[\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s*\]")
            mat_pattern_cm = re.compile(r"^(?P<pre>\s*)(?P<a>[-+\d.eE]+)\s+(?P<b>[-+\d.eE]+)\s+(?P<c>[-+\d.eE]+)\s+(?P<d>[-+\d.eE]+)\s+(?P<e>[-+\d.eE]+)\s+(?P<f>[-+\d.eE]+)\s+cm(?P<post>.*)$")
            mat_pattern_bracket = re.compile(r"^(?P<pre>.*?)(\[\s*)(?P<a>[-+\d.eE]+)\s+(?P<b>[-+\d.eE]+)\s+(?P<c>[-+\d.eE]+)\s+(?P<d>[-+\d.eE]+)\s+(?P<e>[-+\d.eE]+)\s+(?P<f>[-+\d.eE]+)\s*\](?P<post>.*)$")
            
            
            pattern = re.compile(
                r"""^
                (?P<prefix>.*?)                                  # 前导内容
                (?:
                    (?P<vals1>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s+cm
                    |
                    \[\s*(?P<vals2>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s*\]
                )
                (?P<suffix>.*)$                                   # 后缀
                """,
                re.VERBOSE
            )

            
            for i, line in enumerate(lines):

                match = pattern.match(line)
                if match:
                    pre = match.group("prefix")
                    post = match.group("suffix")

                    # 可能是 cm 形式，也可能是 [ ] 形式
                    vals = match.group("vals1") or match.group("vals2")
                    a, b, c, d, e, f = map(float, vals.split())
                    orig_mat = [a, b, c, d, e, f]
                    mat_line_idx = i
                    print("PREFIX:", pre)
                    print("VALUES:", orig_mat)
                    print("SUFFIX:", post)
                    break
                print("XXXXXX")

        
            if orig_mat is not None and mat_line_idx is not None:
                mat = compute_trans_matrix(orig_mat)
                logger.info(f"[vector] Original EPS/PS transform matrix: {orig_mat}") if logger else None
            else:
                logger.warning("[vector] No transform matrix found in EPS/PS.") if logger else None
                return None

            if 'flip_lr' in kwargs and kwargs['flip_lr']:
                mat = compute_trans_matrix(mat, flip_lr=True, translate=[width, 0])
                logger.info("[vector] Applied transforms: " + f"{mat}") if logger else None

            if 'flip_tb' in kwargs and kwargs['flip_tb']: 
                mat = compute_trans_matrix(mat, flip_tb=True, translate=[0, height])
                logger.info("[vector] Applied transforms: " + f"{mat}") if logger else None
            
            if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
                angle = kwargs.get("rotate_angle", None)
                # if angle is not None:
                    # 通用 rotate + translate
                    # transform_cmds.append(f"{angle} rotate\n0 {-height} translate\n")

                logger.info(f"[vector] Applied transforms:  rotate={angle}") if logger else None


            if mat_pattern_cm.match(lines[mat_line_idx]):
                # 替换为 a b c d e f cm
                new_line = f"{pre}" + "{} {} {} {} {} {} cm".format(*mat) + f"{post}\n"
                lines[mat_line_idx] = new_line
            else:
                # 替换为 [a b c d e f]
                new_line = f"{pre}" + "[ {} {} {} {} {} {} ]".format(*mat) + f"{post}"
                # 保留原行其他内容
                lines[mat_line_idx] = mat_pattern_bracket.sub(new_line, lines[mat_line_idx])
            print("NEW LINE")
            print(new_line)
            logger.info(f"[vector] EPS/PS transform matrix replaced: {mat}") if logger else None

            with open(tmp_out, "w", encoding="utf-8") as f:
                f.writelines(lines)

            project_callback(cv.show_script(tmp_out, dpi=dpi)) if project_callback else None
            if save_image:
                shutil.move(tmp_out, out_path)
            else:
                out_path = None

        return out_path
    

def transform_eps_ps2(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    project_callback: Optional[Callable] = None,
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
        # 获取 crop_box
        
        dpi = kwargs.get("dpi", None)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. 先用 wash_eps_ps 清洗，输出到 out_path
            # tmp_out = cv.script_convert(in_path, tmp_dir)
            tmp_out = os.path.join(tmp_dir, "washed.eps")
            # 2. 如果有 crop_box，修改 BoundingBox
            if 'crop_box' in kwargs and kwargs['crop_box'] is not None:
                crop_box = kwargs.get("crop_box", None)
                if confirm_cropbox(crop_box, get_script_size(in_path)):
                    x0, y0, x1, y1 = crop_box
                    # 二进制模式读取 EPS
                    with open(in_path, "rb") as f:
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
                    with open(in_path, "wb") as f:
                        f.write(content)
                    if logger:
                        logger.info(f"Cropped BoundingBox to {x0} {y0} {x1} {y1} "
                                    f"(bbox lines: {n_bbox}, hires lines: {n_hires})")
            else:
                shutil.copy(in_path, tmp_out)
            
            # ======== 读取 EPS 内容，准备替换变换矩阵 ========
            with open(tmp_out, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            width, height = get_script_size(tmp_out)

            # 匹配六元组（a b c d e f cm 或 [a b c d e f]）
            import re
            mat_line_idx = None
            orig_mat = None
            mat_pattern_cm = re.compile(r"^\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+cm\b")
            mat_pattern_bracket = re.compile(r"\[\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s*\]")
            mat_pattern_cm = re.compile(r"^(?P<pre>\s*)(?P<a>[-+\d.eE]+)\s+(?P<b>[-+\d.eE]+)\s+(?P<c>[-+\d.eE]+)\s+(?P<d>[-+\d.eE]+)\s+(?P<e>[-+\d.eE]+)\s+(?P<f>[-+\d.eE]+)\s+cm(?P<post>.*)$")
            mat_pattern_bracket = re.compile(r"^(?P<pre>.*?)(\[\s*)(?P<a>[-+\d.eE]+)\s+(?P<b>[-+\d.eE]+)\s+(?P<c>[-+\d.eE]+)\s+(?P<d>[-+\d.eE]+)\s+(?P<e>[-+\d.eE]+)\s+(?P<f>[-+\d.eE]+)\s*\](?P<post>.*)$")
            
            
            pattern = re.compile(
                r"""^
                (?P<prefix>.*?)                                  # 前导内容
                (?:
                    (?P<vals1>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s+cm
                    |
                    \[\s*(?P<vals2>[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+)\s*\]
                )
                (?P<suffix>.*)$                                   # 后缀
                """,
                re.VERBOSE
            )

            match = pattern.match(line)
            if match:
                prefix = match.group("prefix")
                suffix = match.group("suffix")

                # 可能是 cm 形式，也可能是 [ ] 形式
                vals = match.group("vals1") or match.group("vals2")
                a, b, c, d, e, f = map(float, vals.split())

                print("PREFIX:", prefix)
                print("VALUES:", a, b, c, d, e, f)
                print("SUFFIX:", suffix)
            print("XXXXXX")
            for i, line in enumerate(lines):
                m = mat_pattern_cm.match(line)
                if m:
                    pre = m.group('pre')
                    post = m.group('post')
                    orig_mat = [float(m.group(j)) for j in range(1, 7)]
                    mat_line_idx = i
                    break
                m2 = mat_pattern_bracket.search(line)
                if m2:
                    pre = m2.group('pre')
                    post = m2.group('post')
                    orig_mat = [float(m2.group(j)) for j in range(1, 7)]
                    mat_line_idx = i
                    break
            if orig_mat is not None and mat_line_idx is not None:
                mat = compute_trans_matrix(orig_mat)
                logger.info(f"[vector] Original EPS/PS transform matrix: {orig_mat}") if logger else None
            else:
                logger.warning("[vector] No transform matrix found in EPS/PS.") if logger else None
                return None

            if 'flip_lr' in kwargs and kwargs['flip_lr']:
                mat = compute_trans_matrix(mat, flip_lr=True, translate=[width, 0])
                logger.info("[vector] Applied transforms: " + f"{mat}") if logger else None

            if 'flip_tb' in kwargs and kwargs['flip_tb']: 
                mat = compute_trans_matrix(mat, flip_tb=True, translate=[0, height])
                logger.info("[vector] Applied transforms: " + f"{mat}") if logger else None
            
            if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
                angle = kwargs.get("rotate_angle", None)
                # if angle is not None:
                    # 通用 rotate + translate
                    # transform_cmds.append(f"{angle} rotate\n0 {-height} translate\n")

                logger.info(f"[vector] Applied transforms:  rotate={angle}") if logger else None


            if mat_pattern_cm.match(lines[mat_line_idx]):
                # 替换为 a b c d e f cm
                new_line = f"{pre}" + "{} {} {} {} {} {} cm".format(*mat) + f"{post}\n"
                lines[mat_line_idx] = new_line
            else:
                # 替换为 [a b c d e f]
                new_line = f"{pre}" + "[ {} {} {} {} {} {} ]".format(*mat) + f"{post}"
                # 保留原行其他内容
                lines[mat_line_idx] = mat_pattern_bracket.sub(new_line, lines[mat_line_idx])
            print("NEW LINE")
            print(new_line)
            logger.info(f"[vector] EPS/PS transform matrix replaced: {mat}") if logger else None

            with open(tmp_out, "w", encoding="utf-8") as f:
                f.writelines(lines)

            project_callback(cv.show_script(tmp_out, dpi=dpi)) if project_callback else None
            if save_image:
                shutil.move(tmp_out, out_path)
            else:
                out_path = None

        return out_path