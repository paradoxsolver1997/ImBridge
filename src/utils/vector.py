from PIL import Image
import os
import base64
from reportlab.pdfgen import canvas
import subprocess
from typing import Optional, Tuple
import tempfile
import shutil

from src.utils.logger import Logger
from src.utils.commons import check_tool
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_dir_existence
from src.utils.commons import confirm_single_page

import src.utils.converter as cv



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
            img = Image.open(out_path)
            img.load()  # 强制读取到内存
        return img
    except Exception as ve:
        raise ve


def show_svg(in_path: str) -> Image.Image:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = cv.svg2raster(in_path, tmp_dir, out_fmt=".png")
            img = Image.open(out_path)
            img.load()  # 强制读取到内存
            img = cv.remove_alpha_channel(img)
        return img
    except Exception as ve:
        raise ve

def get_svg_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    try:
        tree = ET.parse(in_path)
        root = tree.getroot()
        width = int(float(root.get("width")))
        height = int(float(root.get("height")))
        return width, height
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")


def get_script_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    """
    获取脚本类矢量文件（pdf/ps/eps）的页面尺寸，单位pt。
    支持PDF（用fitz）和PS/EPS（用BoundingBox）。
    """
    import os
    ext = os.path.splitext(in_path)[1].lower()
    if ext == ".pdf":
        import fitz
        with fitz.open(in_path) as doc:
            page = doc[0]
            width_pt = page.rect.width
            height_pt = page.rect.height
        return width_pt, height_pt
    elif ext in (".ps", ".eps"):
        with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
            import re
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
        return width_pt, height_pt
    else:
        return None, None


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
