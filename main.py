"""
main.py
-------
Entry point for the Satellite Image Analysis Pipeline.

Usage:
    python main.py --safe path/to/scene.SAFE
    python main.py --safe path/to/scene.SAFE --output outputs/

The pipeline runs six stages in order:
  1. Ingest      — load bands and metadata
  2. Preprocess  — resample, cloud mask, atmospheric correction
  3. Indices     — NDVI, NDWI, NBR, BSI
  4. Classify    — rule-based land cover classification
  5. Visualise   — export all maps and composites
  6. Report      — JSON summary + console report

Outputs written to --output directory (default: outputs/)
"""

import sys
import os
import argparse
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingest     import load_bands, load_metadata
from preprocess import preprocess_all_bands
from indices    import compute_all_indices
from classify   import classify_land_cover, classification_stats
from visualise  import (
    export_rgb_composite,
    export_false_colour,
    export_ndvi_heatmap,
    export_classified_map,
    export_interactive_map,
)
from report import generate_summary, print_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Satellite Image Analysis Pipeline — Sentinel-2"
    )
    parser.add_argument(
        "--safe",
        required=True,
        help="Path to Sentinel-2 .SAFE folder"
    )
    parser.add_argument(
        "--output",
        default="outputs",
        help="Output directory (default: outputs/)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("  SATELLITE IMAGE ANALYSIS PIPELINE")
    print("  Sentinel-2 · Python · ESA SNAP-compatible")
    print("=" * 60)

    # ── STAGE 1: INGEST ──────────────────────────────────────────
    print("\n[1/6] INGESTING BANDS...")
    bands    = load_bands(args.safe)
    metadata = load_metadata(args.safe)
    print(f"  Scene date : {metadata['date']}")
    print(f"  Tile ID    : {metadata['tile_id']}")
    print(f"  Cloud cover: {metadata['cloud_cover']}%")

    # ── STAGE 2: PREPROCESS ──────────────────────────────────────
    print("\n[2/6] PREPROCESSING...")
    bands = preprocess_all_bands(bands)

    # ── STAGE 3: INDICES ─────────────────────────────────────────
    print("\n[3/6] COMPUTING SPECTRAL INDICES...")
    indices = compute_all_indices(bands)

    # ── STAGE 4: CLASSIFY ────────────────────────────────────────
    print("\n[4/6] CLASSIFYING LAND COVER...")
    classified = classify_land_cover(
        indices["ndvi"],
        indices["ndwi"],
        indices["bsi"],
    )
    stats = classification_stats(classified)
    for cls, pct in stats.items():
        print(f"  {cls:<25s} {pct:.1f}%")

    # ── STAGE 5: VISUALISE ───────────────────────────────────────
    print("\n[5/6] EXPORTING VISUALISATIONS...")
    export_rgb_composite(
        bands["B02"]["data"],
        bands["B03"]["data"],
        bands["B04"]["data"],
        str(out_dir / "rgb_composite.png"),
    )
    export_false_colour(
        bands["B08"]["data"],
        bands["B04"]["data"],
        bands["B03"]["data"],
        str(out_dir / "false_colour.png"),
    )
    export_ndvi_heatmap(
        indices["ndvi"],
        str(out_dir / "ndvi_heatmap.png"),
    )
    export_classified_map(
        classified,
        str(out_dir / "land_cover_classified.png"),
    )
    export_interactive_map(
        lat=None, lon=None,
        ndvi=indices["ndvi"],
        output_path=str(out_dir / "interactive_map.html"),
    )

    # ── STAGE 6: REPORT ──────────────────────────────────────────
    print("\n[6/6] GENERATING REPORT...")
    summary = generate_summary(metadata, indices, stats, str(out_dir))
    print_report(summary)

    print(f"All outputs saved to: {out_dir.resolve()}\n")


if __name__ == "__main__":
    main()
