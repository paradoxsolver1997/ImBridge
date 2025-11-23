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
"""Bitmap conversion utilities.

Uses Pillow for most bitmap format conversions and pillow-heif for HEIC/HEIF decoding.
"""

device_map = {
    ".pdf": "pdfwrite",
    ".eps": "eps2write",
    ".ps": "ps2write",
    ".png": "pngalpha",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".tiff": "tiff24nc",
}

def raster_convert(
    in_path: str,
    out_dir: str,
    out_fmt: str = None,
    logger: Optional[Logger] = None,
    **kwargs,
) -> Optional[str]:
    """Convert between raster images using Pillow."""
    try:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        out_fmt = out_fmt if out_fmt is not None else in_fmt
        suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            img = Image.open(in_path)
            # For formats like JPEG, ensure RGB
            if img.mode in ("RGBA", "P") and out_fmt in (".jpg", ".jpeg",):
                img = img.convert("RGB")
            img.save(out_path, quality=kwargs.get("quality", 95))
            logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
            return out_path
    except Exception as e:
        logger.error(f'Format Conversion of {os.path.basename(in_path)} failed due to "{e}".') if logger else None


def raster2script(
    in_path: str,
    out_dir: str,
    out_fmt: str,
    dpi: int,
    logger: Optional[Logger] = None,
) -> Optional[str]:
    """
    Embed bitmap into vector graphics (svg/pdf/eps) as <image> tag or embedded image.
    """
    try:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
        
        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            img = Image.open(in_path)
            if out_fmt == ".eps":
                # EPS embedding can use Pillow to save as EPS, ensure mode is RGB or L
                img = remove_alpha_channel(img)
                img.save(out_path, format="EPS", dpi=(dpi, dpi))
                logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
                return out_path
            elif out_fmt in (".pdf", ".ps"):
                w, h = img.size
                # Calculate physical size (inches) based on pixel dimensions and dpi
                w_pt = w / dpi * 72
                h_pt = h / dpi * 72
                # Convert physical size (inches) to pt (1pt = 1/72 inches)
                c = canvas.Canvas(out_path, pagesize=(w_pt, h_pt))
                c.drawImage(in_path, 0, 0, width=w_pt, height=h_pt)
                c.showPage()
                c.save()
                logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
                return out_path
            else:
                raise RuntimeError(f"Unsupported vector format: {out_fmt}")
    except Exception as e:
        logger.error(f'Format Conversion of {os.path.basename(in_path)} failed due to "{e}".') if logger else None


def script2raster(
    in_path: str,
    out_dir: str,
    out_fmt: str,
    dpi: int,
    logger: Optional[Logger] = None,
) -> Optional[str]:
    """
    Convert vector graphics (ps/eps/pdf/svg) to high-definition bitmap (e.g. png/jpg/tiff) using Ghostscript or cairosvg.
    """
    try:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
            
        if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            if in_fmt in (".ps", ".eps", ".pdf"):
                gs = shutil.which("gswin64c") if check_tool("ghostscript") else None
                if not gs:
                    raise RuntimeError(
                        "Ghostscript executable not found; provide path in config or ensure it is on PATH"
                    )
                device = device_map.get(out_fmt, ".pngalpha")
                # ps/eps 用 -dEPSCrop，pdf 用 -dUseCropBox
                crop_flag = "-dEPSCrop" if in_fmt in (".ps", ".eps") else "-dUseCropBox"
                gs_cmd = [
                    gs,
                    "-dSAFER",
                    "-dBATCH",
                    "-dNOPAUSE",
                    f"-sDEVICE={device}",
                    crop_flag,
                    f"-r{dpi}",
                    f"-sOutputFile={out_path}",
                    in_path,
                ]
                subprocess.run(gs_cmd, check=True)
                logger.info(
                    f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded."
                ) if logger else None
                return out_path
            else:
                raise RuntimeError(f"Unsupported input format: {in_fmt}")
    except Exception as e:
        msg = f'Format Conversion of {os.path.basename(in_path)} failed due to "{e}".'
        logger.error(msg) if logger else None


def raster2svg(in_path: str, out_dir: str, logger: Optional[Logger] = None) -> Optional[str]:
    with open(in_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    mime = "image/png" if in_path.lower().endswith(".png") else "image/jpeg"
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = in_fmt.lstrip(".") + "2" + "svg"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}.svg")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            f"""<?xml version="1.0" standalone="no"?>
                    <svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
                    <image href="data:{mime};base64,{b64}" x="0" y="0" width="{w}" height="{h}" />
                    </svg>
                    """
        )
    logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
    return out_path


def svg2raster(in_path: str, out_dir: str, out_fmt: str, logger: Optional[Logger] = None, **kwargs) -> Optional[str]:
    try:
        import cairosvg
    except Exception as e:
        raise RuntimeError(
            "cairosvg is required for svg -> bitmap conversion"
        ) from e
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")

    assert in_fmt == ".svg"

    with tempfile.TemporaryDirectory() as tmp_dir:
        if out_fmt == ".png":
            cairosvg.svg2png(url=in_path, write_to=out_path)
        elif out_fmt in (".jpg", ".jpeg"):
            tmp_png = os.path.join(tmp_dir, "temp.png")
            cairosvg.svg2png(url=in_path, write_to=tmp_png)
            Image.open(tmp_png).convert("RGB").save(out_path, quality=kwargs.get("quality", 95))
        elif out_fmt == ".tiff":
            tmp_png = os.path.join(tmp_dir, "temp.png")
            cairosvg.svg2png(url=in_path, write_to=tmp_png)
            Image.open(tmp_png).save(out_path, format="TIFF")
        else:
            raise RuntimeError(f"Unsupported bitmap format: {out_fmt}")
        logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
    return out_path


def script2svg(in_path: str, out_dir: str, logger: Optional[Logger] = None) -> Optional[str]:
    """
    支持ps/eps/pdf转svg，pdf需先转ps。
    in_path: 输入文件（.ps/.eps/.pdf）
    out_dir: 输出目录
    """
    if not check_tool("pstoedit"):
        raise RuntimeError("pstoedit not found in PATH; required for script -> svg")
    pstoedit = shutil.which("pstoedit")

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = in_fmt.lstrip(".") + "2" + "svg"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}.svg")

    try:
        if in_fmt == ".pdf":
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_ps, _ = script_convert(in_path, tmp_dir, ".ps")
                subprocess.run([pstoedit, "-f", "svg", temp_ps, out_path], check=True)
            # 清理临时ps
        else:
            subprocess.run([pstoedit, "-f", "svg", in_path, out_path], check=True)
        logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
        
        return out_path
    except Exception as e:
        logger.error(f"Format Conversion failed: {e}") if logger else None
        raise


def svg2script(in_path: str, out_dir: str, out_fmt: str, dpi: int, logger: Optional[Logger] = None) -> Optional[str]:
    """
    将SVG转为PDF/EPS/PS，并用Ghostscript清洗，最后删除缓存文件。
    in_path: SVG文件路径
    out_dir: 输出目录
    out_fmt: 目标格式（.pdf/.eps/.ps）
    dpi: 输出分辨率（仅影响尺寸标注，默认96）
    """
    try:
        import cairosvg
    except Exception as e:
        raise RuntimeError("cairosvg is required for svg -> script conversion") from e
    assert out_fmt in (".pdf", ".eps", ".ps")

    if confirm_dir_existence(out_dir):

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, "temp" + out_fmt)
            # SVG转目标格式到临时文件
            if out_fmt == ".pdf":
                cairosvg.svg2pdf(url=in_path, write_to=tmp_path, dpi=dpi)
            elif out_fmt in (".eps", ".ps"):
                cairosvg.svg2ps(url=in_path, write_to=tmp_path, dpi=dpi)
            # Ghostscript清洗
            # out_path, _ = script_convert(tmp_path, out_dir, out_fmt)
            base_name = os.path.splitext(os.path.basename(in_path))[0]
            in_fmt = os.path.splitext(in_path)[1].lower()
            out_fmt = out_fmt if out_fmt is not None else in_fmt
            suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
            out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
            shutil.copy(tmp_path, out_path)
        msg = f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded."
        logger.info(msg) if logger else None
        return out_path


def script_convert(in_path: str, out_dir: str, out_fmt: str = None, logger: Optional[Logger] = None) -> Optional[str]:
    
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for conversion")
    gs = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    if not gs:
        raise RuntimeError("Ghostscript executable not found")
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    out_fmt = out_fmt if out_fmt is not None else in_fmt
    suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
    device = device_map[out_fmt]
    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
        cmd = [
            gs,
            "-dBATCH",
            "-dNOPAUSE",
            f"-sDEVICE={device}",
            f"-sOutputFile={out_path}",
            in_path,
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
        return out_path
        

def show_script(in_path: str, dpi: int = 96) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = script2raster(in_path, tmp_dir, out_fmt=".png", dpi=dpi)
        img = Image.open(out_path)
        img.load()  # 强制读取到内存
    return img


def show_svg(in_path: str) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = svg2raster(in_path, tmp_dir, out_fmt=".png")
        img = Image.open(out_path)
        img.load()  # 强制读取到内存
    return img


def remove_alpha_channel(img: Image.Image, bg_color=(255, 255, 255)) -> Image.Image:
    """Remove alpha channel from an image by compositing onto a background color."""
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return background
    elif img.mode != "RGB" and img.mode != "L":
        return img.convert("RGB")
    return img


def pdf2script(in_path: str, out_dir: str, out_fmt: str, logger: Optional[Logger] = None):
    """
    使用 pdf2ps 将 PDF 转换为 PS 或 EPS。
    
    参数:
        in_path (str): 输入 PDF 文件路径
        out_path (str): 输出 PS/EPS 文件路径
        out_fmt (str): ".ps" 或 ".eps"
    """
    print("CALLED!")
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = ".pdf"
    suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")

    # 检查格式参数
    if out_fmt not in (".ps", ".eps"):
        raise ValueError("out_fmt must be '.ps' or '.eps'")

    # 自动修正输出文件后缀
    if not out_path.endswith(out_fmt):
        out_path = os.path.splitext(out_path)[0] + out_fmt

    cmd = ["pdftops"]

    # EPS 模式必须加 -eps
    if out_fmt == ".eps":
        cmd.append("-eps")

    # 输入/输出
    cmd.extend([in_path, out_path])

    try:
        subprocess.run(cmd, check=True)
        print(f"转换完成：{out_path}")
    except subprocess.CalledProcessError as e:
        print("转换失败:", e)
        raise

    return out_path