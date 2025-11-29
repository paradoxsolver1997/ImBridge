from typing import Optional, Tuple, Callable
from PIL import Image, ImageDraw
import os
import fitz  # PyMuPDF
import math
import xml.etree.ElementTree as ET
from src.utils.logger import Logger

from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_single_page
from src.utils.commons import confirm_dir_existence
from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_cropbox

import src.utils.vector as vec


def display_crop(img, crop_box, eps_coordinate=False, box_color="white", box_width=3, mask_opacity=120):
    """
    Draw a crop box on the image and add a semi-transparent mask outside it.
    
    Parameters:
        img: Image.Image
        crop_box: (x, y, w, h) - top-left corner + width and height
        box_color: Crop box color (default white for better visibility)
        box_width: Border width
        mask_opacity: Mask opacity, range 0-255 (higher is darker)
    """
    x, y, x2, y2 = crop_box
    if eps_coordinate:
        # EPS coordinate system, y axis upwards
        y, y2 = img.height - y2, img.height - y

    # Copy the image to avoid modifying the original
    img_out = img.copy().convert("RGBA")

    # Create a transparent layer the same size as the image for the mask
    mask_layer = Image.new("RGBA", img_out.size, (0, 0, 0, 0))
    mask_draw = ImageDraw.Draw(mask_layer)

    # Semi-transparent mask (outside the box)
    width, height = img_out.size

    # Draw masks in four directions
    mask_draw.rectangle([(0, 0), (width, y)], fill=(0, 0, 0, mask_opacity))               # Top
    mask_draw.rectangle([(0, y2), (width, height)], fill=(0, 0, 0, mask_opacity))        # Bottom
    mask_draw.rectangle([(0, y), (x, y2)], fill=(0, 0, 0, mask_opacity))                 # Left
    mask_draw.rectangle([(x2, y), (width, y2)], fill=(0, 0, 0, mask_opacity))            # Right

    # Composite the mask layer onto the image
    img_out = Image.alpha_composite(img_out, mask_layer)

    # Finally draw the crop box (white recommended for better visibility)
    draw = ImageDraw.Draw(img_out)
    draw.rectangle([x, y, x2, y2], outline=box_color, width=box_width)

    return img_out.convert("RGB")


def crop_image(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None
) -> Optional[str]:

    img = Image.open(in_path)
    if not confirm_cropbox(crop_box, (img.width, img.height)):
        logger.error("[bitmap] Crop box invalid (exceeding the bounds), skipping crop.")
        return None

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

        logger.info(f"[crop] crop box: {crop_box}") if logger else None
        img = img.crop(crop_box)
        img.save(out_path)
        logger.info(f"[crop] saved to: {out_path}") if logger else None
        preview_callback(img) if preview_callback else None
        return out_path
    else:
        preview_callback(display_crop(Image.open(in_path), crop_box)) if preview_callback else None
        logger.info("[crop] see preview frame for cropping effect") if logger else None
        return None


def crop_svg(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:

    dpi = kwargs.get("dpi", 96)
    try:
        tree = ET.parse(in_path)
        root = tree.getroot()
        view_box = vec.get_view_box_from_root(root)
        (orig_width, orig_height), unit = vec.get_size_from_root(root)
        if view_box is None:
            view_box = (0, 0, orig_width, orig_height)
            root.set("viewBox", "{} {} {} {}".format(*view_box))
    except Exception:
        raise RuntimeError("Failed to parse SVG dimensions.")
    
    def display_crop_svg(img):
        x1 = max(math.floor(crop_box[0] / 72 * dpi), 0)
        y1 = max(math.floor(crop_box[1] / 72 * dpi), 0)
        x2 = math.floor(crop_box[2] / 72 * dpi)
        y2 = math.floor(crop_box[3] / 72 * dpi)
        return display_crop(img, crop_box=(x1, y1, x2, y2))

    if not confirm_cropbox(crop_box, (orig_width, orig_height)):
        logger.error("[vector] Crop box invalid (exceeding the bounds), skipping crop.")
        return None

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):

            scaled_crop_box = (
                crop_box[0] / orig_width * view_box[2],
                crop_box[1] / orig_height * view_box[3],
                crop_box[2] / orig_width * view_box[2],
                crop_box[3] / orig_height * view_box[3],
                )
            
            try:
                x = scaled_crop_box[0] + view_box[0]
                y = scaled_crop_box[1] + view_box[1]
                w = scaled_crop_box[2]
                h = scaled_crop_box[3]
                logger.info(f"[vector] Cropping SVG viewBox to ({x},{y},{w},{h})") if logger else None
                root.set("viewBox", f"{x} {y} {w} {h}")
                tree.write(out_path, encoding="utf-8", xml_declaration=True)
                preview_img = vec.show_svg(out_path, dpi=dpi)
                vec.optimize_svg(out_path, out_path)
                preview_callback(preview_img, unit) if preview_callback else None
                logger.info(f"[vector] SVG saved to {out_path}") if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f"SVG crop/resize failed: {e}")
        else:
            return None
    else:
        preview_img = display_crop_svg(vec.show_svg(in_path, dpi=dpi))
        preview_callback(preview_img, unit) if preview_callback else None
        logger.info(f"[Transform] see preview frame for cropping effect") if logger else None
        return None

def crop_pdf(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    
    dpi = kwargs.get("dpi", 96)

    def display_crop_pdf(img):
        x1 = max(math.floor(crop_box[0] / 72 * dpi), 0)
        y1 = max(math.floor(crop_box[1] / 72 * dpi), 0)
        x2 = math.floor(crop_box[2] / 72 * dpi)
        y2 = math.floor(crop_box[3] / 72 * dpi)
        return display_crop(img, crop_box=(x1, y1, x2, y2))

    if not confirm_single_page(in_path):
        return None
    (orig_width, orig_height), unit = vec.get_pdf_size(in_path)
    if not confirm_cropbox(crop_box, (orig_width, orig_height)):
        logger.error("[vector] Crop box invalid (exceeding the bounds), skipping crop.")
        return None

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            try:
                with fitz.open(in_path) as doc:
                    with fitz.open() as new_doc:
                        for page in doc:
                            new_page = new_doc.new_page(width=orig_width, height=orig_height)
                            new_page.set_cropbox(fitz.Rect(*crop_box))
                            new_page.show_pdf_page(
                                new_page.rect,  # Target rectangle
                                doc,  # Source document
                                page.number,  # Source page number
                                clip=crop_box,  # No clipping
                                rotate=0,  # No rotation
                                keep_proportion=False,  # Do not keep proportion (use our scaling)
                                overlay=True
                            )                            
                            logger.info(f"[vector] Set cropbox to {crop_box}") if logger else None
                        new_doc.save(out_path)
                preview_img = vec.show_script(out_path, dpi=dpi)
                preview_callback(preview_img, unit) if preview_callback else None
                logger.info(f"[vector] PDF saved to {out_path}") if logger else None    
                return out_path
            except Exception as e:
                raise RuntimeError(f"PDF crop/resize failed: {e}")
        else:
            return None
    else:
        preview_img = display_crop_pdf(vec.show_script(in_path, dpi=dpi))
        preview_callback(preview_img, unit) if preview_callback else None
        logger.info(f"[Transform] see preview frame for cropping effect") if logger else None
        return None

def crop_script(
    in_path: str,
    out_dir: str,
    crop_box: tuple[int, int, int, int],
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    """
    Resize or crop EPS/PS file by editing BoundingBox and HiResBoundingBox.
    Logic:
      1. Use wash_eps_ps to clean the file (standardize EPS/PS)
      2. If crop_box is specified, directly modify %%BoundingBox and %%HiResBoundingBox
      3. Fully binary safe, supports EPS containing binary data
      Only supports cropping, not scaling
    """
    dpi = kwargs.get("dpi", 96)

    def display_crop_script(img):
        x1 = max(math.floor(crop_box[0] / 72 * dpi), 0)
        y1 = max(math.floor(crop_box[1] / 72 * dpi), 0)
        x2 = math.floor(crop_box[2] / 72 * dpi)
        y2 = math.floor(crop_box[3] / 72 * dpi)
        y1, y2 = img.height - y2, img.height - y1 # EPS coordinate system
        return display_crop(img, crop_box=(x1, y1, x2, y2))
    
    if not confirm_single_page(in_path):
        return None
    (orig_width, orig_height), unit = vec.get_script_size(in_path)
    if not confirm_cropbox(crop_box, (orig_width, orig_height)):
        logger.error("[vector] Crop box invalid (exceeding the bounds), skipping crop.")
        return None

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "cropped"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            # Translate to origin, avoiding negative coordinates
            # First translate to origin, then crop, then translate back
            # Otherwise, negative coordinates may appear, causing some viewers to display incorrectly
            # Therefore, the matrix and BoundingBox must be modified in two steps, not merged into one
            '''
            vec.change_bbox(
                in_path=in_path, 
                out_path=out_path,
                old_bbox=(0, 0, orig_width, orig_height),
                new_bbox=(0, 0, max(orig_width, orig_height), max(orig_width, orig_height)), 
                logger=logger
            )
            vec.update_matrix(
                in_path, 
                out_path, 
                translate=[0, crop_box[3] - orig_height],  # y direction translation
            )
            '''
            vec.change_bbox(
                in_path=in_path, 
                out_path=out_path,
                old_bbox=(0, 0, max(orig_width, orig_height), max(orig_width, orig_height)),
                new_bbox=(0, 0, crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]), 
                logger=logger
            )
            vec.update_matrix(
                out_path, 
                out_path, 
                translate=[-crop_box[0], -crop_box[1]],  # y direction translation
            )
            preview_img = vec.show_script(out_path, dpi=dpi)
            preview_callback(preview_img, unit) if preview_callback else None
            logger.info(f"[vector] EPS saved to {out_path}") if logger else None
            return out_path
        else:
            return None
    else:
        preview_img = display_crop_script(vec.show_script(in_path, dpi=dpi))
        preview_callback(preview_img, unit) if preview_callback else None
        logger.info(f"[Transform] see preview frame for cropping effect") if logger else None
        return None