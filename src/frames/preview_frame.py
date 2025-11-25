import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from pillow_heif import register_heif_opener

from src.frames.base_frame import BaseFrame
import src.utils.vector as vec
from src.utils.commons import script_formats, bitmap_formats, heif_formats


class PreviewFrame(BaseFrame):

    def __init__(self, parent, title=None, width=160, height=160, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title = title if title is not None else "Preview"
        self.width = width
        self.height = height
        self.dpi = 96
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
        # Pack the preview label after buttons to ensure it is above them
        self.preview_label = ttk.Label(self.title_frame, text="Preview Area", anchor="center")
        self.preview_label.pack(side="top", fill="both", expand=True, padx=10, pady=10)

    def build_buttons(self):
        # Navigation buttons area (pack first to ensure at bottom)
        btn_frame = ttk.Frame(self.title_frame)
        btn_frame.pack(side="bottom", pady=0)
        small_font = ("TkDefaultFont", 8)
        self.btn_prev = tk.Button(btn_frame, text="◀", width=2, height=1, font=small_font, command=self.previous_page)
        self.btn_prev.pack(side="left", ipadx=0, ipady=0, padx=(0, 12))
        # Added: page number label
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
        # Private ordered queue, not directly accessible from outside
        from collections import deque
        self.__file_queue = deque()

    def add_file_to_queue(self, file_path):
        """
        Add a file path to the queue, callable from outside
        """
        self.__file_queue.append(file_path)
        self._queue_index = len(self.__file_queue) - 1
        self.show_file(self.__file_queue[self._queue_index])
        self._update_page_label()

    def clear_file_queue(self):
        """
        Clear the file queue, callable from outside
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
            # Center crop
            bg_color = "#f0f0f0"
            bg = Image.new("RGB", (frame_w, frame_h), bg_color)
            left = (frame_w - img.width) // 2
            top = (frame_h - img.height) // 2
            bg.paste(img, (left, top))
            imgtk = ImageTk.PhotoImage(bg)
            self.preview_label.config(image=imgtk)
            self.preview_label.image = imgtk
            self.preview_label.config(text="")  # Clear text
            # Display size information
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
                img = vec.show_script(img_path, dpi=self.dpi)
                img = process_callback(img.copy()) if process_callback else img
                sz, unit = vec.get_script_size(img_path)
                self.show_image(img, img_size=sz, unit=unit)
            elif ext == ".pdf":
                img = vec.show_script(img_path)
                img = process_callback(img) if process_callback else img
                sz, unit = vec.get_pdf_size(img_path)
                self.show_image(img, img_size=sz, unit=unit)
            elif ext == ".svg":
                img = vec.show_svg(img_path)
                img = process_callback(img) if process_callback else img
                sz, unit = vec.get_svg_size(img_path)
                self.show_image(img, img_size=sz, unit=unit)
            elif ext in heif_formats:
                register_heif_opener()
                img = Image.open(img_path)
                img = process_callback(img) if process_callback else img
                sz, = img.size
                self.show_image(img, img_size=sz, unit='px')
            elif ext in bitmap_formats:
                img = Image.open(img_path)
                img = process_callback(img) if process_callback else img
                sz, = img.size
                self.show_image(img, img_size=sz, unit='px')
            else:
                # Unsupported format
                if hasattr(self, "preview_label"):
                    self.preview_label.config(image="", text="No Preview Available")
                    self.preview_label.image = None
                if hasattr(self, "size_label"):
                    self.size_label.config(text="")
            self._update_page_label()
        except Exception as e:
            # Only clear image and size information, do not destroy buttons and page number
            if hasattr(self, "preview_label"):
                self.preview_label.config(image="", text="No Preview Available")
                self.preview_label.image = None
            if hasattr(self, "size_label"):
                self.size_label.config(text="")

    def clear_preview(self):
        # Only clear image and size information, do not destroy buttons and page number
        if hasattr(self, "preview_label"):
            self.preview_label.config(image="", text="Preview Area")
            self.preview_label.image = None
        if hasattr(self, "size_label"):
            self.size_label.config(text="")
        self._update_page_label()
            
    def previous_page(self):
        """
        Previous page button callback, decrement queue index and show previous image, boundary check
        """
        if len(self.__file_queue) == 0:
            return
        if self._queue_index > 0:
            self._queue_index -= 1
            self.show_file(self.__file_queue[self._queue_index])
            self._update_page_label()
            # Send custom page change event
            self.event_generate('<<PreviewPageChanged>>', when='tail')

    def next_page(self):
        """
        Next page button callback, increment queue index and show next image, boundary check
        """
        if len(self.__file_queue) == 0:
            return
        if self._queue_index < len(self.__file_queue) - 1:
            self._queue_index += 1
            self.show_file(self.__file_queue[self._queue_index])
            self._update_page_label()
            # Send custom page change event
            self.event_generate('<<PreviewPageChanged>>', when='tail')

    def get_queue_size(self):
        """
        Get the current queue size
        """
        return len(self.__file_queue)