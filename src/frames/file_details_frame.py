import tkinter as tk
from tkinter import ttk, messagebox
from src.frames.base_frame import BaseFrame
import time
import os
from PIL import Image
from PyPDF2 import PdfReader
# 缓存元数据，避免重复I/O


class FileDetailsFrame(BaseFrame):
    def __init__(self, parent, file_list, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.list_window = parent
        self._file_meta_cache = {}
        self.file_list = file_list
        self.build_contents()

    def build_contents(self):

        # 主体frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        # Treeview区域
        columns = ("文件名", "大小 (KB)", "修改时间")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=50 if col=="大小 (KB)" else 150)
        self.tree.pack(fill="x", padx=10, pady=(10, 2))


        # 详情Frame
        self.detail_frame = ttk.Frame(main_frame)
        self.detail_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        # 预览Frame（预留）
        self.preview_frame = ttk.Frame(main_frame)
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 关闭按钮
        btn = ttk.Button(main_frame, text="关闭", command=self.list_window.destroy)
        btn.pack(pady=(0, 6), anchor="e")

        # 获取文件列表
        
        file_list = [f for f in self.file_list if f]

        # 填充Treeview
        for f in file_list:
            if os.path.isfile(f):
                try:
                    size_kb = os.path.getsize(f) // 1024
                    mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(f)))
                    self.tree.insert("", "end", iid=f, values=(os.path.basename(f), size_kb, mtime))
                except Exception as e:
                    self.tree.insert("", "end", iid=f, values=(os.path.basename(f), "读取失败", str(e)))
            else:
                self.tree.insert("", "end", iid=f, values=(os.path.basename(f), "不存在", "-"))

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # 默认选中第一个
        if file_list:
            self.tree.selection_set(file_list[0])
            self.show_details(file_list[0])

    # 详情显示函数
    def sniff_type(self, path):
        try:
            with open(path,'rb') as f:
                head = f.read(512)
        except:
            return 'Unknown','Unknown'
        sig = head[:16]
        txt_head = head.decode('utf-8','ignore').lower()
        if sig.startswith(b'\x89PNG\r\n\x1a\n'): return 'PNG','Raster'
        if sig.startswith(b'\xff\xd8\xff'): return 'JPEG','Raster'
        if head[:6] in (b'GIF87a', b'GIF89a'): return 'GIF','Raster'
        if sig.startswith(b'BM'): return 'BMP','Raster'
        if sig[:4] == b'RIFF' and b'WEBP' in head[:32]: return 'WEBP','Raster'
        if sig[:4] in (b'II*\x00', b'MM\x00*'): return 'TIFF','Raster'
        if head.startswith(b'%PDF-'): return 'PDF','Vector'
        if head.startswith(b'%!PS'): return 'EPS','Vector'
        if '<svg' in txt_head[:200]: return 'SVG','Vector'
        return 'Unknown','Unknown'

    def read_image_meta(self, path):
        meta = {}
        try:
            fsize = os.path.getsize(path)
            meta['文件大小'] = f'{fsize // 1024} KB'
            mtime = os.path.getmtime(path)
            meta['修改时间'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        except Exception as e:
            meta['文件大小'] = '读取失败'
            meta['修改时间'] = '-'
        typ, cat = self.sniff_type(path)
        meta['类型'] = typ
        meta['类别'] = cat
        meta['绝对路径'] = path
        if cat == 'Raster' and typ not in ('PDF','SVG','EPS'):
            try:
                with Image.open(path) as im:
                    w,h = im.size
                    meta['像素尺寸'] = f'{w} × {h}'
                    dpi = im.info.get('dpi') or im.info.get('jfif_density')
                    if dpi and isinstance(dpi,(tuple,list)) and len(dpi)>=2:
                        xdpi, ydpi = dpi[0], dpi[1]
                    else:
                        xdpi = ydpi = None
                    if xdpi and ydpi:
                        meta['DPI'] = f'{xdpi} × {ydpi}'
                        meta['物理尺寸'] = f'{w/xdpi*2.54:.2f} × {h/ydpi*2.54:.2f} cm'
                    else:
                        meta['DPI'] = 'N/A'
                        meta['物理尺寸'] = f'估算(72DPI): {w/72*2.54:.2f} × {h/72*2.54:.2f} cm'
            except Exception as e:
                meta['像素尺寸'] = '读取失败'
                meta['DPI'] = 'N/A'
                meta['物理尺寸'] = '-'
        elif cat == 'Vector' and typ == 'PDF':
            try:
                reader = PdfReader(path)
                page = reader.pages[0]
                width_pt = float(page.mediabox.width)
                height_pt = float(page.mediabox.height)
                width_in = width_pt/72
                height_in = height_pt/72
                meta['像素尺寸'] = 'N/A'
                meta['DPI'] = 'N/A'
                meta['物理尺寸'] = f'{width_in*2.54:.2f} × {height_in*2.54:.2f} cm'
            except Exception:
                meta['物理尺寸'] = '-'
                meta['像素尺寸'] = 'N/A'
                meta['DPI'] = 'N/A'
        else:
            meta['像素尺寸'] = 'N/A'
            meta['DPI'] = 'N/A'
            meta['物理尺寸'] = '-'
        return meta

    # 详情面板内容刷新
    def show_details(self, path):
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        if not os.path.isfile(path):
            ttk.Label(self.detail_frame, text="文件不存在", foreground="red").pack(anchor="w")
            return
            
        # 读取缓存或新解析
        if path in self._file_meta_cache:
            meta = self._file_meta_cache[path]
        else:
            meta = self.read_image_meta(path)
            self._file_meta_cache[path] = meta
        # 展示每一条
        for k, v in meta.items():
            row = ttk.Frame(self.detail_frame)
            row.pack(fill="x", anchor="w", pady=1)
            ttk.Label(row, text=f"{k}: ", font=("TkDefaultFont", 10, "bold")).pack(side="left", anchor="w")
            ttk.Label(row, text=str(v), font=("TkDefaultFont", 10)).pack(side="left", anchor="w")

    # 绑定选中事件
    def on_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.show_details(sel[0])
    