"""
preprocess.py
-------------
Resampling, cloud masking, and DOS1 atmospheric correction for Sentinel-2 bands.
"""

import numpy as np


# SCL classes considered valid (cloud-free) pixels
VALID_SCL_CLASSES = [4, 5, 6, 7, 11]  # vegetation, bare, water, unclassified, snow


def resample_to_10m(band_data: np.ndarray, src_resolution: int) -> np.ndarray:
    """
    Upsample a band from 20m or 60m to 10m resolution using nearest-neighbour.

    Sentinel-2 bands at 20m (B11, B12, SCL) must match the 10m bands
    (B02, B03, B04, B08) before any per-pixel computation can be done.

    Parameters
    ----------
    band_data      : 2D NumPy array at source resolution
    src_resolution : source resolution in metres (10, 20, or 60)

    Returns
    -------
    2D NumPy array at 10m resolution
    """
    if src_resolution == 10:
        return band_data
    scale = src_resolution // 10
    return np.repeat(np.repeat(band_data, scale, axis=0), scale, axis=1)


def apply_cloud_mask(band_array: np.ndarray, scl: np.ndarray) -> np.ndarray:
    """
    Mask cloud, shadow, and no-data pixels using the SCL layer.

    SCL class reference:
      0  = No Data
      1  = Saturated / Defective
      2  = Dark Area Pixels
      3  = Cloud Shadow
      4  = Vegetation          ← valid
      5  = Bare Soils          ← valid
      6  = Water               ← valid
      7  = Unclassified        ← valid
      8  = Cloud Medium Prob
      9  = Cloud High Prob
      10 = Thin Cirrus
      11 = Snow / Ice          ← valid

    Invalid pixels are set to NaN so they are excluded from all index
    calculations and statistics automatically.

    Parameters
    ----------
    band_array : 2D float32 array (one band)
    scl        : 2D SCL array, same shape as band_array

    Returns
    -------
    2D float32 array with invalid pixels as NaN
    """
    mask = np.isin(scl, VALID_SCL_CLASSES)
    result = band_array.copy()
    result[~mask] = np.nan
    return result


def dos1_correction(band_array: np.ndarray) -> np.ndarray:
    """
    Apply DOS1 (Dark Object Subtraction) atmospheric correction.

    Principle:
      The darkest pixel in a scene — deep shadow, deep water — should
      theoretically have near-zero surface reflectance. Any signal above
      zero is atmospheric path radiance (scattering). Subtracting this
      minimum value corrects for atmospheric haze.

    Formula:
      Surface Reflectance = (DN - DN_dark) / 10000

    The 1st percentile of valid pixels is used as DN_dark to avoid
    influence from noise or sensor artefacts at the absolute minimum.

    Output is clipped to [0, 1] — valid surface reflectance range.

    Parameters
    ----------
    band_array : 2D float32 array (cloud-masked, raw DN values)

    Returns
    -------
    2D float32 array of surface reflectance values in [0, 1]
    """
    valid_pixels = band_array[~np.isnan(band_array)]
    if len(valid_pixels) == 0:
        return band_array  # fully clouded scene — return as-is

    dark_object_dn = np.percentile(valid_pixels, 1)
    corrected = (band_array - dark_object_dn) / 10000.0
    return np.clip(corrected, 0, 1)


def preprocess_all_bands(bands: dict) -> dict:
    """
    Apply full preprocessing pipeline to all bands in order:
      1. Resample 20m bands to 10m
      2. Apply cloud mask using SCL
      3. Apply DOS1 atmospheric correction

    Parameters
    ----------
    bands : dict returned by ingest.load_bands()

    Returns
    -------
    dict with same structure, data arrays fully preprocessed
    """
    print("\n[PREPROCESS] Resampling 20m bands to 10m...")
    for band_id in ["B11", "B12", "SCL"]:
        bands[band_id]["data"] = resample_to_10m(
            bands[band_id]["data"], src_resolution=20
        )

    scl = bands["SCL"]["data"]
    print("[PREPROCESS] Applying cloud mask...")
    for band_id in ["B02", "B03", "B04", "B08", "B11", "B12"]:
        bands[band_id]["data"] = apply_cloud_mask(bands[band_id]["data"], scl)

    print("[PREPROCESS] Applying DOS1 atmospheric correction...")
    for band_id in ["B02", "B03", "B04", "B08", "B11", "B12"]:
        bands[band_id]["data"] = dos1_correction(bands[band_id]["data"])
        print(f"  [✓] {band_id} corrected")

    return bands
