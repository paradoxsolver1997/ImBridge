# 新增：确认输出目录存在，否则询问用户是否创建
import os
import tkinter as tk
from tkinter import messagebox
import subprocess
import shutil
import json
import importlib
import numpy as np
from typing import Optional
import xml.etree.ElementTree as ET
from PIL import Image

bitmap_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
vector_formats = [".svg", ".pdf", ".eps", ".ps"]
script_formats = [".ps", ".eps", ".pdf"]


def confirm_cropbox(cropbox: tuple[float, float, float, float], canvas_size: tuple[int, int]) -> bool:
    """
    Confirm that the cropbox is within the canvas size.
    cropbox: (left, top, right, bottom)
    canvas_size: (width, height)
    Returns True if valid, False otherwise.
    """
    left, top, right, bottom = cropbox
    width, height = canvas_size
    if left < 0 or top < 0 or right > width or bottom > height:
        root = tk._default_root or tk.Tk()
        root.withdraw()
        msg = (
            f"The specified crop box {cropbox} is out of bounds for the canvas size {canvas_size}.\n"
            "Please adjust the crop box to fit within the image dimensions."
        )
        messagebox.showwarning("Invalid Crop Box", msg)
        if not tk._default_root:
            root.destroy()
        return False
    return True


def confirm_single_page(in_path: str) -> bool:
    """
    Check if the input file is single-page. If PDF/PS and multi-page, prompt user for confirmation.
    Returns True if single-page or user chooses to continue, False otherwise.
    """
    import os
    import tkinter as tk
    from tkinter import messagebox
    ext = os.path.splitext(in_path)[1].lower()
    # Only PDF and PS can be multi-page
    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(in_path)
            n_pages = doc.page_count
            doc.close()
        except Exception:
            n_pages = 1  # Fallback: treat as single page if cannot open
        if n_pages > 1:
            root = tk._default_root or tk.Tk()
            root.withdraw()
            msg = (
                f"The PDF file contains {n_pages} pages. Only single-page files are supported.\n"
                "If you continue, only the last page will be saved and previous pages will be overwritten.\n"
                "It is recommended to split the file into single pages before proceeding.\n\nContinue anyway?"
            )
            resp = messagebox.askyesno("Multi-page PDF Detected", msg)
            if not tk._default_root:
                root.destroy()
            return resp
        else:
            return True
    elif ext == ".ps":
        # Heuristic: count 'showpage' operators
        try:
            with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            n_pages = content.count("showpage")
        except Exception:
            n_pages = 1
        if n_pages > 1:
            root = tk._default_root or tk.Tk()
            root.withdraw()
            msg = (
                f"The PS file contains {n_pages} pages (detected by 'showpage'). Only single-page files are supported.\n"
                "If you continue, only the last page will be saved and previous pages will be overwritten.\n"
                "It is recommended to split the file into single pages before proceeding.\n\nContinue anyway?"
            )
            resp = messagebox.askyesno("Multi-page PS Detected", msg)
            if not tk._default_root:
                root.destroy()
            return resp
        else:
            return True
    else:
        # Other formats are always treated as single-page
        return True

def confirm_dir_existence(out_dir: str) -> bool:
    """
    检查out_dir是否存在，不存在则弹窗询问用户是否创建。
    若用户同意则递归创建，创建失败则警告并返回False。
    若用户拒绝则返回False。
    """
    if os.path.exists(out_dir):
        return True
    # 弹窗询问
    root = None
    try:
        root = tk._default_root or tk.Tk()
        root.withdraw()
        resp = messagebox.askyesno("Create Directory", f"Output directory does not exist:\n{out_dir}\nCreate it?")
        if resp:
            try:
                os.makedirs(out_dir, exist_ok=True)
                if os.path.exists(out_dir):
                    return True
                else:
                    messagebox.showwarning("Create Directory Failed", f"Failed to create directory:\n{out_dir}\nPlease choose another output directory.")
                    return False
            except Exception as e:
                messagebox.showwarning("Create Directory Failed", f"Failed to create directory:\n{out_dir}\nError: {e}\nPlease choose another output directory.")
                return False
        else:
            return False
    finally:
        # 只在本函数创建的root才销毁
        if root and not tk._default_root:
            root.destroy()

def confirm_overwrite(out_path: str) -> bool:
    if os.path.exists(out_path):
        return messagebox.askyesno(
            "File Exists", f"File already exists:\n{out_path}\nOverwrite?"
        )
    return True

def check_tool(tool_key: str) -> bool:
    # DLL detection
    if tool_key.lower().endswith(".dll"):
        for p in os.environ.get("PATH", "").split(os.pathsep):
            if os.path.exists(os.path.join(p, tool_key)):
                return True
        return False
    """
    Check if a single tool is available.
    """

    tool_list_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "configs",
        "tool_list.json",
    )
    with open(tool_list_path, "r", encoding="utf-8") as f:
        tool_list = json.load(f)
    tool = next((t for t in tool_list if t["key"] == tool_key), None)
    if tool:
        if tool["type"] == "exe" and tool.get("executables"):
            exe_path = None
            for exe_name in tool["executables"]:
                exe_path = shutil.which(exe_name)
                if exe_path:
                    break
            if not exe_path:
                return False
            # Optional: Further validation (e.g. ghostscript --version)
            if tool["key"] == "ghostscript":
                try:
                    proc = subprocess.run(
                        [exe_path, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=2,
                    )
                    if proc.returncode == 0:
                        return True
                except Exception:
                    try:
                        proc = subprocess.run(
                            [exe_path, "-v"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=2,
                        )
                        if proc.returncode == 0:
                            return True
                    except Exception:
                        return False
                return False
            else:
                return True
        elif tool["type"] == "python":
            # 智能检测所有python依赖项
            import_name = tool.get("executables")[0] or tool["executables"][0]
            try:
                return importlib.util.find_spec(import_name) is not None
            except Exception:
                return False
        else:
            return False
    # If tool_list.json does not define the key, try to detect it为Python包
    try:
        if tool_key == "pymupdf":
            return importlib.util.find_spec("fitz") is not None
        return importlib.util.find_spec(tool_key) is not None
    except Exception:
        return False

def get_raster_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    try:
        img = Image.open(in_path)
        return img.size
    except Exception:
        raise 

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
