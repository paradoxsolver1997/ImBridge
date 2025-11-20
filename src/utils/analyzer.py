from PIL import Image
import os
import base64
from typing import Optional, Dict, Any, Callable
import tempfile
from xml.etree import ElementTree as ET

from src.utils.converter import ps_eps_to_svg


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
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
            svg_path = tmp_svg.name
        try:
            ps_eps_to_svg(in_path, svg_path)
            result = svg_analyzer(svg_path)
        finally:
            if os.path.exists(svg_path):
                os.remove(svg_path)
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
    import fitz  # PyMuPDF
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