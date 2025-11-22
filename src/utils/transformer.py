from PIL import Image
import tempfile
import shutil
import os
import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
from src.utils.commons import script_formats
from src.utils.converter import script_convert

def rotate_raster_anti_clockwise(img: Image.Image, angle: float = 90) -> Image.Image:
    """
    将输入的PIL Image逆时针旋转指定角度（默认为90度），返回旋转后的Image。
    angle: 旋转角度，正值为逆时针。
    """
    return img.rotate(angle, expand=True)

def flip_raster(img: Image.Image, axis: int = 0) -> Image.Image:
    """
    翻转PIL图像。axis=0为水平翻转（左右），axis=1为垂直翻转（上下）。
    """
    if axis == 0:
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    elif axis == 1:
        return img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise ValueError("axis must be 0 (horizontal) or 1 (vertical)")

def rotate_vector(in_path: str, out_dir: str, angle: float = 90, logger=None) -> str:
    """
    对pdf/eps/ps/svg文件逆时针旋转指定角度，返回输出文件路径。
    angle: 旋转角度，正值为逆时针。
    """
    ext = os.path.splitext(in_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    suffix = f"rotated{int(angle)}"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{ext}")
    if ext == ".pdf":
        with fitz.open(in_path) as doc:
            for page in doc:
                page.set_rotation(int(angle) % 360)
            doc.save(out_path)
        if logger:
            logger.info(f"[vector] Rotated PDF saved to {out_path}")
        return out_path
    elif ext in (".ps", ".eps"):
        # 先用ghostscript标准化，再插入rotate指令
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = script_convert(in_path, tmp_dir, ext)
            with open(tmp_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            # 在%%EndProlog后插入旋转指令
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("%%EndProlog"):
                    insert_idx = i + 1
                    break
            rotate_str = f"{angle} rotate\n"
            lines.insert(insert_idx, rotate_str)
            with open(out_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        if logger:
            logger.info(f"[vector] Rotated PS/EPS saved to {out_path}")
        return out_path
    elif ext == ".svg":
        tree = ET.parse(in_path)
        root = tree.getroot()
        # 包裹原内容加g标签加transform
        g = ET.Element("g")
        for child in list(root):
            g.append(child)
            root.remove(child)
        width = root.get("width") or ""
        height = root.get("height") or ""
        g.set("transform", f"rotate({angle} {width}/2 {height}/2)")
        root.append(g)
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        if logger:
            logger.info(f"[vector] Rotated SVG saved to {out_path}")
        return out_path
    else:
        raise RuntimeError("Unsupported vector format for rotation.")

def flip_vector(in_path: str, out_dir: str, axis: int = 0, logger=None) -> str:
    """
    对pdf/eps/ps/svg文件进行水平或垂直翻转，返回输出文件路径。
    axis=0为水平，1为垂直。
    """
    ext = os.path.splitext(in_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    suffix = f"flipped{'h' if axis==0 else 'v'}"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{ext}")
    if ext == ".pdf":
        with fitz.open(in_path) as doc:
            for page in doc:
                rect = page.rect
                if axis == 0:
                    # 水平翻转
                    m = fitz.Matrix(-1, 1, rect.width, 0)
                else:
                    # 垂直翻转
                    m = fitz.Matrix(1, -1, 0, rect.height)
                page.set_transform(m)
            doc.save(out_path)
        if logger:
            logger.info(f"[vector] Flipped PDF saved to {out_path}")
        return out_path
    elif ext in (".ps", ".eps"):
        # 先用ghostscript标准化，再插入scale指令
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = script_convert(in_path, tmp_dir, ext)
            with open(tmp_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            # 在%%EndProlog后插入翻转指令
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("%%EndProlog"):
                    insert_idx = i + 1
                    break
            if axis == 0:
                scale_str = "-1 1 scale\n"
            else:
                scale_str = "1 -1 scale\n"
            lines.insert(insert_idx, scale_str)
            with open(out_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        if logger:
            logger.info(f"[vector] Flipped PS/EPS saved to {out_path}")
        return out_path
    elif ext == ".svg":
        tree = ET.parse(in_path)
        root = tree.getroot()
        g = ET.Element("g")
        for child in list(root):
            g.append(child)
            root.remove(child)
        width = root.get("width") or ""
        height = root.get("height") or ""
        if axis == 0:
            g.set("transform", f"scale(-1 1)")
        else:
            g.set("transform", f"scale(1 -1)")
        root.append(g)
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        if logger:
            logger.info(f"[vector] Flipped SVG saved to {out_path}")
        return out_path
    else:
        raise RuntimeError("Unsupported vector format for flip.")

