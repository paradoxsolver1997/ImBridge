"""Image enhancement utilities (refactored from enhance_img_300dpi.py).

Exports:
- enhance_image(input_image_path, output_image_path, target_dpi=300)
- enhance_contrast(PIL.Image) -> PIL.Image
- image_to_pdf(input_image_path, output_pdf_path)
- batch_enhance_jpgs(in_folder_path, out_folder_path)
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageChops
import numpy as np
import os
import tempfile


def grayscale_image(
    in_path: str, out_path: str, log_fun=None, binarize: bool = False
) -> Image.Image:
    """
    Turn image into grayscale, with optional contrast enhancement and binarization.
    If the input has an alpha channel, it will be separated and restored at the end.
    """

    img = Image.open(in_path)

    is_bw = img.mode == "1" or (img.mode == "L" and set(img.getextrema()) <= {0, 255})
    if not is_bw:

        if img.mode == "RGBA":
            if log_fun:
                log_fun("  [contrast] split alpha channel")
            rgb = img.convert("RGB")
            alpha = img.getchannel("A")
        else:
            rgb = img
            alpha = None

        if log_fun:
            log_fun("  [contrast] convert to grayscale")
        img_gray = rgb.convert("L")
        img_array = np.array(img_gray, dtype=np.float32)

        if binarize:

            def sigmoid(x, threshold=220, gain=20):
                x = np.clip(x, 0, 255)
                x = 255 / (1 + np.exp(-gain * (x - threshold) / 255.0))
                x = x + 100
                x = np.clip(x, 0, 255)
                return x

            if log_fun:
                log_fun("  [contrast] apply sigmoid")
            enhanced_array = sigmoid(img_array)
            enhanced_array = np.clip(enhanced_array, 0, 255)
            # Binarization
            threshold = 128
            bw_array = (enhanced_array > threshold) * 255
            img_gray = Image.fromarray(bw_array.astype(np.uint8))
        else:
            img_gray = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))

        # Restore alpha channel
        if alpha is not None:
            img_gray = img_gray.convert("L")
            img_gray = Image.merge("LA", (img_gray, alpha))

        img_gray.save(out_path)
        if log_fun:
            log_fun(
                f"Grayscale {os.path.basename(in_path)} -> {os.path.basename(out_path)} completed."
            )
    else:
        img.save(out_path)
        if log_fun:
            log_fun(
                f"{os.path.basename(in_path)} is already grayscale. Directly copy to {os.path.basename(out_path)}."
            )


def enhance_image(
    input_image_path: str, output_image_path: str, target_dpi: int = 300, log_fun=None
) -> None:
    if log_fun:
        log_fun(f"[enhance] open image: {input_image_path}")
    img = Image.open(input_image_path)
    original_dpi = img.info.get("dpi", (72, 72))[0]
    if log_fun:
        log_fun(f"[enhance] original size: {img.size}, dpi: {original_dpi}")
    img_smooth = upscale_image(img, scale_factor=target_dpi / original_dpi, log_fun=log_fun)
    if log_fun:
        log_fun(f"[enhance] save to: {output_image_path}")
    img_contrasted = grayscale_image(img_smooth, log_fun=log_fun)
    img_contrasted.save(output_image_path)
    if log_fun:
        log_fun("[enhance] done")


def scale_image(
    img: Image.Image, scale_factor: float = 2.0, log_fun=None, **kwargs
) -> None:
    
    width, height = img.size
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    if scale_factor > 1.0: 
        img_smooth = resize_image(img, new_width, new_height, enhance_flag=True, log_fun=log_fun, **kwargs)
    elif scale_factor < 1.0:
        img_smooth = resize_image(img, new_width, new_height, log_fun=log_fun, **kwargs)
    else:
        img_smooth = img.copy()
    return img_smooth


def resize_image(
    img: Image.Image,
    new_width: int,
    new_height: int,
    enhance_flag=False,
    log_fun=None,
    **kwargs
) -> None:

    if log_fun:
        log_fun(f"[enhance] resize to: {(new_width, new_height)}")

    # Separate alpha channel
    if img.mode == "RGBA":
        rgb = img.convert("RGB")
        alpha = img.getchannel("A").resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )
        img_2 = rgb.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        img_2 = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        alpha = None

    if enhance_flag:
        if log_fun:
            log_fun("[enhance] sharpen")
        enhancer = ImageEnhance.Sharpness(img_2)
        img_2 = enhancer.enhance(kwargs.get('sharpness', 5.0))
        if log_fun:
            log_fun("[enhance] gaussian blur")
        img_2 = img_2.filter(ImageFilter.GaussianBlur(radius=kwargs.get('blur_radius', 1.0)))
        if log_fun:
            log_fun("[enhance] median filter")
        img_2 = img_2.filter(ImageFilter.MedianFilter(size=kwargs.get('median_size', 3)))
        if log_fun:
            log_fun("[enhance] enhance contrast")
        # Merge alpha channel
        if alpha is not None:
            img_2 = img_2.convert("RGBA")
            img_2.putalpha(alpha)
        if log_fun:
            log_fun("Upscale finished.")
    
    return img_2


def save_with_enhance(img: Image.Image, filepath: str, dpi: int = 300):
    """
    Crop the signature and enhance the resolution, keeping the transparent background, and save as various bitmap formats (png/jpg/jpeg/bmp/tiff, etc.).
    img: PIL.Image (RGBA)
    filepath: Save path
    dpi: Target DPI
    """
    # Crop the blank area
    bg = Image.new("RGBA", img.size, (255, 255, 255, 0))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    cropped = img.crop(bbox) if bbox else img
    # Temporarily save the cropped image
    ext = os.path.splitext(filepath)[1].lower()
    if ext in [".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
        tmp_suffix = ext
    else:
        tmp_suffix = ".png"
    with tempfile.NamedTemporaryFile(suffix=tmp_suffix, delete=False) as tmp:
        tmp_path = tmp.name
        # jpg does not support alpha
        save_img = (
            cropped.convert("RGB") if ext in [".jpg", ".jpeg", ".bmp"] else cropped
        )
        save_img.save(tmp_path, format=ext.lstrip(".").upper() if ext else "PNG")
    # Call enhance to improve resolution
    enhance_image(tmp_path, filepath, target_dpi=dpi)
    os.remove(tmp_path)
