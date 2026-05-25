"""
visualise.py
------------
Export visualisations: RGB composite, NDVI heatmap, classified land cover map,
and an interactive Folium HTML map.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from pathlib import Path

from classify import CLASS_COLOURS, CLASSES


def _normalise_for_display(arr: np.ndarray, brightness: float = 3.5) -> np.ndarray:
    """Clip and scale a reflectance band to [0, 1] for display."""
    return np.clip(arr * brightness, 0, 1)


def export_rgb_composite(
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    output_path: str,
) -> None:
    """
    Export a true-colour RGB composite PNG.

    Bands: B04 (Red), B03 (Green), B02 (Blue)
    Brightness factor applied to make the scene visually clear
    (Sentinel-2 surface reflectance values are typically 0.03–0.25,
    which appears very dark without enhancement).
    """
    rgb = np.dstack([
        _normalise_for_display(red),
        _normalise_for_display(green),
        _normalise_for_display(blue),
    ])
    fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0a0f1a")
    ax.imshow(rgb)
    ax.set_title("True Colour RGB Composite — Sentinel-2", fontsize=14,
                 fontweight="bold", color="white", pad=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#0a0f1a")
    plt.close(fig)
    print(f"  [✓] RGB composite → {output_path}")


def export_false_colour(
    nir: np.ndarray,
    red: np.ndarray,
    green: np.ndarray,
    output_path: str,
) -> None:
    """
    Export a false-colour infrared composite PNG.

    Bands: B08 (NIR) → Red channel, B04 (Red) → Green channel, B03 (Green) → Blue channel
    Vegetation appears bright red — the most common satellite image representation
    for vegetation analysis.
    """
    fcc = np.dstack([
        _normalise_for_display(nir),
        _normalise_for_display(red),
        _normalise_for_display(green),
    ])
    fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0a0f1a")
    ax.imshow(fcc)
    ax.set_title("False Colour Infrared Composite — Sentinel-2", fontsize=14,
                 fontweight="bold", color="white", pad=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#0a0f1a")
    plt.close(fig)
    print(f"  [✓] False colour composite → {output_path}")


def export_ndvi_heatmap(ndvi: np.ndarray, output_path: str) -> None:
    """
    Export NDVI as a colour-graded heatmap PNG.

    Colourmap: RdYlGn (red = low/negative NDVI, green = high NDVI)
    Range clamped to [-0.2, 0.8] to emphasise the vegetation signal.
    """
    fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0a0f1a")
    img = ax.imshow(ndvi, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
    cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("NDVI Value", color="white", fontsize=11)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    ax.set_title("NDVI — Normalised Difference Vegetation Index", fontsize=14,
                 fontweight="bold", color="white", pad=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#0a0f1a")
    plt.close(fig)
    print(f"  [✓] NDVI heatmap → {output_path}")


def export_classified_map(classified: np.ndarray, output_path: str) -> None:
    """
    Export the classified land cover map as a PNG with a legend.
    """
    # Build RGB image from class colours
    rgb = np.zeros((*classified.shape, 3), dtype=np.uint8)
    for class_id, colour in CLASS_COLOURS.items():
        rgb[classified == class_id] = colour

    fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0a0f1a")
    ax.imshow(rgb)
    ax.set_title("Land Cover Classification — Sentinel-2", fontsize=14,
                 fontweight="bold", color="white", pad=12)
    ax.axis("off")

    # Legend
    patches = [
        mpatches.Patch(
            color=tuple(c / 255 for c in colour),
            label=CLASSES[class_id]
        )
        for class_id, colour in CLASS_COLOURS.items()
    ]
    legend = ax.legend(
        handles=patches,
        loc="lower right",
        fontsize=10,
        framealpha=0.8,
        facecolor="#1a2a3a",
        edgecolor="#4aa8ff",
        labelcolor="white",
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#0a0f1a")
    plt.close(fig)
    print(f"  [✓] Classified map → {output_path}")


def export_interactive_map(
    lat: np.ndarray,
    lon: np.ndarray,
    ndvi: np.ndarray,
    output_path: str,
    center_lat: float = None,
    center_lon: float = None,
) -> None:
    """
    Export an interactive Folium HTML map with the scene bounding box.

    Note: Full raster overlay requires large file sizes — this version
    shows the scene center marker and NDVI statistics as a popup.
    For full tile overlay, use rasterio + Folium's ImageOverlay.
    """
    try:
        import folium
    except ImportError:
        print("  [!] folium not installed — skipping interactive map. Run: pip install folium")
        return

    c_lat = center_lat or float(np.nanmean(lat)) if lat is not None else 0
    c_lon = center_lon or float(np.nanmean(lon)) if lon is not None else 0

    m = folium.Map(
        location=[c_lat, c_lon],
        zoom_start=10,
        tiles="CartoDB dark_matter"
    )

    valid_ndvi = ndvi[~np.isnan(ndvi)]
    popup_text = (
        f"<b>Scene Centre</b><br>"
        f"Lat: {c_lat:.4f}° | Lon: {c_lon:.4f}°<br><br>"
        f"<b>NDVI Statistics</b><br>"
        f"Mean: {np.mean(valid_ndvi):.3f}<br>"
        f"Min:  {np.min(valid_ndvi):.3f}<br>"
        f"Max:  {np.max(valid_ndvi):.3f}<br>"
        f"Valid pixels: {len(valid_ndvi):,}"
    )

    folium.Marker(
        location=[c_lat, c_lon],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip="Scene Centre — click for NDVI stats",
        icon=folium.Icon(color="blue", icon="satellite", prefix="fa"),
    ).add_to(m)

    m.save(output_path)
    print(f"  [✓] Interactive map → {output_path}")
