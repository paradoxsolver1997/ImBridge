from PIL import Image
from typing import Optional, Callable
import os
import shutil
import numpy as np

from src.utils.logger import Logger

from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_dir_existence


def remove_alpha_channel(img: Image.Image, bg_color=(255, 255, 255)) -> Image.Image:
    """Remove alpha channel from an image by compositing onto a background color."""
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return background
    elif img.mode != "RGB" and img.mode != "L":
        return img.convert("RGB")
    return img


def get_raster_size(in_path: str) -> tuple[Optional[float], Optional[float]]:
    try:
        img = Image.open(in_path)
        return img.size
    except Exception:
        raise 


def grayscale_image(
    in_path: str, 
    out_dir: str, 
    binarize: bool = False, 
    save_image: bool = True, 
    preview_callback: Optional[Callable] = None, 
    logger: Optional[Logger] = None
) -> Optional[str]:
    """
    Turn image into grayscale, with optional contrast enhancement and binarization.
    If the input has an alpha channel, it will be separated and restored at the end.
    """
    
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "gray_binarized" if binarize else "gray"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
    if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
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
            preview_callback(img) if preview_callback else None                
        else:
            preview_callback(Image.open(in_path)) if preview_callback else None
            shutil.copy(in_path, out_path) if save_image else None
            out_path = out_path if save_image else None
            logger.info(
                f"{os.path.basename(in_path)} is already grayscale. Directly copy to {os.path.basename(out_path)}."
            ) if logger else None
        return out_path


