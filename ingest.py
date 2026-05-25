"""
ingest.py
---------
Loads Sentinel-2 .SAFE folder bands into NumPy arrays and parses scene metadata.
"""

import numpy as np
import rasterio
import xml.etree.ElementTree as ET
from pathlib import Path


BANDS_NEEDED = {
    "B02": {"name": "Blue",        "resolution": 10},
    "B03": {"name": "Green",       "resolution": 10},
    "B04": {"name": "Red",         "resolution": 10},
    "B08": {"name": "NIR",         "resolution": 10},
    "B11": {"name": "SWIR1",       "resolution": 20},
    "B12": {"name": "SWIR2",       "resolution": 20},
    "SCL": {"name": "SceneClass",  "resolution": 20},
}


def load_bands(safe_path: str) -> dict:
    """
    Load all required Sentinel-2 bands from a .SAFE folder.

    Parameters
    ----------
    safe_path : str
        Path to the Sentinel-2 .SAFE directory.

    Returns
    -------
    dict
        Keys are band IDs (e.g. 'B04').
        Values are dicts with keys: data (ndarray), profile, transform, crs, resolution.
    """
    safe = Path(safe_path)
    if not safe.exists():
        raise FileNotFoundError(f"SAFE path not found: {safe_path}")

    loaded = {}
    for band_id, meta in BANDS_NEEDED.items():
        matches = list(safe.rglob(f"*_{band_id}_*.jp2"))
        if not matches:
            matches = list(safe.rglob(f"*{band_id}*.jp2"))
        if not matches:
            raise FileNotFoundError(
                f"Band {band_id} not found in {safe_path}. "
                f"Ensure this is a valid Sentinel-2 L2A .SAFE folder."
            )
        with rasterio.open(matches[0]) as src:
            loaded[band_id] = {
                "data":       src.read(1).astype(np.float32),
                "profile":    src.profile,
                "transform":  src.transform,
                "crs":        src.crs,
                "resolution": meta["resolution"],
                "name":       meta["name"],
            }
        print(f"  [✓] Loaded {band_id} ({meta['name']}) @ {meta['resolution']}m")

    return loaded


def load_metadata(safe_path: str) -> dict:
    """
    Parse MTD_MSIL2A.xml for scene-level metadata.

    Returns
    -------
    dict with keys: date, cloud_cover, tile_id, processing_level
    """
    safe = Path(safe_path)
    xml_candidates = list(safe.glob("MTD_MSIL2A.xml"))
    if not xml_candidates:
        raise FileNotFoundError(f"MTD_MSIL2A.xml not found in {safe_path}")

    tree = ET.parse(xml_candidates[0])
    root = tree.getroot()

    def find_text(tag):
        el = root.find(f".//{tag}")
        return el.text if el is not None else "Unknown"

    return {
        "date":             find_text("DATATAKE_SENSING_START"),
        "cloud_cover":      float(find_text("Cloud_Coverage_Assessment") or 0),
        "tile_id":          find_text("TILE_ID"),
        "processing_level": find_text("PROCESSING_LEVEL"),
    }
