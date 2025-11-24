import tkinter as tk
from tkinter import ttk
from src.frames.base_frame import BaseFrame
from PIL import Image, ImageTk
import os
import tempfile

import src.utils.converter as cv
from src.utils.commons import get_script_size, get_svg_size
from src.utils.commons import script_formats, bitmap_formats


class PreviewFrame(BaseFrame):

    def __init__(self, parent, title=None, width=160, height=160, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title = title if title is not None else "Preview"
        self.width = width
        self.height = height
        self.dpi = 96
        # 设定固定宽度，避免被挤压到不可见
        self.configure(width=self.width)
        try:
            self.pack_propagate(False)
        except Exception:
            pass
        self.__init_file_queue()
        self._queue_index = -1

        self.title_frame = ttk.LabelFrame(
            self, text=self.title, width=self.width, height=self.height, relief="groove"
        )
        self.title_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.build_contents()

    def build_contents(self):

        self.build_buttons()
        # 预览label后pack，保证内容在按钮上方
        self.preview_label = ttk.Label(self.title_frame, text="图片预览区域", anchor="center")
        self.preview_label.pack(side="top", fill="both", expand=True, padx=10, pady=10)

    def build_buttons(self):
        # 翻页按钮区（先pack，保证在底部）
        btn_frame = ttk.Frame(self.title_frame)
        btn_frame.pack(side="bottom", pady=0)
        small_font = ("TkDefaultFont", 8)
        self.btn_prev = tk.Button(btn_frame, text="◀", width=2, height=1, font=small_font, command=self.previous_page)
        self.btn_prev.pack(side="left", ipadx=0, ipady=0, padx=(0, 12))
        # 新增：页码label
        self.page_label = ttk.Label(btn_frame, text=self._get_page_text(), width=7, anchor="center")
        self.page_label.pack(side="left", padx=(0, 12))
        self.btn_next = tk.Button(btn_frame, text="▶", width=2, height=1, font=small_font, command=self.next_page)
        self.btn_next.pack(side="left", ipadx=0, ipady=0)

    def _get_page_text(self):
        total = len(self.__file_queue)
        if total == 0 or self._queue_index < 0:
            return "0/0"
        return f"{self._queue_index+1}/{total}"

    def _update_page_label(self):
        if hasattr(self, "page_label"):
            self.page_label.config(text=self._get_page_text())

    def __init_file_queue(self):
        # 私有有序队列，外部不可直接访问
        from collections import deque
        self.__file_queue = deque()

    def add_file_to_queue(self, file_path):
        """
        添加文件路径到队列，外部可调用
        """
        self.__file_queue.append(file_path)
        self._queue_index = len(self.__file_queue) - 1
        self.show_file(self.__file_queue[self._queue_index])
        self._update_page_label()

    def clear_file_queue(self):
        """
        清空文件队列，外部可调用
        """
        self.__file_queue.clear()
        self._queue_index = -1
        self.clear_preview()
        self._update_page_label()

    def show_image(self, image, img_size=None, unit='px'):
        try:
            img = image.copy()
            orig_size = img_size if img_size else img.size
            self.update_idletasks()
            frame_w = self.preview_label.winfo_width()
            frame_h = self.preview_label.winfo_height()
            scale = min(frame_w / img.width, frame_h / img.height)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)
            # 居中裁剪
            bg_color = "#f0f0f0"
            bg = Image.new("RGB", (frame_w, frame_h), bg_color)
            left = (frame_w - img.width) // 2
            top = (frame_h - img.height) // 2
            bg.paste(img, (left, top))
            imgtk = ImageTk.PhotoImage(bg)
            self.preview_label.config(image=imgtk)
            self.preview_label.image = imgtk
            self.preview_label.config(text="")  # 清除文字
            # 显示尺寸信息
            if hasattr(self, "size_label"):
                self.size_label.config(text=f"{int(orig_size[0])}x{int(orig_size[1])}"+unit)
            else:
                self.size_label = tk.Label(self.title_frame, text=f"{int(orig_size[0])}x{int(orig_size[1])}", anchor="ne", bg="#f0f0f0")
                self.size_label.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)
            self._update_page_label()
        except Exception as e:
            self.preview_label.config(image="", text="Preview failed")
            self.preview_label.image = None
    
    def show_file(self, img_path, process_callback=None):
        try:
            ext = os.path.splitext(img_path)[1].lower()
            if ext in script_formats:
                img = cv.show_script(img_path, dpi=self.dpi)
                img = process_callback(img) if process_callback else img
                sz = get_script_size(img_path)
                self.show_image(img, img_size=sz, unit='pt')
            elif ext == ".svg":
                img = cv.show_svg(img_path)
                img = process_callback(img) if process_callback else img
                sz = get_svg_size(img_path)
                self.show_image(img, img_size=sz, unit='px')
            elif ext in bitmap_formats:
                img = Image.open(img_path)
                img = process_callback(img) if process_callback else img
                sz = img.size
                self.show_image(img, img_size=sz, unit='px')
            else:
                # 不支持的格式
                if hasattr(self, "preview_label"):
                    self.preview_label.config(image="", text="No Preview Available")
                    self.preview_label.image = None
                if hasattr(self, "size_label"):
                    self.size_label.config(text="")
            self._update_page_label()
        except Exception as e:
            # 只清空图片和尺寸信息，不销毁按钮和页码
            if hasattr(self, "preview_label"):
                self.preview_label.config(image="", text="No Preview Available")
                self.preview_label.image = None
            if hasattr(self, "size_label"):
                self.size_label.config(text="")

    def clear_preview(self):
        # 只清空图片和尺寸信息，不销毁按钮和页码
        if hasattr(self, "preview_label"):
            self.preview_label.config(image="", text="图片预览区域")
            self.preview_label.image = None
        if hasattr(self, "size_label"):
            self.size_label.config(text="")
        self._update_page_label()
            
    def previous_page(self):
        """
        上一页按钮回调，队列索引减1并显示上一张图片，边界检查
        """
        if len(self.__file_queue) == 0:
            return
        if self._queue_index > 0:
            self._queue_index -= 1
            self.show_file(self.__file_queue[self._queue_index])
            self._update_page_label()
            # 发送自定义翻页事件
            self.event_generate('<<PreviewPageChanged>>', when='tail')

    def next_page(self):
        """
        下一页按钮回调，队列索引加1并显示下一张图片，边界检查
        """
        if len(self.__file_queue) == 0:
            return
        if self._queue_index < len(self.__file_queue) - 1:
            self._queue_index += 1
            self.show_file(self.__file_queue[self._queue_index])
            self._update_page_label()
            # 发送自定义翻页事件
            self.event_generate('<<PreviewPageChanged>>', when='tail')

    def get_queue_size(self):
        """
        获取当前队列大小
        """
        return len(self.__file_queue)