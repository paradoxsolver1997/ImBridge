# 新增：确认输出目录存在，否则询问用户是否创建
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import subprocess
import shutil
import json
import importlib

import fitz

bitmap_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
vector_formats = [".svg", ".pdf", ".eps", ".ps"]
script_formats = [".ps", ".eps", ".pdf"]

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

def confirm_overwrite(out_path):
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


def remove_temp(temp_path: str) -> None:
    """Remove image file from disk."""
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        raise e


def remove_alpha_channel(img: Image.Image, bg_color=(255, 255, 255)) -> Image.Image:
    """Remove alpha channel from an image by compositing onto a background color."""
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return background
    elif img.mode != "RGB" and img.mode != "L":
        return img.convert("RGB")
    return img


def get_pdf_size_pt(pdf_path):
    with fitz.open(pdf_path) as doc:
        page = doc[0]
        width_pt = page.rect.width  # 单位: pt
        height_pt = page.rect.height
    return width_pt, height_pt


def get_ps_size_pt(ps_path):
    with open(ps_path, 'r', encoding='utf-8', errors='ignore') as f:
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