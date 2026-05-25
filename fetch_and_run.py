"""
fetch_and_run.py
----------------
Fetches Sentinel-2 data from Microsoft Planetary Computer and runs the full pipeline.
- Parallel band downloads (all 7 bands at once)
- Cache: reruns with same bbox/date skip the download entirely
"""

import sys
import os
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

CACHE_DIR = Path("cache")


def ask_bbox():
    print("  Enter the area you want to analyse as a bounding box.")
    print("  Format : min_longitude, min_latitude, max_longitude, max_latitude")
    print("  Example: 80.20, 12.90, 80.35, 13.10  (central Chennai)")
    print("  Press Enter to use the default (central Chennai).")
    print()
    raw = input("  Bounding box: ").strip()
    if not raw:
        raw = "80.20, 12.90, 80.35, 13.10"
        print(f"  Using default: {raw}")
    try:
        parts = [float(x.strip()) for x in raw.split(",")]
        assert len(parts) == 4
        return parts
    except Exception:
        print("  Could not read that. Using default (Chennai).")
        return [80.20, 12.90, 80.35, 13.10]


def ask_date_range():
    print()
    print("  Enter a date range to search for cloud-free scenes.")
    print("  Format : YYYY-MM-DD/YYYY-MM-DD")
    print("  Press Enter to search the last 3 months automatically.")
    print()
    raw = input("  Date range: ").strip()
    if not raw:
        end   = datetime.now()
        start = end - timedelta(days=90)
        raw   = f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
        print(f"  Using: {raw}")
    return raw


def cache_key(bbox, scene_date):
    raw = f"{bbox}-{scene_date}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def save_cache(key, bands, metadata):
    CACHE_DIR.mkdir(exist_ok=True)
    arrays = {bid: b["data"] for bid, b in bands.items()}
    meta_strip = {bid: {k: v for k, v in b.items() if k != "data" and k not in ("profile", "transform", "crs")}
                  for bid, b in bands.items()}
    np.savez_compressed(CACHE_DIR / f"{key}.npz", **arrays)
    with open(CACHE_DIR / f"{key}.json", "w") as f:
        json.dump({"metadata": metadata, "band_meta": meta_strip}, f)
    print("  [OK] Scene cached for instant reuse next time.")


def load_cache(key, bands_needed):
    npz_path  = CACHE_DIR / f"{key}.npz"
    json_path = CACHE_DIR / f"{key}.json"
    if not npz_path.exists() or not json_path.exists():
        return None, None
    print("  [CACHE HIT] Loading from local cache — skipping download.")
    npz = np.load(npz_path)
    with open(json_path) as f:
        saved = json.load(f)
    bands = {}
    for bid in bands_needed:
        if bid in npz:
            bands[bid] = {
                "data":       npz[bid],
                "profile":    {},
                "transform":  None,
                "crs":        None,
                "resolution": saved["band_meta"][bid]["resolution"],
                "name":       saved["band_meta"][bid]["name"],
            }
    return bands, saved["metadata"]


def fetch_band(args):
    href, bbox, band_id, meta = args
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    with rasterio.open(href) as src:
        dst_crs = src.crs
        left, bottom, right, top = transform_bounds(
            CRS.from_epsg(4326), dst_crs,
            bbox[0], bbox[1], bbox[2], bbox[3]
        )
        window = from_bounds(left, bottom, right, top, src.transform)
        data   = src.read(1, window=window).astype(np.float32)
        result = {
            "data":       data,
            "profile":    src.profile,
            "transform":  src.window_transform(window),
            "crs":        src.crs,
            "resolution": meta["resolution"],
            "name":       meta["name"],
        }
    return band_id, result


def main():
    print()
    print("=" * 60)
    print("  SATELLITE IMAGE ANALYSIS PIPELINE")
    print("  Data source: Microsoft Planetary Computer (free)")
    print("=" * 60)
    print()

    bbox       = ask_bbox()
    date_range = ask_date_range()

    print()
    print("[1/6] SEARCHING FOR SCENES...")

    try:
        import planetary_computer
        import pystac_client
        import rasterio
    except ImportError as e:
        print(f"  ERROR: Missing package — {e}")
        input("\nPress Enter to close...")
        sys.exit(1)

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": 15}},
        sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        max_items=5,
    )

    items = list(search.items())
    if not items:
        print("  No suitable scenes found. Try a wider date range.")
        input("\nPress Enter to close...")
        sys.exit(1)

    item        = items[0]
    scene_date  = item.properties["datetime"][:10]
    print(f"  [OK] Scene found:")
    print(f"       Date       : {scene_date}")
    print(f"       Cloud cover: {item.properties['eo:cloud_cover']:.1f}%")
    print(f"       Tile ID    : {item.properties.get('s2:mgrs_tile', 'Unknown')}")

    BANDS_NEEDED = {
        "B02": {"name": "Blue",        "resolution": 10},
        "B03": {"name": "Green",       "resolution": 10},
        "B04": {"name": "Red",         "resolution": 10},
        "B08": {"name": "NIR",         "resolution": 10},
        "B11": {"name": "SWIR1",       "resolution": 20},
        "B12": {"name": "SWIR2",       "resolution": 20},
        "SCL": {"name": "SceneClass",  "resolution": 20},
    }

    metadata = {
        "date":             scene_date,
        "cloud_cover":      item.properties["eo:cloud_cover"],
        "tile_id":          item.properties.get("s2:mgrs_tile", "Unknown"),
        "processing_level": "L2A",
    }

    # ── CHECK CACHE ──────────────────────────────────────────────
    key = cache_key(bbox, scene_date)
    bands, cached_meta = load_cache(key, BANDS_NEEDED)

    if bands is None:
        print()
        print("[2/6] LOADING BANDS FROM API (parallel)...")

        available_assets = list(item.assets.keys())
        tasks = []
        for band_id, meta in BANDS_NEEDED.items():
            candidates = [band_id, band_id.lower(), f"B{int(band_id[1:]):02d}" if band_id != "SCL" else "SCL"]
            asset_key  = next((k for k in candidates if k in available_assets), None)
            if asset_key is None:
                print(f"  [!!] {band_id} not found, skipping.")
                continue
            tasks.append((item.assets[asset_key].href, bbox, band_id, BANDS_NEEDED[band_id]))

        bands      = {}
        completed  = 0
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {executor.submit(fetch_band, t): t[2] for t in tasks}
            for future in as_completed(futures):
                band_id = futures[future]
                try:
                    bid, result = future.result()
                    bands[bid]  = result
                    completed  += 1
                    print(f"  [{completed}/7] {bid} ({result['name']}) done", flush=True)
                except Exception as e:
                    print(f"  [!!] {band_id} failed — {e}")

        required = {"B02", "B03", "B04", "B08", "B11", "B12", "SCL"}
        missing  = required - set(bands.keys())
        if missing:
            print(f"\n  ERROR: Missing bands: {missing}")
            input("\nPress Enter to close...")
            sys.exit(1)

        # Normalize shapes
        ref = bands["B02"]["data"]
        H   = (ref.shape[0] // 2) * 2
        W   = (ref.shape[1] // 2) * 2
        for bid in bands:
            if bands[bid]["resolution"] == 10:
                bands[bid]["data"] = bands[bid]["data"][:H, :W]
            else:
                bands[bid]["data"] = bands[bid]["data"][:H // 2, :W // 2]

        save_cache(key, bands, metadata)
    else:
        metadata = cached_meta
        # Still normalize shapes from cache
        ref = bands["B02"]["data"]
        H   = (ref.shape[0] // 2) * 2
        W   = (ref.shape[1] // 2) * 2
        for bid in bands:
            if bands[bid]["resolution"] == 10:
                bands[bid]["data"] = bands[bid]["data"][:H, :W]
            else:
                bands[bid]["data"] = bands[bid]["data"][:H // 2, :W // 2]

    # ── PIPELINE ─────────────────────────────────────────────────
    try:
        from preprocess import preprocess_all_bands
        from indices    import compute_all_indices
        from classify   import classify_land_cover, classification_stats
        from visualise  import (
            export_rgb_composite, export_false_colour,
            export_ndvi_heatmap, export_classified_map,
        )
        from report import generate_summary, print_report
    except ImportError as e:
        print(f"\n  ERROR: Could not import pipeline module — {e}")
        input("\nPress Enter to close...")
        sys.exit(1)

    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)

    print()
    print("[3/6] PREPROCESSING...")
    bands = preprocess_all_bands(bands)

    print()
    print("[4/6] COMPUTING SPECTRAL INDICES...")
    indices = compute_all_indices(bands)

    print()
    print("[5/6] CLASSIFYING LAND COVER...")
    classified = classify_land_cover(indices["ndvi"], indices["ndwi"], indices["bsi"])
    stats      = classification_stats(classified)
    for cls, pct in stats.items():
        print(f"  {cls:<25s} {pct:.1f}%")

    print()
    print("[6/6] EXPORTING MAPS AND IMAGES...")
    export_rgb_composite(bands["B02"]["data"], bands["B03"]["data"], bands["B04"]["data"], str(out_dir / "rgb_composite.png"))
    export_false_colour(bands["B08"]["data"], bands["B04"]["data"], bands["B03"]["data"], str(out_dir / "false_colour.png"))
    export_ndvi_heatmap(indices["ndvi"], str(out_dir / "ndvi_heatmap.png"))
    export_classified_map(classified, str(out_dir / "land_cover_classified.png"))

    # Interactive NDVI map with real overlay
    import folium
    import folium.raster_layers
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import io, base64

    ndvi      = indices["ndvi"]
    valid     = ndvi[~np.isnan(ndvi)]
    center    = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]
    bounds    = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]

    cmap      = plt.get_cmap("RdYlGn")
    norm      = mcolors.Normalize(vmin=-0.2, vmax=0.8)
    ndvi_disp = np.where(np.isnan(ndvi), 0, ndvi)
    rgba      = cmap(norm(ndvi_disp))
    alpha     = np.where(np.isnan(ndvi), 0, 0.7)
    rgba[..., 3] = alpha

    fig, ax = plt.subplots(figsize=(1, 1))
    ax.imshow(rgba, aspect="auto")
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=300)
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")

    m = folium.Map(tiles="CartoDB dark_matter")
    m.fit_bounds(bounds)
    folium.raster_layers.ImageOverlay(
        image=f"data:image/png;base64,{img_b64}",
        bounds=bounds, opacity=0.7, name="NDVI Heatmap",
    ).add_to(m)
    folium.LayerControl().add_to(m)
    folium.Marker(
        location=center,
        popup=folium.Popup(
            f"<b>NDVI Statistics</b><br>"
            f"Mean: {np.mean(valid):.3f}<br>Min: {np.min(valid):.3f}<br>"
            f"Max: {np.max(valid):.3f}<br>Valid pixels: {len(valid):,}<br><br>"
            f"<span style='color:red'>Red</span> = bare/urban<br>"
            f"<span style='color:green'>Green</span> = vegetation",
            max_width=250,
        ),
        tooltip="Click for NDVI stats",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)
    m.save(str(out_dir / "interactive_map.html"))
    print("  [OK] Interactive NDVI map saved")

    print()
    print("[DONE] Generating report...")
    summary = generate_summary(metadata, indices, stats, str(out_dir))
    print_report(summary)

    print(f"  All outputs saved to: {out_dir.resolve()}")
    print()
    print("  rgb_composite.png         — True colour image")
    print("  false_colour.png          — Vegetation in red")
    print("  ndvi_heatmap.png          — Vegetation health map")
    print("  land_cover_classified.png — Land cover map")
    print("  interactive_map.html      — Open in browser")
    print("  summary.json              — Raw statistics")
    print()
    input("Press Enter to close...")


if __name__ == "__main__":
    main()