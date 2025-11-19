import tkinter as tk
from tkinter import ttk
from src.frames.base_frame import BaseFrame
from PIL import Image, ImageTk
import os
import tempfile

from src.utils import converter


class PreviewFrame(BaseFrame):

    def __init__(self, parent, title=None, width=160, height=160, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title = title if title is not None else "Preview"
        self.width = width
        self.height = height
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
        btn_frame.pack(side="bottom", pady=3)
        self.btn_prev = ttk.Button(btn_frame, text="◀", width=1.5, command=self.previous_page)
        self.btn_prev.pack(side="left", ipadx=0, ipady=0, padx=(0, 12))
        # 新增：页码label
        self.page_label = ttk.Label(btn_frame, text=self._get_page_text(), width=7, anchor="center")
        self.page_label.pack(side="left", padx=(0, 12))
        self.btn_next = ttk.Button(btn_frame, text="▶", width=1.5, command=self.next_page)
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

    def show_image(self, image):
        for w in self.title_frame.winfo_children():
            w.destroy()
        try:
            img = image.copy()
            orig_size = img.size
            # 计算缩放比例，保持比例填满
            frame_w, frame_h = self.width, self.height - 60  # 留出按钮区高度
            scale = min(frame_w / img.width, frame_h / img.height)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)
            # 居中裁剪
            left = (img.width - frame_w) // 2
            top = (img.height - frame_h) // 2
            img = img.crop((left, top, left + frame_w, top + frame_h))
            imgtk = ImageTk.PhotoImage(img)
            self.build_buttons()
            label = tk.Label(self.title_frame, image=imgtk)
            label.image = imgtk
            label.pack(expand=True, fill="both")
            size_label = tk.Label(self.title_frame, text=f"{orig_size[0]}x{orig_size[1]}", anchor="ne", bg="#f0f0f0")
            size_label.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)
            self._update_page_label()
        except Exception as e:
            tk.Label(self.title_frame, text="Preview failed").pack(expand=True)
    
    def show_file(self, img_path):
        try:
            ext = os.path.splitext(img_path)[1].lower()
            # Support vector preview: svg/pdf/eps/ps

            if ext in (".svg", ".pdf", ".eps", ".ps"):
                self.log("Vector file detected, converting to bitmap for preview...")
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as tmp_png:
                    png_path = tmp_png.name
                try:
                    converter.vector_to_bitmap(img_path, png_path, dpi=60)
                    with Image.open(png_path) as img:
                        img.thumbnail((100, 100))
                except Exception as ve:
                    raise
                finally:
                    if os.path.exists(png_path):
                        os.remove(png_path)
            else:
                img = Image.open(img_path)
            self.log("Displaying preview image...")
            self.show_image(img)
            self._update_page_label()
        except Exception as e:
            # 清理预览区域并显示占位
            for w in self.title_frame.winfo_children():
                w.destroy()
            tk.Label(self.title_frame, text="No Preview Available").pack(expand=True)

    def clear_preview(self):
        # 只清空内容，不销毁容器，避免预览区消失
        if hasattr(self, "title_frame"):
            for w in self.title_frame.winfo_children():
                w.destroy()
            self.build_contents()
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

        