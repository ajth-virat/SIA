"""
indices.py
----------
Spectral index computation from preprocessed Sentinel-2 surface reflectance bands.
All indices return float32 arrays with NaN where data is invalid.
"""

import numpy as np


def _safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Compute ratio, setting result to NaN where denominator is zero or NaN."""
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(
            (denominator != 0) & ~np.isnan(denominator) & ~np.isnan(numerator),
            numerator / denominator,
            np.nan,
        )
    return result.astype(np.float32)


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Normalised Difference Vegetation Index.

    Formula : (NIR - Red) / (NIR + Red)
    Range   : -1 to +1

    Interpretation:
      > 0.6        Dense, healthy vegetation
      0.2 – 0.6   Moderate vegetation / crops
      0.0 – 0.2   Sparse vegetation / grassland
      < 0.0        Water, urban, bare soil, clouds

    Physics: Healthy chlorophyll strongly absorbs red light for
    photosynthesis and reflects NIR. The ratio isolates this signature
    independent of illumination angle.

    Bands used: B08 (NIR), B04 (Red)
    """
    return _safe_ratio(nir - red, nir + red)


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalised Difference Water Index (McFeeters, 1996).

    Formula : (Green - NIR) / (Green + NIR)
    Range   : -1 to +1

    Interpretation:
      > 0.3    Open water bodies (rivers, lakes, reservoirs)
      < 0.0    Non-water surfaces

    Physics: Water absorbs NIR and reflects green. Vegetation does
    the opposite — this makes NDWI effective at isolating water bodies.

    Bands used: B03 (Green), B08 (NIR)
    """
    return _safe_ratio(green - nir, green + nir)


def compute_nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """
    Normalised Burn Ratio.

    Formula : (NIR - SWIR2) / (NIR + SWIR2)
    Range   : -1 to +1

    Interpretation:
      High NBR  = Healthy vegetation
      Low NBR   = Burned / disturbed areas, bare soil
      dNBR      = Pre-fire NBR minus post-fire NBR — gives burn severity

    Bands used: B08 (NIR), B12 (SWIR2)
    """
    return _safe_ratio(nir - swir2, nir + swir2)


def compute_bsi(
    blue: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir1: np.ndarray,
) -> np.ndarray:
    """
    Bare Soil Index.

    Formula : ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))
    Range   : -1 to +1

    Interpretation:
      High BSI  = Exposed bare soil, construction sites, deserts, urban
      Low BSI   = Vegetated or water surfaces

    Physics: Soil strongly reflects SWIR and Red; vegetation suppresses
    these bands. Combining four bands improves separation from vegetation
    and water.

    Bands used: B02 (Blue), B04 (Red), B08 (NIR), B11 (SWIR1)
    """
    numerator   = (swir1 + red) - (nir + blue)
    denominator = (swir1 + red) + (nir + blue)
    return _safe_ratio(numerator, denominator)


def compute_all_indices(bands: dict) -> dict:
    """
    Compute all four spectral indices from a preprocessed bands dict.

    Parameters
    ----------
    bands : dict returned by preprocess.preprocess_all_bands()

    Returns
    -------
    dict with keys: ndvi, ndwi, nbr, bsi — each a float32 ndarray
    """
    print("\n[INDICES] Computing spectral indices...")

    indices = {
        "ndvi": compute_ndvi(bands["B08"]["data"], bands["B04"]["data"]),
        "ndwi": compute_ndwi(bands["B03"]["data"], bands["B08"]["data"]),
        "nbr":  compute_nbr(bands["B08"]["data"],  bands["B12"]["data"]),
        "bsi":  compute_bsi(
            bands["B02"]["data"],
            bands["B04"]["data"],
            bands["B08"]["data"],
            bands["B11"]["data"],
        ),
    }

    for name, arr in indices.items():
        valid = arr[~np.isnan(arr)]
        print(
            f"  [✓] {name.upper():5s}  mean={np.mean(valid):+.3f}  "
            f"min={np.min(valid):+.3f}  max={np.max(valid):+.3f}"
        )

    return indices
