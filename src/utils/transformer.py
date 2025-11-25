from typing import Optional, Tuple, Callable
from PIL import Image, ImageEnhance, ImageFilter
import os
import tempfile
import fitz  # PyMuPDF
import shutil
import xml.etree.ElementTree as ET

from src.utils.commons import confirm_overwrite
from src.utils.commons import confirm_single_page
from src.utils.commons import confirm_dir_existence

from src.utils.logger import Logger
import src.utils.converter as cv
import src.utils.vector as vec


def transform_raster(
    img: Image.Image,
    logger: Optional[Logger] = None,
    **kwargs
) -> Image.Image:
    """Crop and enhance raster image."""

    if 'new_width' in kwargs and 'new_height' in kwargs:
        new_width = int(kwargs['new_width'])
        new_height = int(kwargs['new_height'])
    elif 'scale_x' in kwargs and 'scale_y' in kwargs:
        new_width = int(img.width * float(kwargs['scale_x']))
        new_height = int(img.height * float(kwargs['scale_y']))
    else:
        new_width = img.width
        new_height = img.height

    logger.info(f"[enhance] resize to: {(new_width, new_height)}") if logger else None

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

    if new_height > img.height and new_width > img.width:
        logger.info("[enhance] sharpen") if logger else None
        enhancer = ImageEnhance.Sharpness(img_2)
        img_2 = enhancer.enhance(kwargs.get('sharpness', 5.0))
        logger.info("[enhance] gaussian blur") if logger else None
        img_2 = img_2.filter(ImageFilter.GaussianBlur(radius=kwargs.get('blur_radius', 1.0)))
        logger.info("[enhance] median filter") if logger else None
        img_2 = img_2.filter(ImageFilter.MedianFilter(size=kwargs.get('median_size', 3)))
        logger.info("[enhance] enhance contrast") if logger else None
        # Merge alpha channel
        if alpha is not None:
            img_2 = img_2.convert("RGBA")
            img_2.putalpha(alpha)
        logger.info("Upscale finished.") if logger else None
    tilt = False
    if 'rotate_angle' in kwargs:
        angle = kwargs.get('rotate_angle') % 360
        logger.info(f"[crop] rotate image by {angle} degrees") if logger else None
        img_2 = img_2.rotate(angle, expand=True)
        if angle in [90, 270]:
            tilt = True

    if 'flip_lr' in kwargs and kwargs['flip_lr']:
        if tilt:
            img_2 = img_2.transpose(Image.FLIP_TOP_BOTTOM)
        else:
            img_2 = img_2.transpose(Image.FLIP_LEFT_RIGHT)
        logger.info(f"[crop] flip image left-right") if logger else None
    if 'flip_tb' in kwargs and kwargs['flip_tb']:
        if tilt:
            img_2 = img_2.transpose(Image.FLIP_LEFT_RIGHT)
        else:
            img_2 = img_2.transpose(Image.FLIP_TOP_BOTTOM)
        logger.info(f"[crop] flip image top-bottom") if logger else None

    return img_2


def transform_image(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:

    base_name = os.path.splitext(os.path.basename(in_path))[0]
    in_fmt = os.path.splitext(in_path)[1].lower()
    suffix = "resized"
    out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

    # 自动获取目标尺寸
    img = Image.open(in_path)
    img = transform_raster(img, logger=logger, **kwargs)
    
    if save_image:
        img.save(out_path)
        logger.info(f"[Transform] saved to: {out_path}") if logger else None
        return out_path
    else:
        logger.info("[Transform] see preview frame for transformation effect") if logger else None
        preview_callback(img) if preview_callback else None
        return None


def transform_svg(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[Tuple[Optional[str], Optional[Image.Image]]]:
    
    dpi = kwargs.get("dpi", 96)

    def mat2str(mat: list[float, float, float, float, float, float]) -> str:
        return "matrix(" + " ".join(f"{x}" for x in mat) + ")"
    (orig_width, orig_height), unit = vec.get_svg_size(in_path)
    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "resized"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
        
        
        mat = vec.compute_trans_matrix()

        if 'new_width' in kwargs and 'new_height' in kwargs:
            target_width = float(kwargs['new_width'])
            target_height = float(kwargs['new_height'])
            scale_x = target_width / orig_width
            scale_y = target_height / orig_height
        elif 'scale_x' in kwargs and 'scale_y' in kwargs:
            scale_x = float(kwargs['scale_x'])
            scale_y = float(kwargs['scale_y'])
            target_width = orig_width * scale_x
            target_height = orig_height * scale_y
        else:
            scale_x = 1.0
            scale_y = 1.0
            target_width = orig_width
            target_height = orig_height
        mat = vec.compute_trans_matrix(mat, scale=(scale_x, scale_y))

        try:
            tree = ET.parse(in_path)
            root = tree.getroot()
        except Exception:
            raise RuntimeError("Failed to parse SVG dimensions.")
        
        root.set("viewBox", f"0 0 {target_width} {target_height}")
        root.set("width", str(target_width))
        root.set("height", str(target_height))

        if 'flip_lr' in kwargs and kwargs['flip_lr']:
            mat = vec.compute_trans_matrix(mat, flip_lr=True, translate=[target_width, 0])
        if 'flip_tb' in kwargs and kwargs['flip_tb']:
            mat = vec.compute_trans_matrix(mat, flip_tb=True, translate=[0, target_height])

        if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
            angle = kwargs['rotate_angle'] % 360
            # 如果旋转90或270度，需要交换width和height
            if angle in [90, 270]:
                temp_value = target_width
                target_width = target_height
                target_height = temp_value
                root.set("viewBox", f"0 0 {target_width} {target_height}")
                root.set("width", str(target_width))
                root.set("height", str(target_height))
            angle_map = {
                0: [0, 0],
                90: [0, target_height],
                180: [target_width, target_height],
                270: [target_width, 0],
            }
            mat = vec.compute_trans_matrix(
                mat, 
                rotate_angle=angle, 
                translate=angle_map.get(angle, [0, 0])
            )
            logger.info(f"[Transform] Rotating SVG by {angle} degrees") if logger else None
        try:
            g = ET.Element("g")
            for child in list(root):
                g.append(child)
                root.remove(child)
            g.set("transform", " ".join([mat2str(mat)]))
            root.append(g)
            tree.write(out_path, encoding="utf-8", xml_declaration=True)
            vec.optimize_svg(out_path, out_path)
            preview_img = vec.show_svg(out_path, dpi=dpi)
            preview_callback(preview_img, unit) if preview_callback else None
            logger.info(f"[Transform] svg saved to {out_path}") if logger else None
            return out_path
        except Exception as e:
            raise RuntimeError(f"SVG transform failed: {e}")
    else:
        preview_img = transform_raster(vec.show_svg(in_path, dpi=dpi), logger=logger, **kwargs)
        preview_callback(preview_img, unit) if preview_callback else None
        logger.info(f"[Transform] see preview frame for cropping effect") if logger else None
        return None


def transform_pdf(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    
    dpi = kwargs.get("dpi", 96)

    if not confirm_single_page(in_path):
        return None

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "resized"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")

        if confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            try:
                with fitz.open(in_path) as doc:
                    with fitz.open() as new_doc:
                        page = doc[0]
                        rect = page.rect
                        orig_width = rect.width
                        orig_height = rect.height
            
                        if 'new_width' in kwargs and 'new_height' in kwargs:
                            target_width = float(kwargs['new_width'])
                            target_height = float(kwargs['new_height'])
                            scale_x = target_width / orig_width
                            scale_y = target_height / orig_height
                        elif 'scale_x' in kwargs and 'scale_y' in kwargs:
                            scale_x = float(kwargs['scale_x'])
                            scale_y = float(kwargs['scale_y'])
                            target_width = orig_width * scale_x
                            target_height = orig_height * scale_y
                        else:
                            scale_x = 1.0
                            scale_y = 1.0
                            target_width = orig_width
                            target_height = orig_height
                        logger.info(f"[vector] Page scaled: {orig_width}x{orig_height}pt -> {target_width}x{target_height}pt, scale=({scale_x:.2f},{scale_y:.2f})") if logger else None
                        new_page = new_doc.new_page(width=target_width, height=target_height)
                        new_page.show_pdf_page(
                            new_page.rect,  # 目标矩形
                            doc,  # 源文档
                            page.number,  # 源页码
                            clip=None,  # 不裁剪
                            rotate=0,  # 不旋转
                            keep_proportion=False,  # 不保持比例(使用我们的缩放)
                            overlay=True
                        )
                        if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
                            angle = (360 - kwargs.get('rotate_angle')) % 360
                            logger.info(f"[vector] Rotating PDF page by {angle} degrees") if logger else None
                            new_page.set_rotation(angle)
                        if 'flip_lr' in kwargs or 'flip_tb' in kwargs:
                            logger.error(f"[vector] Flipping PDF page is not supported.") if logger else None
                        new_doc.save(out_path)
                preview_img = vec.show_script(out_path, dpi=dpi)
                preview_callback(preview_img, "pt") if preview_callback else None
                logger.info(f"[Transform] PDF saved to {out_path}") if logger else None
                return out_path
            except Exception as e:
                raise RuntimeError(f"[Transform] PDF crop/resize failed: {e}")
    else:
        preview_img = transform_raster(vec.show_script(in_path, dpi=dpi), logger=logger, **kwargs)
        preview_callback(preview_img, "pt") if preview_callback else None
        logger.info(f"[Transform] see preview frame for cropping effect") if logger else None
        return None



def transform_script(
    in_path: str,
    out_dir: str,
    save_image: bool = True,
    preview_callback: Optional[Callable] = None,
    logger: Optional[Logger] = None,
    **kwargs
) -> Optional[str]:
    """
    Resize or crop EPS/PS file by editing BoundingBox and HiResBoundingBox.
    逻辑：
      1. 用 wash_eps_ps 清洗文件（标准化 EPS/PS）
      2. 如果指定 crop_box，直接修改 %%BoundingBox 和 %%HiResBoundingBox
      3. 完全二进制安全，支持包含二进制数据的 EPS
      只支持裁剪，不支持缩放
    """
    dpi = kwargs.get("dpi", 96)

    if save_image:
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        in_fmt = os.path.splitext(in_path)[1].lower()
        suffix = "resized"
        out_path = os.path.join(out_dir, f"{base_name}_{suffix}{in_fmt}")
        
        if confirm_single_page(in_path) and confirm_dir_existence(out_dir) and confirm_overwrite(out_path):
            (orig_width, orig_height), _ = vec.get_script_size(in_path)
            if 'new_width' in kwargs and 'new_height' in kwargs:
                target_width = float(kwargs['new_width'])
                target_height = float(kwargs['new_height'])
                scale_x = target_width / orig_width
                scale_y = target_height / orig_height
            elif 'scale_x' in kwargs and 'scale_y' in kwargs:
                scale_x = float(kwargs['scale_x'])
                scale_y = float(kwargs['scale_y'])
                target_width = orig_width * scale_x
                target_height = orig_height * scale_y
            else:
                scale_x = 1.0
                scale_y = 1.0
                target_width = orig_width
                target_height = orig_height

            target_size = max(target_width, target_height)

            vec.update_matrix(in_path, out_path, scale=(scale_x, scale_y))   
            vec.change_bbox(
                    in_path=out_path, 
                    out_path=out_path, 
                    old_bbox=(0, 0, orig_width, orig_height),
                    new_bbox=(0, 0, target_size, target_size),
                    logger=logger
                )

            if 'flip_lr' in kwargs and kwargs['flip_lr']:
                vec.update_matrix(out_path, out_path, flip_lr=True, translate=[target_width, 0])

            if 'flip_tb' in kwargs and kwargs['flip_tb']: 
                vec.update_matrix(out_path, out_path, flip_tb=True, translate=[0, target_height])           

            if 'rotate_angle' in kwargs and kwargs['rotate_angle'] is not None:
                angle = (360 - kwargs.get('rotate_angle')) % 360
                # 如果旋转90或270度，需要交换width和height
                if angle in [90, 270]:
                    temp_value = target_width
                    target_width = target_height
                    target_height = temp_value
                angle_map = {
                    0: [0, 0],
                    90: [0, target_height],
                    180: [target_width, target_height],
                    270: [target_width, 0],
                }
                vec.update_matrix(
                    out_path, 
                    out_path, 
                    rotate_angle=angle, 
                    translate=angle_map.get(angle, [0, 0])
                )
                logger.info(f"[Transform] Rotating EPS by {angle} degrees") if logger else None

            vec.change_bbox(
                in_path=out_path, 
                out_path=out_path, 
                old_bbox=(0, 0, orig_width, orig_height),
                new_bbox=(0, 0, target_width, target_height),
                logger=logger
            )
            preview_img = vec.show_script(out_path, dpi=dpi)
            preview_callback(preview_img, "pt") if preview_callback else None
            logger.info(f"[Transform] EPS/PS saved to {out_path}") if logger else None
    else:
        preview_img = transform_raster(vec.show_script(in_path, dpi=dpi), logger=logger, **kwargs)
        preview_callback(preview_img, "pt") if preview_callback else None
        logger.info(f"[Transform] see preview frame for cropping effect") if logger else None
        return None
