from PIL import Image
import os
import base64
from reportlab.pdfgen import canvas
import subprocess
from typing import Optional
import tempfile
import shutil
from pillow_heif import register_heif_opener

from src.utils.logger import Logger
from src.utils.commons import check_tool
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_dir_existence
from src.utils.commons import confirm_single_page

import src.utils.raster as rst
from src.utils.commons import heif_formats

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
            if in_fmt in heif_formats:
                register_heif_opener()
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
            if in_fmt in heif_formats:
                register_heif_opener()
            img = Image.open(in_path)
            if out_fmt == ".eps":
                # EPS embedding can use Pillow to save as EPS, ensure mode is RGB or L
                img = rst.remove_alpha_channel(img)
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
                # ps/eps with -dEPSCrop, pdf with -dUseCropBox
                crop_flag = "-dEPSCrop" if in_fmt in (".ps", ".eps") else "-dUseCropBox"
                gs_cmd = [
                    gs,
                    "-dSAFER",
                    "-dBATCH",
                    "-dNOPAUSE",
                    crop_flag,
                    f"-sDEVICE={device}",
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
    """Convert raster image to SVG by embedding as base64 PNG."""
    try:
        # 生成SVG
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = in_fmt.lstrip(".") + "2" + "svg"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}.svg")

        if in_fmt in heif_formats:
            register_heif_opener()
        with Image.open(in_path) as img:
            original_mode = img.mode
            w, h = img.size

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = os.path.join(tmp_dir, "temp.png")
                if original_mode in ('RGBA', 'LA', 'PA'):
                    if original_mode != 'RGBA':
                        img = img.convert('RGBA')
                    img.save(tmp_path, 'PNG')
                    mime_type = 'image/png'
                else:
                    img.convert('RGB').save(tmp_path, 'PNG')
                    mime_type = 'image/png'

                with open(tmp_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
        
        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(
                    f"""<?xml version="1.0" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
<image href="data:{mime_type};base64,{b64}" x="0" y="0" width="{w}" height="{h}" />
</svg>"""
                )
            logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
            return out_path
            
    except Exception as e:
        logger.error(f"SVG conversion failed: {e}") if logger else None
        return None


def svg2raster(in_path: str, out_dir: str, out_fmt: str, dpi: int = None, logger: Optional[Logger] = None, **kwargs) -> Optional[str]:
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
            cairosvg.svg2png(url=in_path, write_to=out_path, dpi=dpi)
        elif out_fmt in (".jpg", ".jpeg"):
            tmp_png = os.path.join(tmp_dir, "temp.png")
            cairosvg.svg2png(url=in_path, write_to=tmp_png, dpi=dpi)
            Image.open(tmp_png).convert("RGB").save(out_path, quality=kwargs.get("quality", 95))
        elif out_fmt == ".tiff":
            tmp_png = os.path.join(tmp_dir, "temp.png")
            cairosvg.svg2png(url=in_path, write_to=tmp_png, dpi=dpi)
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
            if out_fmt == ".pdf":
                cairosvg.svg2pdf(url=in_path, write_to=tmp_path, dpi=dpi)
            elif out_fmt in (".eps", ".ps"):
                cairosvg.svg2ps(url=in_path, write_to=tmp_path, dpi=dpi)
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
    crop_flag = "-dEPSCrop" if in_fmt in (".ps", ".eps") else "-dUseCropBox"
    device = device_map[out_fmt]
    if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
        cmd = [
            gs,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            crop_flag,
            f"-sDEVICE={device}",
            f"-sOutputFile={out_path}",
            in_path,
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
        return out_path


def pdf2script(in_path: str, out_dir: str, out_fmt: str, logger: Optional[Logger] = None):
    """
    Use pdf2ps to convert PDF to PS or EPS.
    
    Parameters:
        in_path (str): Input PDF file path
        out_path (str): Output PS/EPS file path
        out_fmt (str): ".ps" or ".eps"
    """
    if not check_tool("pdftops"):
        raise RuntimeError("pdftops not found in PATH; required for PDF to PS/EPS conversion")
    pdftops = shutil.which("pdftops")
    if not pdftops:
        raise RuntimeError("pdftops executable not found in PATH")

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = ".pdf"
    suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")

    # Check format parameter
    if out_fmt not in (".ps", ".eps"):
        raise ValueError("out_fmt must be '.ps' or '.eps'")

    # Automatically correct output file suffix
    if not out_path.endswith(out_fmt):
        out_path = os.path.splitext(out_path)[0] + out_fmt

    cmd = [pdftops]
    if out_fmt == ".eps":
        cmd.append("-eps")
    cmd.extend([in_path, out_path])

    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Conversion completed: {out_path}") if logger else None
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed: {e}") if logger else None
        raise

    return out_path