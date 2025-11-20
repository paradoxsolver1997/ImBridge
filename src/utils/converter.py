"""Bitmap conversion utilities.

Uses Pillow for most bitmap format conversions and pillow-heif for HEIC/HEIF decoding.
"""

from PIL import Image
import os
import base64
from reportlab.pdfgen import canvas
import subprocess
from typing import Optional, Dict, Any, Callable
import tempfile
import shutil
import re
from xml.etree import ElementTree as ET
import json
import importlib


def remove_alpha_channel(img: Image.Image, bg_color=(255, 255, 255)) -> Image.Image:
    """Remove alpha channel from an image by compositing onto a background color."""
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return background
    elif img.mode != "RGB" and img.mode != "L":
        return img.convert("RGB")
    return img


def bitmap_to_bitmap(
    in_path: str,
    out_path: str,
    quality: int = 95,
    log_fun: Optional[Callable[[str], None]] = None,
) -> None:
    """Convert a single image file to another raster format using Pillow."""
    try:
        img = Image.open(in_path)
        # For formats like JPEG, ensure RGB
        if img.mode in ("RGBA", "P") and os.path.splitext(out_path)[1].lower() in (
            ".jpg",
            ".jpeg",
        ):
            img = img.convert("RGB")
        img.save(out_path, quality=quality)
        if log_fun:
            log_fun(
                f"B2B Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded."
            )
    except Exception as e:
        if log_fun:
            log_fun(
                f'B2B Conversion of {os.path.basename(in_path)} failed due to "{e}".'
            )


def embed_bitmap_to_vector(
    in_path: str,
    out_path: str,
    dpi: int = 300,
    log_fun: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Embed bitmap into vector graphics (svg/pdf/eps) as <image> tag or embedded image.
    """
    try:
        img = Image.open(in_path)
        w, h = img.size
        # Calculate physical size (inches) based on pixel dimensions and dpi
        w_pt = w / dpi * 72
        h_pt = h / dpi * 72

        fmt = os.path.splitext(out_path)[1].lower()
        if fmt == ".svg":
            with open(in_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            mime = "image/png" if in_path.lower().endswith(".png") else "image/jpeg"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(
                    f"""<?xml version="1.0" standalone="no"?>
                            <svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
                            <image href="data:{mime};base64,{b64}" x="0" y="0" width="{w}" height="{h}" />
                            </svg>
                            """
                )
        elif fmt in (".pdf", ".ps"):
            # Convert physical size (inches) to pt (1pt = 1/72 inches)
            c = canvas.Canvas(out_path, pagesize=(w_pt, h_pt))
            c.drawImage(in_path, 0, 0, width=w_pt, height=h_pt)
            c.showPage()
            c.save()
        elif fmt == ".eps":
            # EPS embedding can use Pillow to save as EPS, ensure mode is RGB or L
            img = remove_alpha_channel(img)
            img.save(out_path, format="EPS", dpi=(dpi, dpi))
        else:
            raise RuntimeError(f"Unsupported vector format: {fmt}")
        if log_fun:
            log_fun(
                f"B2V Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded."
            )
    except Exception as e:
        if log_fun:
            log_fun(
                f'B2V Conversion of {os.path.basename(in_path)} failed due to "{e}".'
            )


def bmp_to_vector(
    in_path: str, 
    out_path: str, 
    log_fun: Optional[Callable[[str], None]] = None
) -> None:
    """
    Convert BMP bitmap to vector graphics (eps/svg/pdf/ps) using potrace.exe.
    Only supports grayscale or black-and-white BMP.
    out_fmt: eps/svg/pdf/ps
    """
    out_fmt = os.path.splitext(out_path)[1].lower().lstrip('.')
    potrace_exe = None
    if check_tool('potrace'):
        potrace_exe = shutil.which('potrace')
    if not potrace_exe:
        raise RuntimeError('potrace.exe not found in PATH; please install and configure the environment variable')

    if out_fmt not in ['eps', 'svg', 'pdf', 'ps']:
        raise RuntimeError(f'Unsupported output format for potrace: {out_fmt}')
    # potrace only supports BMP input

    ext = os.path.splitext(in_path)[1].lower()
    if ext != '.bmp':
        # Automatically convert to bmp temporary file
        with Image.open(in_path) as im:
            tmp_dir = tempfile.gettempdir()
            tmp_bmp = os.path.join(tmp_dir, f'tmp_potrace_{os.getpid()}.bmp')
            im.convert('L').save(tmp_bmp, format='BMP')
            log_fun(f'Converted {in_path} to temporary BMP for potrace.') if log_fun else None
            in_path = tmp_bmp
    cmd = [potrace_exe, in_path, '-o', out_path, '-b', out_fmt.lower()]
    try:
        subprocess.run(cmd, check=True)
        log_fun(f'potrace.exe converted {os.path.basename(in_path)} to {os.path.basename(out_path)} successfully.') if log_fun else None
    except Exception as e:
        raise RuntimeError(f'potrace.exe failed: {e}')



def vector_to_bitmap(
    in_path: str,
    out_path: str,
    dpi: int = 600,
    gs_path: Optional[str] = None,
    log_fun: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Convert vector graphics (ps/eps/pdf/svg) to high-definition bitmap (e.g. png/jpg/tiff) using Ghostscript or cairosvg.
    """
    try:
        ext = os.path.splitext(in_path)[1].lower()
        fmt = os.path.splitext(out_path)[1].lower()
        if ext in (".ps", ".eps", ".pdf"):
            gs = gs_path or (
                shutil.which("gswin64c") if check_tool("ghostscript") else None
            )
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
            device = device_map.get(fmt, ".pngalpha")
            gs_cmd = [
                gs,
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                f"-sDEVICE={device}",
                "-dEPSCrop",
                f"-r{dpi}",
                f"-sOutputFile={out_path}",
                in_path,
            ]
            subprocess.run(gs_cmd, check=True)
        elif ext == ".svg":
            try:
                import cairosvg
            except Exception as e:
                raise RuntimeError(
                    "cairosvg is required for svg -> bitmap conversion"
                ) from e
            if fmt == ".png":
                cairosvg.svg2png(url=in_path, write_to=out_path, dpi=dpi)
            elif fmt in (".jpg", ".jpeg"):
                tmp_png = out_path + ".tmp.png"
                cairosvg.svg2png(url=in_path, write_to=tmp_png, dpi=dpi)
                Image.open(tmp_png).convert("RGB").save(out_path, quality=95)
                remove_temp(tmp_png)
            elif fmt == ".tiff":
                tmp_png = out_path + ".tmp.png"
                cairosvg.svg2png(url=in_path, write_to=tmp_png, dpi=dpi)
                Image.open(tmp_png).save(out_path, format="TIFF")
                remove_temp(tmp_png)
            else:
                raise RuntimeError(f"Unsupported bitmap format: {fmt}")
        else:
            raise RuntimeError(f"Unsupported input format: {ext}")
        if log_fun:
            log_fun(
                f"V2B Conversion {os.path.basename(in_path)} -> {os.path.basename(out_path)} succeeded."
            )
    except Exception as e:
        if log_fun:
            log_fun(
                f'V2B Conversion of {os.path.basename(in_path)} failed due to "{e}".'
            )


def vector_to_vector(
    in_path: str, out_path: str, log_fun: Optional[Callable[[str], None]] = None
) -> None:
    # pdf -> ps: 先pdf->eps, 再eps->ps

    """
    General vector format conversion function, automatically selects tools based on input/output formats.
    Supports svg/pdf/eps/ps conversion, some paths require intermediate eps/ps.
    """
    try:
        out_fmt = os.path.splitext(out_path)[1].lower()
        ext_in = os.path.splitext(in_path)[1].lower()
        ext_out = os.path.splitext(out_path)[1].lower()
        # Normalize formats
        fmt_in = ext_in.lstrip(".")
        fmt_out = (
            ext_out.lstrip(".") if out_fmt is None else out_fmt.lstrip(".").lower()
        )

        # svg -> pdf
        if fmt_in == "svg" and fmt_out == "pdf":
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


def svg_to_pdf(svg_path: str, pdf_path: str) -> None:
    try:
        import cairosvg
    except Exception as e:
        raise RuntimeError("cairosvg is required for svg -> pdf conversion") from e
    cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)


def svg_to_eps(svg_path: str, eps_path: str) -> None:
    try:
        import cairosvg
    except Exception as e:
        raise RuntimeError("cairosvg is required for svg -> eps conversion") from e
    cairosvg.svg2ps(url=svg_path, write_to=eps_path)


def svg_to_ps(svg_path: str, ps_path: str) -> None:
    try:
        import cairosvg
    except Exception as e:
        raise RuntimeError("cairosvg is required for svg -> ps conversion") from e
    cairosvg.svg2ps(url=svg_path, write_to=ps_path)


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


def ps_eps_to_svg(ps_eps_path: str, svg_path: str) -> None:
    if not check_tool("pstoedit"):
        raise RuntimeError("pstoedit not found in PATH; required for ps/eps -> svg")
    pstoedit = shutil.which("pstoedit")
    subprocess.run([pstoedit, "-f", "svg", ps_eps_path, svg_path], check=True)


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
        if tool["type"] == "exe" and tool["executables"]:
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
        elif tool["type"] == "python" and tool["key"] == "cairosvg":
            return importlib.util.find_spec("cairosvg") is not None
        else:
            return False
    # If tool_list.json does not define the key, try to detect it as a Python package
    try:
        return importlib.util.find_spec(tool_key) is not None
    except Exception:
        return False


def remove_temp(temp_path: str, log_fun=None) -> None:
    """Remove image file from disk."""
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        if log_fun:
            log_fun(f"[vector] Failed to remove temp file {temp_path}: {e}")