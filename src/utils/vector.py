from PIL import Image
import os
import base64
import subprocess
from typing import Optional, Dict, Any, Callable, Tuple
import tempfile
import shutil
import re
import fitz  # PyMuPDF
import numpy as np
from xml.etree import ElementTree as ET

import src.utils.converter as cv
import src.utils.raster as rst
from src.utils.logger import Logger
from src.utils.commons import check_tool
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_dir_existence


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


def show_script(in_path: str, dpi: int = 96) -> Image.Image:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = cv.script2raster(in_path, tmp_dir, out_fmt=".png", dpi=dpi)
            with Image.open(out_path) as image:
                #img.load()  # 强制读取到内存
                img = image.copy()
        return img
    except Exception as ve:
        raise ve


def show_svg(in_path: str, dpi: int = None) -> Image.Image:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = cv.svg2raster(in_path, tmp_dir, out_fmt=".png", dpi=dpi)
            with Image.open(out_path) as image:
                # img.load()  # 强制读取所有数据到内存
                img = rst.remove_alpha_channel(image.copy())  # 创建副本
            img = rst.remove_alpha_channel(img)
            print(f"Loaded SVG raster image size: {img.size}")
        return img
    except Exception as ve:
        raise ve

def get_svg_view_box(in_path: str) -> tuple[Optional[float], Optional[float]]:
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(in_path)
    root = tree.getroot()
    return get_view_box_from_root(root)
    

def get_view_box_from_root(root):
    try:
        viewbox_str = root.get('viewBox')
        return tuple(map(float, viewbox_str.split()))
    except:
        return None

def get_svg_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(in_path)
    root = tree.getroot()
    full_size, unit = get_size_from_root(root)
    return full_size, unit

def get_size_from_root(root):
    try:
        match = re.search(r'(\d+\.?\d*)(\D*)', root.get("width"))  # 匹配数字（包括小数）
        if match:
            width = int(float(match.group(1)))
            unit_w = match.group(2).strip()
        match = re.search(r'(\d+\.?\d*)(\D*)', root.get("height"))  # 匹配数字（包括小数）
        if match:
            height = int(float(match.group(1)))
            unit_h = match.group(2).strip()
        if not width or not height:
            raise RuntimeError("SVG width or height attribute missing or invalid.")
        if unit_w == "":
            unit_w = "px"
        if unit_h == "":
            unit_h = "px"
        if unit_w != unit_h:
            raise RuntimeError("SVG width and height units do not match.")
        return (width, height), unit_w
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")

def get_pdf_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    try:
        with fitz.open(in_path) as doc:
            page = doc[0]
            width_pt = page.rect.width
            height_pt = page.rect.height
        return (width_pt, height_pt), "pt"
    except Exception:
            raise RuntimeError("Failed to parse PDF dimensions.")

def get_script_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    """
    获取脚本类矢量文件（pdf/ps/eps）的页面尺寸，单位pt。
    支持PDF（用fitz）和PS/EPS（用BoundingBox）。
    """
    try:
        with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
            bbox_pat = re.compile(r"^%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
            for line in f:
                m = bbox_pat.match(line)
                if m:
                    llx, lly, urx, ury = [int(m.group(i)) for i in range(1,5)]
                    width_pt = urx - llx
                    height_pt = ury - lly
                    break
            else:
                width_pt = height_pt = None
        return (width_pt, height_pt), "pt"
    except Exception:
        raise RuntimeError("Failed to parse PS/EPS dimensions.")


def compute_trans_matrix(
    base_mat: Optional[list[float, float, float, float, float, float]] = [1, 0, 0, 1, 0, 0],
    rotate_angle: Optional[float] = None,   # 度
    flip_lr: Optional[bool] = None,
    flip_tb: Optional[bool] = None,
    translate: Optional[list[float]] = None,
    scale: Optional[list[float]] = None  # [sx, sy]
) -> list[float, float, float, float, float, float]:
    """
    返回 SVG matrix(a,b,c,d,e,f)
    变换顺序: rotate -> scale -> flip -> translate
    """
    # 旋转矩阵
    B = np.array([[base_mat[0], base_mat[2], base_mat[4]],
                [base_mat[1], base_mat[3], base_mat[5]],
                [0, 0, 1]])

    if rotate_angle is not None:
        theta = np.radians(rotate_angle)
        R = np.array([[np.cos(theta), np.sin(theta), 0],
                    [-np.sin(theta), np.cos(theta), 0],
                    [0, 0, 1]])
    else:
        R = np.eye(3)

    # 缩放矩阵
    S = np.array([[scale[0], 0, 0],
                  [0, scale[1], 0],
                  [0, 0, 1]]) if scale is not None else np.eye(3)
    
    # 翻转矩阵
    if flip_lr:
        F_LR = np.array([[-1, 0, 0],
                    [0, 1, 0],
                    [0, 0, 1]])
    else:
        F_LR = np.eye(3)
    
    if flip_tb:
        F_TB = np.array([[1, 0, 0],
                    [0, -1, 0],
                    [0, 0, 1]])
    else:
        F_TB = np.eye(3)

    # 平移矩阵
    T = np.array([[1, 0, translate[0]],
                  [0, 1, translate[1]],
                  [0, 0, 1]]) if translate is not None else np.eye(3)
    
    # 依次相乘
    M = T @ R @ F_TB @ F_LR @ S @ B
    
    # 返回 SVG matrix(a,b,c,d,e,f)
    a, c, e = M[0]
    b, d, f = M[1]
    return [a, b, c, d, e, f]


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
            new_vals_str = " ".join(f"{float(x)}" for x in mat)
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



def vector_analyzer(
    in_path: str, log_fun: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Automatically analyze vector file types (pdf/eps/svg) and return quantitative features and types.
    """

    result = None
    ext = os.path.splitext(in_path)[1].lower()
    if ext == ".pdf":
        result = pdf_analyzer(in_path)
    elif ext == ".eps":
        with tempfile.TemporaryDirectory() as tmp_dir:
            svg_path, _ = cv.script2svg(in_path, tmp_dir)
            result = svg_analyzer(svg_path)
    elif ext == ".svg":
        result = svg_analyzer(in_path)
    else:
        raise RuntimeError(f"Unsupported vector file type: {ext}")
    if result is not None and log_fun:
        msg = f"[{os.path.basename(in_path)}] Type: {result['type']}, Paths: {result['num_paths']}, Images: {result['num_images']}"
        if result["images"]:
            img_desc = ", ".join(
                [
                    f"{(str(img['real_width']) if img.get('real_width') else img.get('width','?'))}x"
                    f"{(str(img['real_height']) if img.get('real_height') else img.get('height','?'))}"
                    for img in result["images"]
                ]
            )
            msg += f", Image sizes: {img_desc}"
        log_fun(msg)
    return result


def pdf_analyzer(pdf_path: str) -> Dict[str, Any]:
    """
    用 PyMuPDF 分析 PDF 文件的矢量/栅格内容，统计 path 和 image 数量及尺寸。
    """
    result = {
        "type": "unknown",
        "num_paths": 0,
        "num_images": 0,
        "images": [],
    }
    doc = fitz.open(pdf_path)
    for page in doc:
        # 统计图片
        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            w, h = pix.width, pix.height
            result["num_images"] += 1
            result["images"].append({
                "xref": xref,
                "width": w,
                "height": h,
            })
            pix = None  # 释放内存
        # 统计路径
        drawings = page.get_drawings()
        vector_ops = [d for d in drawings if d["type"] != "image"]
        path_count = len(vector_ops)

        result["num_paths"] += path_count
    # 类型判定
    if result["num_images"] > 0 and result["num_paths"] > 0:
        result["type"] = "mixed"
    elif result["num_images"] > 0:
        result["type"] = "raster"
    elif result["num_paths"] > 0:
        result["type"] = "vector"
    return result


def svg_analyzer(svg_path: str) -> Dict[str, Any]:
    """
    Analyze SVG files for pure vector, pure raster, or mixed graphics, and count paths and images.
    For <image> tags, try to get actual pixel size from href/xlink:href if possible.
    """
    import io
    result = {
        "type": "unknown",
        "num_paths": 0,
        "num_images": 0,
        "images": [],
    }
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(svg_path)
    root = tree.getroot()
    # Count paths
    paths = root.findall(".//{http://www.w3.org/2000/svg}path")
    result["num_paths"] = len(paths)
    # Count images
    images = root.findall(".//{http://www.w3.org/2000/svg}image")
    result["num_images"] = len(images)
    svg_dir = os.path.dirname(svg_path)
    for img in images:
        w = img.get("width")
        h = img.get("height")
        # 解析 href/xlink:href
        href = img.get("{http://www.w3.org/1999/xlink}href") or img.get("href")
        real_w, real_h = None, None
        if href:
            try:
                if href.startswith("data:"):
                    # Data URI
                    header, b64data = href.split(",", 1)
                    img_bytes = base64.b64decode(b64data)
                    with Image.open(io.BytesIO(img_bytes)) as im:
                        real_w, real_h = im.width, im.height
                else:
                    # 文件路径或URL（只尝试本地文件）
                    img_path = os.path.join(svg_dir, href)
                    if os.path.exists(img_path):
                        with Image.open(img_path) as im:
                            real_w, real_h = im.width, im.height
            except Exception:
                real_w, real_h = None, None
        result["images"].append({
            "width": w,
            "height": h,
            "real_width": real_w,
            "real_height": real_h,
            "href": href
        })
    # Type determination
    if result["num_images"] > 0 and result["num_paths"] > 0:
        result["type"] = "mixed"
    elif result["num_images"] > 0:
        result["type"] = "raster"
    elif result["num_paths"] > 0:
        result["type"] = "vector"
    return result

def trace_bmp_to_svg(
    in_path: str, 
    out_dir: str,
    logger: Optional[Logger] = None
) -> Optional[str]:
    """
    Convert BMP bitmap to vector graphics (eps/svg/pdf/ps) using potrace.exe.
    Only supports grayscale or black-and-white BMP.
    out_fmt: eps/svg/pdf/ps
    """
    potrace_exe = None
    if check_tool('potrace'):
        potrace_exe = shutil.which('potrace')
    if not potrace_exe:
        raise RuntimeError('potrace.exe not found in PATH; please install and configure the environment variable')

    if confirm_dir_existence(out_dir):
        out_fmt = ".svg"
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        assert in_fmt == ".bmp"
        suffix = "traced"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")

        if confirm_overwrite(out_path):
            cmd = [potrace_exe, in_path, '-o', out_path, '-s']
            try:
                subprocess.run(cmd, check=True)
                logger.info(f'potrace.exe converted {os.path.basename(in_path)} to {os.path.basename(out_path)} successfully.') if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f'potrace.exe failed: {e}')

def apply_transform(point, matrix):
    """
    对点应用仿射变换
    
    Args:
        point: (x, y) 二元组
        matrix: (a, b, c, d, e, f) 六元组变换矩阵
               对应矩阵: [a c e]
                        [b d f] 
    
    Returns:
        (new_x, new_y) 变换后的坐标
    """
    x, y = point
    a, b, c, d, e, f = matrix
    
    new_x = a * x + c * y + e
    new_y = b * x + d * y + f
    
    return (new_x, new_y)

def transform_box(
    box: Tuple[int, int, int, int], 
    mat: Tuple[float, float, float, float, float, float]): 

    anchor_1 = apply_transform((box[0], box[1]), mat)
    anchor_2 = apply_transform((box[0] + box[2], box[1] + box[3]), mat)
    x_min = int(min(anchor_1[0], anchor_2[0]))
    x_max = int(max(anchor_1[0], anchor_2[0]))
    y_min = int(min(anchor_1[1], anchor_2[1]))
    y_max = int(max(anchor_1[1], anchor_2[1]))
    box = (x_min, y_min, x_max - x_min, y_max - y_min)
    return box