from tkinter import ttk
from PIL import Image
import time
import os

import src.utils.vector as vec

from src.frames.base_frame import BaseFrame
from src.frames.preview_frame import PreviewFrame

class FileDetailsFrame(BaseFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.list_window = parent
        self._file_meta_cache = {}
        self.build_contents()

    def build_contents(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        # Treeview area
        columns = ("Filename", "Size (KB)", "Modified Time")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=50 if col=="Size (KB)" else 150)
        self.tree.pack(fill="x", padx=10, pady=(10, 2))

        # Detail Frame
        self.detail_frame = ttk.Frame(main_frame)
        self.detail_frame.pack(fill="x", expand=False, padx=10, pady=(0, 4))

        # Preview Frame
        self.preview_frame = PreviewFrame(main_frame, title="Input Preview", width=160, height=160)
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        # Bind custom page change event
        self.preview_frame.bind('<<PreviewPageChanged>>', self._on_preview_page_changed)
        
        # Close button
        btn = ttk.Button(main_frame, text="Withdraw", command=self.list_window.withdraw)
        btn.pack(padx=(8, 8), pady=(0, 6), anchor="e")
        self.populate_file_list([])

    def populate_file_list(self, file_list=[]):
        
        # --- Preview Frame queue initialization ---
        self.preview_frame.clear_file_queue()
        for item in self.tree.get_children():
            self.tree.delete(item)

        if file_list:
            # Populate Treeview
            for f in file_list:
                if os.path.isfile(f):
                    try:
                        size_kb = os.path.getsize(f) // 1024
                        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(f)))
                        self.tree.insert("", "end", iid=f, values=(os.path.basename(f), size_kb, mtime))
                        self.preview_frame.add_file_to_queue(f)
                    except Exception as e:
                        self.tree.insert("", "end", iid=f, values=(os.path.basename(f), "读取失败", str(e)))
                else:
                    self.tree.insert("", "end", iid=f, values=(os.path.basename(f), "不存在", "-"))
        
            self.tree.bind("<<TreeviewSelect>>", self.on_select)

            # Default select the first
            if file_list:
                self.tree.selection_set(file_list[0])
                self.show_details(file_list[0])
                # Preview Frame sync to the first file
                # self._sync_preview_to_file(file_list[0])
    
    def _sync_preview_to_file(self, file_path):
        """
        Let preview_frame's queue_index point to file_path and display the file
        """
        try:
            queue = list(self.preview_frame._PreviewFrame__file_queue)
            idx = queue.index(file_path)
            self.preview_frame._queue_index = idx
            self.preview_frame.show_file(file_path)
            self.preview_frame._update_page_label()
        except Exception:
            pass

    # Detail display function
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
        typ, cat = self.sniff_type(path)
        meta['Format'] = typ
        meta['Category'] = cat
        meta['Location'] = path
        # Raster: display pixel dimensions (px)
        if cat == 'Raster' and typ not in ('PDF','SVG','EPS'):
            try:
                with Image.open(path) as im:
                    w, h = im.size
                    meta['Size'] = f'{w} × {h} px'
            except Exception as e:
                meta['Size'] = 'Read failed'
        # PDF/EPS/PS: display physical dimensions (cm)
        elif typ in ('PDF'):
            try:
                width_pt, height_pt = vec.get_pdf_size(path)
                if width_pt and height_pt:
                    width_in = width_pt/72
                    height_in = height_pt/72
                    meta['Size'] = f'{width_in*2.54:.2f} × {height_in*2.54:.2f} cm ({width_pt} × {height_pt} pt)'
                else:
                    meta['Size'] = 'N/A'
            except Exception:
                meta['Size'] = 'N/A'
        elif typ in ('EPS','PS'):
            try:
                width_pt, height_pt = vec.get_script_size(path)
                if width_pt and height_pt:
                    width_in = width_pt/72
                    height_in = height_pt/72
                    meta['Size'] = f'{width_in*2.54:.2f} × {height_in*2.54:.2f} cm ({width_pt} × {height_pt} pt)'
                else:
                    meta['Size'] = 'N/A'
            except Exception:
                meta['Size'] = 'N/A'
        # SVG: prefer width/height attributes (px), otherwise N/A
        elif typ == 'SVG':
            try:
                (w, h), unit = vec.get_svg_size(path)
                if w and h:
                    meta['Size'] = f'{w} × {h} {unit}'
                else:
                    meta['Size'] = 'N/A'
            except Exception:
                meta['Size'] = 'N/A'
        # Other cases
        else:
            meta['Size'] = 'N/A'
        # Vector analyzer additional information
        if cat == 'Vector':
            try:
                analysis = vec.vector_analyzer(path)
            except Exception:
                analysis = None
            if analysis:
                ana_type = analysis.get('type', 'unknown').title()
                if ana_type in ('Vector','Mixed','Raster'):
                    meta['Category'] = ana_type
                if 'num_paths' in analysis:
                    meta['Embedded Paths'] = analysis.get('num_paths', 0)
                if ana_type in ('Mixed','Raster'):
                    num_images = analysis.get('num_images', 0)
                    meta['Embedded Images'] = num_images
                    if num_images:
                        sizes = []
                        for iminfo in analysis.get('images', []):
                            rw = iminfo.get('real_width') or iminfo.get('width') or '?'
                            rh = iminfo.get('real_height') or iminfo.get('height') or '?'
                            sizes.append(f"{rw}x{rh} px")
                        meta['Image Sizes'] = ', '.join(sizes) if sizes else '-'
        return meta

    # Detail panel content refresh
    def show_details(self, path):
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        if not os.path.isfile(path):
            ttk.Label(self.detail_frame, text="File does not exist", foreground="red").pack(anchor="w")
            return
            
        # Read from cache or parse anew
        if path in self._file_meta_cache:
            meta = self._file_meta_cache[path]
        else:
            meta = self.read_image_meta(path)
            self._file_meta_cache[path] = meta
        # Display each item
        for k, v in meta.items():
            row = ttk.Frame(self.detail_frame)
            row.pack(fill="x", anchor="w", pady=1)
            ttk.Label(row, text=f"{k}: ", font=("TkDefaultFont", 10, "bold")).pack(side="left", anchor="w")
            ttk.Label(row, text=str(v), font=("TkDefaultFont", 10)).pack(side="left", anchor="w")

        # When detail panel refreshes, sync preview Frame to current file
        self._sync_preview_to_file(path)

    # Bind selection event
    def on_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.show_details(sel[0])
    

    def _on_preview_page_changed(self, event):
        # Only respond to events emitted by preview_frame itself
        if event.widget is not self.preview_frame:
            return
        queue = list(self.preview_frame._PreviewFrame__file_queue)
        idx = self.preview_frame._queue_index
        if 0 <= idx < len(queue):
            file_path = queue[idx]
            # Highlight the corresponding Treeview item
            self.tree.selection_set(file_path)
            self.tree.see(file_path)