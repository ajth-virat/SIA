# Sentinel-2 Satellite Image Analysis Pipeline

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat)
![Data](https://img.shields.io/badge/Data-Sentinel--2%20L2A-4CAF50?style=flat)
![Source](https://img.shields.io/badge/Source-Microsoft%20Planetary%20Computer-0078D4?style=flat&logo=microsoft&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

---

This pipeline takes Sentinel-2 satellite imagery — either from a local `.SAFE` folder or streamed live from Microsoft Planetary Computer — and runs it through six stages: band ingestion, cloud masking, spectral index computation (NDVI, NDWI, NBR, BSI), rule-based land cover classification, and visual export. No GIS software needed. No manual tile stitching. You give it a bounding box and a date range; it finds the best available cloud-free scene and dumps everything into an `outputs/` folder — PNGs, an interactive HTML map, and a JSON summary with scene statistics.

---

## Setup

### Windows — just run `run.bat`

Double-click `run.bat`. It creates a virtual environment, installs dependencies (first run takes 2–5 min), and starts the pipeline. You'll be asked two questions:

```
Bounding box: 80.20, 12.90, 80.35, 13.10   ← central Chennai, or press Enter for default
Date range  : 2024-01-01/2024-04-01         ← or press Enter for the last 3 months
```

Done. Everything saves to `outputs/`.

---

### macOS / Linux — manual setup

**1. Install GDAL** (required by rasterio)

macOS:
```bash
brew install gdal
```

Ubuntu / Debian:
```bash
sudo apt-get install gdal-bin libgdal-dev
```

**2. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**3. Run**

Stream from Planetary Computer (no account needed):
```bash
python fetch_and_run.py
```

Run from a local `.SAFE` folder:
```bash
python main.py --safe path/to/scene.SAFE
python main.py --safe path/to/scene.SAFE --output results/march2024/
```

---

## Getting Sentinel-2 Data

**Option A — Stream it (recommended)**

Use `fetch_and_run.py`. It pulls data directly via the Planetary Computer STAC API — no account, no 800 MB download. Only the pixels inside your bounding box come through.

**Option B — Download manually**

1. Register free at [dataspace.copernicus.eu](https://dataspace.copernicus.eu/)
2. Search for Sentinel-2 L2A, filter: Cloud cover < 10%, Product type: S2MSI2A
3. Download the `.SAFE` folder (~800 MB), then point `main.py` at it

---

## What It Outputs

| File | What it is |
|---|---|
| `rgb_composite.png` | True colour image (B04·B03·B02) |
| `false_colour.png` | Infrared composite — vegetation shows red (B08·B04·B03) |
| `ndvi_heatmap.png` | Vegetation health map (RdYlGn colour scale) |
| `land_cover_classified.png` | 5-class land cover map with legend |
| `interactive_map.html` | Browser map with georeferenced NDVI overlay and stats popup |
| `summary.json` | Scene statistics: index values, land cover percentages, metadata |

---

## Land Cover Classes

| Class | Colour | Condition |
|---|---|---|
| Water | Blue | NDWI > 0.3 |
| Vegetation | Green | NDVI > 0.4 |
| Bare Soil | Tan | BSI > 0.1 and NDVI < 0.2 |
| Urban / Built-Up | Red | BSI > 0.0, NDVI < 0.1, NDWI < 0.0 |
| Other | Grey | All remaining valid pixels |
| No Data | Dark | Cloud-masked or invalid pixels |

---

## Spectral Indices

| Index | Formula | What it detects |
|---|---|---|
| NDVI | (NIR − Red) / (NIR + Red) | Vegetation health and density |
| NDWI | (Green − NIR) / (Green + NIR) | Open water |
| NBR | (NIR − SWIR2) / (NIR + SWIR2) | Burn severity, fire mapping |
| BSI | ((SWIR1+Red) − (NIR+Blue)) / ((SWIR1+Red) + (NIR+Blue)) | Bare soil and urban surfaces |

---

## Pipeline Stages

```
Sentinel-2 .SAFE  ──OR──  Planetary Computer API
         │
         ▼
  1. Ingest       Load B02–B12 + SCL bands, parse XML metadata
         ▼
  2. Preprocess   Resample 20m→10m, cloud mask via SCL, DOS1 correction
         ▼
  3. Indices      Compute NDVI, NDWI, NBR, BSI
         ▼
  4. Classify     Rule-based land cover (5 classes)
         ▼
  5. Visualise    RGB, false colour, NDVI heatmap, classified map, HTML map
         ▼
  6. Report       summary.json + console statistics
```

| Module | Does |
|---|---|
| `ingest.py` | Band loading and metadata parsing |
| `preprocess.py` | Resampling, cloud masking, DOS1 atmospheric correction |
| `indices.py` | NDVI, NDWI, NBR, BSI |
| `classify.py` | Rule-based land cover classification |
| `visualise.py` | Image and map export |
| `report.py` | JSON summary and console output |

---

## Project Structure

```
├── main.py              # Local .SAFE workflow
├── fetch_and_run.py     # Planetary Computer streaming workflow
├── run.bat              # Windows one-click launcher
├── requirements.txt
│
├── ingest.py
├── preprocess.py
├── indices.py
├── classify.py
├── visualise.py
├── report.py
│
├── cache/               # Auto-generated — cached band arrays
└── outputs/             # Auto-generated — all output files
```

---

## Libraries Used

| Purpose | Library |
|---|---|
| Raster I/O | `rasterio` |
| Computation | `numpy` |
| Visualisation | `matplotlib` |
| Interactive maps | `folium` |
| STAC catalogue | `pystac-client` |
| Planetary Computer auth | `planetary-computer` |

---

## Author

**Ajith Virat Sridhara Narasimhan**  
PG Certificate in Space Engineering — University of Surrey, UK  
BTech Aerospace Engineering — Bharath University (BIHER), India
