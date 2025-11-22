from PIL import Image
from typing import Optional, Tuple
import os
import tempfile
import subprocess
import shutil
import numpy as np

from src.utils.logger import Logger
import src.utils.converter as cv

from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_dir_existence
from src.utils.commons import check_tool


def trace_image(in_path: str, out_dir: str, show_image: bool = False, save_image: bool = True, logger: Optional[Logger] = None) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    if confirm_dir_existence(out_dir):
        if os.path.getsize(in_path) > 200 * 1024:
            raise RuntimeError(f"File too large (>200K): {os.path.basename(in_path)}")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            in_fmt = os.path.splitext(in_path)[1].lower()
            if in_fmt != '.bmp':
                # Automatically convert to bmp temporary file
                temp_bmp, _ = cv.raster_convert(in_path, tmp_dir, out_fmt='.bmp', logger=logger)
                bmp_path, _ = grayscale_image(temp_bmp, tmp_dir, binarize=True, show_image=False, save_image=True, logger=logger)
            else:
                bmp_path, _ = grayscale_image(in_path, tmp_dir, binarize=True, show_image=False, save_image=True, logger=logger)
            if save_image:
                out_path = trace_bmp_to_svg(bmp_path, out_dir, logger=logger)
                img = cv.show_svg(out_path) if show_image else None
                logger.info(f'Tracing {os.path.basename(in_path)} successful, saved to {os.path.basename(out_path)}.') if logger else None
            else:
                temp_bmp = trace_bmp_to_svg(bmp_path, tmp_dir, logger=logger)
                img = cv.show_svg(temp_bmp) if show_image else None
                logger.info(f'Tracing {os.path.basename(in_path)} successful.') if logger else None
                out_path = None

        return out_path, img


def grayscale_image(
    in_path: str, out_dir: str, binarize: bool = False, show_image: bool = False, save_image: bool = True, logger: Optional[Logger] = None
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    """
    Turn image into grayscale, with optional contrast enhancement and binarization.
    If the input has an alpha channel, it will be separated and restored at the end.
    """
    if confirm_dir_existence(out_dir):
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "gray_binarized" if binarize else "gray"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
        if confirm_overwrite(out_path):
            img = Image.open(in_path)
            is_bw = img.mode == "1" or (img.mode == "L" and set(img.getextrema()) <= {0, 255})
            if not is_bw:
                if img.mode == "RGBA":
                    logger.info("  [contrast] split alpha channel") if logger else None
                    rgb = img.convert("RGB")
                    alpha = img.getchannel("A")
                else:
                    rgb = img
                    alpha = None
                logger.info("  [contrast] convert to grayscale") if logger else None
                img = rgb.convert("L")
                img_array = np.array(img, dtype=np.float32)
                if binarize:
                    def sigmoid(x, threshold=220, gain=20):
                        x = np.clip(x, 0, 255)
                        x = 255 / (1 + np.exp(-gain * (x - threshold) / 255.0))
                        x = x + 100
                        x = np.clip(x, 0, 255)
                        return x
                    logger.info("  [contrast] apply sigmoid") if logger else None
                    enhanced_array = sigmoid(img_array)
                    enhanced_array = np.clip(enhanced_array, 0, 255)
                    # Binarization
                    threshold = 128
                    bw_array = (enhanced_array > threshold) * 255
                    img = Image.fromarray(bw_array.astype(np.uint8))
                else:
                    img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
                # Restore alpha channel
                if alpha is not None:
                    img = img.convert("L")
                    img = Image.merge("LA", (img, alpha))
                
                if save_image:
                    img.save(out_path)
                    logger.info(
                        f"Grayscale {os.path.basename(in_path)} -> {os.path.basename(out_path)} completed."
                    ) if logger else None
                else:
                    out_path = None
                    logger.info(
                        f"Grayscale {os.path.basename(in_path)} completed."
                    ) if logger else None
                img = img if show_image else None                
            else:
                img = Image.open(in_path) if show_image else None
                shutil.copy(in_path, out_path) if save_image else None
                out_path = out_path if save_image else None
                logger.info(
                    f"{os.path.basename(in_path)} is already grayscale. Directly copy to {os.path.basename(out_path)}."
                ) if logger else None
            return out_path, img


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
            cmd = [potrace_exe, in_path, '-o', out_path, '-b', out_fmt.lower()]
            try:
                subprocess.run(cmd, check=True)
                logger.info(f'potrace.exe converted {os.path.basename(in_path)} to {os.path.basename(out_path)} successfully.') if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f'potrace.exe failed: {e}')
