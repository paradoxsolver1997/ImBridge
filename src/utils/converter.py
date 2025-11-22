from PIL import Image
import os
import base64
from reportlab.pdfgen import canvas
import subprocess
from typing import Optional
import tempfile
import shutil

from src.utils.logger import Logger
from src.utils.commons import check_tool
from src.utils.commons import remove_alpha_channel
from src.utils.commons import remove_temp
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_dir_existence
"""Bitmap conversion utilities.

Uses Pillow for most bitmap format conversions and pillow-heif for HEIC/HEIF decoding.
"""

device_map = {
    ".pdf": "pdfwrite",
    ".eps": "eps2write",
    ".ps": "ps2write"
}

def raster_convert(
    in_path: str,
    out_dir: str,
    out_fmt: str,
    logger: Optional[Logger] = None,
    **kwargs,
) -> Optional[str]:
    """Convert between raster images using Pillow."""
    if confirm_dir_existence(out_dir):
        try:
            base_name = os.path.splitext(os.path.basename(in_path))[0]
            in_fmt = os.path.splitext(in_path)[1].lower()
            suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
            out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
            if confirm_overwrite(out_path):
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
    if confirm_dir_existence(out_dir):
        try:
            base_name = os.path.splitext(os.path.basename(in_path))[0]
            in_fmt = os.path.splitext(in_path)[1].lower()
            suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
            out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
            
            if confirm_overwrite(out_path):
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
    if confirm_dir_existence(out_dir):
        try:
            base_name = os.path.splitext(os.path.basename(in_path))[0]
            in_fmt = os.path.splitext(in_path)[1].lower()
            suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
            out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
                
            if confirm_overwrite(out_path):
                if in_fmt in (".ps", ".eps", ".pdf"):
                    gs = shutil.which("gswin64c") if check_tool("ghostscript") else None
                    if not gs:
                        raise RuntimeError(
                            "Ghostscript executable not found; provide path in config or ensure it is on PATH"
                        )
                    device_map = {
                        ".png": "pngalpha",
                        ".jpg": "jpeg",
                        ".jpeg": "jpeg",
                        ".tiff": "tiff24nc",
                    }
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

'''
def v2v(
    in_path: str, out_path: str, log_fun: Optional[Callable[[str], None]] = None
) -> None:
    # pdf -> ps: 先pdf->eps, 再eps->ps

    """
    General vector format conversion function, automatically selects tools based on input/output formats.
    Supports svg/pdf/eps/ps conversion, some paths require intermediate eps/ps.
    """
    if confirm_overwrite(out_path):
        try:
            out_fmt = os.path.splitext(out_path)[1].lower()
            ext_in = os.path.splitext(in_path)[1].lower()
            ext_out = os.path.splitext(out_path)[1].lower()
            # Normalize formats
            fmt_in = ext_in.lstrip(".")
            fmt_out = (
                ext_out.lstrip(".") if out_fmt is None else out_fmt.lstrip(".").lower()
            )

            # eps -> eps
            if fmt_in == "eps" and fmt_out == "eps":
                wash_eps_ps(in_path, out_path)
            # ps -> ps
            elif fmt_in == "ps" and fmt_out == "ps":
                wash_eps_ps(in_path, out_path)
            # pdf -> pdf
            elif fmt_in == "pdf" and fmt_out == "pdf":
                import shutil
                shutil.copy2(in_path, out_path)
            # svg -> pdf
            elif fmt_in == "svg" and fmt_out == "pdf":
                svg_to_pdf(in_path, out_path)
            # svg -> eps
            elif fmt_in == "svg" and fmt_out == "eps":
                svg_to_eps(in_path, out_path)
            # svg -> ps
            elif fmt_in == "svg" and fmt_out == "ps":
                svg_to_ps(in_path, out_path)
            # eps -> pdf
            elif fmt_in in ("ps", "eps") and fmt_out == "pdf":
                ps_eps_to_pdf(in_path, out_path)
            # ps/eps -> svg
            elif fmt_in in ("ps", "eps") and fmt_out == "svg":
                ps_eps_to_svg(in_path, out_path)
            # eps -> ps
            elif fmt_in == "eps" and fmt_out == "ps":
                eps_to_ps(in_path, out_path)
            # ps -> eps
            elif fmt_in == "ps" and fmt_out == "eps":
                ps_to_eps(in_path, out_path)
            # pdf -> eps
            elif fmt_in == "pdf" and fmt_out == "eps":
                pdf_to_eps(in_path, out_path)
            # pdf -> ps
            elif fmt_in == "pdf" and fmt_out == "ps":
                pdf_to_ps(in_path, out_path)
            # pdf -> ps -> svg
            elif fmt_in == "pdf" and fmt_out == "svg":
                with tempfile.TemporaryDirectory() as td:
                    tmp_eps = os.path.join(td, "tmp.eps")
                    pdf_to_ps(in_path, tmp_eps)
                    ps_eps_to_svg(tmp_eps, out_path)
            else:
                raise RuntimeError(f"Unsupported vector conversion: {fmt_in} -> {fmt_out}")
            if log_fun:
                log_fun(
                    f"V2V Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded."
                )
        except Exception as e:
            if log_fun:
                log_fun(
                    f'V2V Conversion of {os.path.basename(in_path)} failed due to "{e}".'
                )
'''

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

    if out_fmt == ".png":
        cairosvg.svg2png(url=in_path, write_to=out_path)
    elif out_fmt in (".jpg", ".jpeg"):
        tmp_png = out_path + ".tmp.png"
        cairosvg.svg2png(url=in_path, write_to=tmp_png)
        Image.open(tmp_png).convert("RGB").save(out_path, quality=kwargs.get("quality", 95))
        remove_temp(tmp_png)
    elif out_fmt == ".tiff":
        tmp_png = out_path + ".tmp.png"
        cairosvg.svg2png(url=in_path, write_to=tmp_png)
        Image.open(tmp_png).save(out_path, format="TIFF")
        remove_temp(tmp_png)
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
            tmp_dir = tempfile.gettempdir()
            temp_ps = script_convert(in_path, tmp_dir, ".ps")
            subprocess.run([pstoedit, "-f", "svg", temp_ps, out_path], check=True)
            # 清理临时ps
            remove_temp(temp_ps)
        else:
            subprocess.run([pstoedit, "-f", "svg", in_path, out_path], check=True)
        logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
        return out_path
    except Exception as e:
        logger.error(f"Format Conversion failed: {e}") if logger else None
        raise
'''
def ps_eps_to_pdf(eps_path: str, pdf_path: str) -> None:

    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for eps->pdf")
    gs = shutil.which("gswin64c")
    subprocess.run(
        [
            gs,
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            f"-sOutputFile={pdf_path}",
            eps_path,
        ],
        check=True,
    )



def eps_to_ps(eps_path: str, ps_path: str) -> None:
    """Convert EPS to PS using Ghostscript if available."""
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for eps->ps")
    gs = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    if not gs:
        raise RuntimeError("Ghostscript executable not found")
    cmd = [
        gs,
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=ps2write",
        f"-sOutputFile={ps_path}",
        eps_path,
    ]
    subprocess.run(cmd, check=True)


def ps_to_eps(ps_path: str, eps_path: str) -> None:
    """Convert PS to EPS using Ghostscript if available."""
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for ps->eps")
    gs = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    if not gs:
        raise RuntimeError("Ghostscript executable not found")
    cmd = [
        gs,
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=eps2write",
        f"-sOutputFile={eps_path}",
        ps_path,
    ]
    subprocess.run(cmd, check=True)


def pdf_to_eps(pdf_path: str, eps_path: str) -> None:
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for pdf->eps")
    gs = shutil.which("gswin64c")
    subprocess.run(
        [
            gs,
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=eps2write",
            f"-sOutputFile={eps_path}",
            pdf_path,
        ],
        check=True,
    )


def pdf_to_ps(pdf_path: str, ps_path: str) -> None:
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for pdf->ps")
    gs = shutil.which("gswin64c")
    subprocess.run(
        [
            gs,
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=ps2write",
            f"-sOutputFile={ps_path}",
            pdf_path,
        ],
        check=True,
    )

def wash_eps_ps(in_path: str, out_path: str) -> None:
    """
    Clean (normalize) an EPS or PS file using Ghostscript.
    EPS 用 eps2write，PS 用 ps2write，输出格式与输入一致。
    """
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for EPS/PS cleaning")
    gs = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    if not gs:
        raise RuntimeError("Ghostscript executable not found")
    ext = os.path.splitext(in_path)[1].lower()
    if ext == ".eps":
        device = "eps2write"
    elif ext == ".ps":
        device = "ps2write"
    else:
        raise RuntimeError("Input file must be .eps or .ps")
    cmd = [
        gs,
        "-dBATCH",
        "-dNOPAUSE",
        f"-sDEVICE={device}",
        f"-sOutputFile={out_path}",
        in_path,
    ]
    subprocess.run(cmd, check=True)
'''


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

        with tempfile.NamedTemporaryFile(suffix=out_fmt, delete=False) as tmpf:
            tmp_path = tmpf.name
        # SVG转目标格式到临时文件
        if out_fmt == ".pdf":
            cairosvg.svg2pdf(url=in_path, write_to=tmp_path, dpi=dpi)
        elif out_fmt in (".eps", ".ps"):
            cairosvg.svg2ps(url=in_path, write_to=tmp_path, dpi=dpi)
        # Ghostscript清洗
        out_path = script_convert(tmp_path, out_dir, out_fmt)
        # 删除缓存
        remove_temp(tmp_path)
        logger.info(f"Format Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded.") if logger else None
        return out_path

def script_convert(in_path: str, out_dir: str, out_fmt: str, logger: Optional[Logger] = None) -> Optional[str]:
    
    if not check_tool("ghostscript"):
        raise RuntimeError("Ghostscript not found in PATH; required for conversion")
    gs = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    if not gs:
        raise RuntimeError("Ghostscript executable not found")
    
    if confirm_dir_existence(out_dir):
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = in_fmt.lstrip(".") + "2" + out_fmt.lstrip(".")
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{out_fmt}")
        device = device_map[out_fmt]
        if confirm_overwrite(out_path):
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