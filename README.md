# ImBridge 🎛️🖼️

![License: MPL-2.0](https://img.shields.io/badge/License-MPL%202.0-orange.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

**ImBridge** is a lightweight desktop app for high‑quality image processing: **batch bitmap conversion**, **vector conversion**, and **image enhancement**. It focuses on local, fast, and reliable workflows powered by Python and a clean Tkinter UI.

## ✨ Features

- 🖼️ Batch bitmap conversion: PNG ⇄ JPEG ⇄ BMP ⇄ TIFF
- 🧭 Vector conversion: SVG ⇄ PDF ⇄ EPS/PS
- 🌉Conversion between bitmaps and vectors: SVG/PDF/EPS/PS ⇄ PNG/JPEG/BMP/TIFF

- 🔍 Enhancement toolkit: upscaling, sharpening/smoothing, grayscale/binarization, and bitmap→vector tracing (Potrace)
- 🔎 Vector analyzer: detect whether a PDF/SVG/EPS is vector/raster/mixed and summarize contents
- 💻 100% local processing: no uploads, predictable and privacy‑preserving


## 📦 Installation

### ✅ Requirements

- **Python 3.x** (recommended: latest 3.x release)
- **Required Python packages:**
	- Pillow, pillow-heif, numpy, cairosvg, reportlab, PyPDF2  
		(see `requirements.txt` for the full list)
- **External tools** (for vector workflows):
	- **Ghostscript** – PostScript/PDF interpreter for vector↔bitmap and vector↔vector conversions
	- **pstoedit** – Convert PS/EPS/PDF graphics to other vector formats (e.g., SVG)
	- **Potrace** – Trace bitmaps to clean, scalable vectors
	- **libcairo-2.dll** – Cairo graphics runtime required by certain SVG/PDF operations

> ℹ️ ImBridge provides an in‑app “Tool Check” to verify the availability of these external tools.

### 🛠️ Setup

1. **Create a virtual environment and install dependencies:**

	 ```powershell
	 python -m venv venv
   # On Windows:
	 .\venv\Scripts\Activate.ps1
   # Alternatively, on Linux:
   source venv/bin/activate
	 ```

2. Install Python dependencies:
   ```
	 pip install -r requirements.txt
   ```

2. **Install external tools** (if you need vector workflows):
	 - Download and install each tool above, and ensure they are available in your system `PATH`.
        - [Ghostscript](https://www.ghostscript.com/)
        - [pstoedit](http://www.pstoedit.net/)
        - [libcairo-2.dll (Cairo)](https://www.cairographics.org/download/)
        - [Potrace](http://potrace.sourceforge.net/)
              

## 🚀 Run

```powershell
python main.py
```

The app stores outputs under the `output/` directory by default (e.g., `vector_output/`, `bitmap_output/`, `enhance_output/`).

## 🧭 Usage Overview

### 1) Bitmap tab
- Select input files and output folder
- Pick target bitmap format (PNG/JPEG/BMP/TIFF) and optional quality (for JPEG)
- Convert in batch

### 2) Vector tab
- Analyze: summarize PDF/SVG/EPS contents (paths/images/type)
- Convert to vectors: SVG⇄PDF/EPS/PS
- Convert to bitmaps: choose DPI for high‑quality rasterization

### 3) Enhancement tab
- Upscale: increase resolution with high‑quality resampling and sharpening
- Grayscale/Binarization: prepare scans/signatures for documents
- Vectorization: trace small monochrome logos/signatures into vectors via Potrace

For detailed guidance, see the docs:
- Help: `docs/help.html`
- Image formats & DPI explained: `docs/image_formats.html`

## 🧪 Notes and Tips

- DPI only affects print/embedding size for bitmaps; screens care about pixels. See the Image Formats guide for more.
- When converting vectors to bitmaps, prefer higher DPI (e.g., 300–600) for crisp print output.
- Large image batches may take time; the UI logs progress and errors in the bottom log area.

## 🙏 Special Thanks

- Ghostscript – PostScript/PDF interpreter used for conversions
- pstoedit – PS/EPS/PDF to SVG and other vector formats
- Potrace – Bitmap‑to‑vector tracing
- libcairo-2.dll – Cairo graphics runtime used by vector processing

## 📄 License

MIT License. See `LICENSE`.

## 🤝 Contributing

Issues and PRs are welcome. If you add support for more formats or platforms, please document any new external dependencies and add checks to the Tool Check section.
