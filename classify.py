"""
classify.py
-----------
Rule-based land cover classification from spectral indices.
Priority order ensures physically meaningful class assignment.
"""

import numpy as np

# Class label mapping
CLASSES = {
    0: "No Data / Cloud",
    1: "Water",
    2: "Vegetation",
    3: "Bare Soil",
    4: "Urban / Built-Up",
    5: "Other / Unclassified",
}

# Colour map for visualisation (RGB tuples 0-255)
CLASS_COLOURS = {
    0: (30,  30,  30),   # Dark grey  — No Data
    1: (30,  90,  200),  # Blue       — Water
    2: (50,  160,  50),  # Green      — Vegetation
    3: (180, 140,  80),  # Tan        — Bare Soil
    4: (180,  80,  80),  # Red        — Urban
    5: (150, 150, 150),  # Mid grey   — Other
}


def classify_land_cover(
    ndvi: np.ndarray,
    ndwi: np.ndarray,
    bsi:  np.ndarray,
) -> np.ndarray:
    """
    Assign a land cover class to each pixel using index thresholds.

    Classification priority (later assignments overwrite earlier ones):
      5. Other (default)
      4. Urban   : BSI > 0.0  AND  NDVI < 0.1  AND  NDWI < 0.0
      3. Bare    : BSI > 0.1  AND  NDVI < 0.2
      2. Vegetation : NDVI > 0.4
      1. Water   : NDWI > 0.3           ← highest priority
      0. No Data : NDVI is NaN

    Priority order is physically motivated:
      - Water is the most spectrally distinct class — assign last to win
      - Dense vegetation is unambiguous above NDVI 0.4
      - Urban and bare soil are separated by BSI magnitude

    Parameters
    ----------
    ndvi, ndwi, bsi : float32 2D arrays of the same shape

    Returns
    -------
    uint8 2D array of class labels (0–5)
    """
    classified = np.full(ndvi.shape, 5, dtype=np.uint8)   # default: Other

    # Urban
    urban_mask = (bsi > 0.0) & (ndvi < 0.1) & (ndwi < 0.0)
    classified[urban_mask] = 4

    # Bare Soil
    bare_mask = (bsi > 0.1) & (ndvi < 0.2)
    classified[bare_mask] = 3

    # Vegetation
    veg_mask = ndvi > 0.4
    classified[veg_mask] = 2

    # Water — highest priority, applied last
    water_mask = ndwi > 0.3
    classified[water_mask] = 1

    # No Data
    nodata_mask = np.isnan(ndvi)
    classified[nodata_mask] = 0

    return classified


def classification_stats(classified: np.ndarray) -> dict:
    """
    Compute percentage coverage of each class.

    Parameters
    ----------
    classified : uint8 2D array from classify_land_cover()

    Returns
    -------
    dict mapping class name → percentage of total pixels
    """
    total = classified.size
    stats = {}
    for class_id, class_name in CLASSES.items():
        count = int((classified == class_id).sum())
        stats[class_name] = round(100.0 * count / total, 2)
    return stats


def classified_to_rgb(classified: np.ndarray) -> np.ndarray:
    """
    Convert a classified label array to an RGB image for export.

    Parameters
    ----------
    classified : uint8 2D array of class labels

    Returns
    -------
    uint8 3D array of shape (H, W, 3) — RGB image
    """
    rgb = np.zeros((*classified.shape, 3), dtype=np.uint8)
    for class_id, colour in CLASS_COLOURS.items():
        mask = classified == class_id
        rgb[mask] = colour
    return rgb
