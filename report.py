"""
report.py
---------
Generate JSON summary statistics and a plain-text report for the pipeline run.
"""

import json
import numpy as np
from datetime import datetime
from pathlib import Path


def generate_summary(
    metadata: dict,
    indices: dict,
    classification_stats: dict,
    output_dir: str,
) -> dict:
    """
    Compile scene statistics into a JSON summary file.

    Parameters
    ----------
    metadata             : dict from ingest.load_metadata()
    indices              : dict from indices.compute_all_indices()
    classification_stats : dict from classify.classification_stats()
    output_dir           : directory to write summary.json

    Returns
    -------
    dict — the summary data (also written to disk)
    """
    summary = {
        "pipeline_run":       datetime.utcnow().isoformat() + "Z",
        "scene": {
            "acquisition_date":  metadata.get("date", "Unknown"),
            "tile_id":           metadata.get("tile_id", "Unknown"),
            "cloud_cover_pct":   metadata.get("cloud_cover", None),
            "processing_level":  metadata.get("processing_level", "Unknown"),
        },
        "spectral_indices": {},
        "land_cover_percent": classification_stats,
    }

    for name, arr in indices.items():
        valid = arr[~np.isnan(arr)]
        summary["spectral_indices"][name.upper()] = {
            "mean":            round(float(np.mean(valid)), 4) if len(valid) else None,
            "std":             round(float(np.std(valid)),  4) if len(valid) else None,
            "min":             round(float(np.min(valid)),  4) if len(valid) else None,
            "max":             round(float(np.max(valid)),  4) if len(valid) else None,
            "valid_pixels":    int(len(valid)),
            "invalid_pixels":  int(arr.size - len(valid)),
        }

    out_path = Path(output_dir) / "summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"  [✓] Summary JSON → {out_path}")
    return summary


def print_report(summary: dict) -> None:
    """Pretty-print the summary to the console."""
    print("\n" + "=" * 60)
    print("  SATELLITE IMAGE ANALYSIS PIPELINE — RESULTS")
    print("=" * 60)

    scene = summary.get("scene", {})
    print(f"\n  Scene Date    : {scene.get('acquisition_date', 'N/A')}")
    print(f"  Tile ID       : {scene.get('tile_id', 'N/A')}")
    print(f"  Cloud Cover   : {scene.get('cloud_cover_pct', 'N/A')}%")

    print("\n  SPECTRAL INDICES")
    print("  " + "-" * 40)
    for idx_name, stats in summary.get("spectral_indices", {}).items():
        if stats["mean"] is not None:
            print(f"  {idx_name:6s}  mean={stats['mean']:+.3f}  "
                  f"std={stats['std']:.3f}  "
                  f"[{stats['min']:+.3f}, {stats['max']:+.3f}]")

    print("\n  LAND COVER BREAKDOWN")
    print("  " + "-" * 40)
    for class_name, pct in summary.get("land_cover_percent", {}).items():
        bar_len = int(pct / 2)
        bar = "█" * bar_len
        print(f"  {class_name:<25s} {pct:5.1f}%  {bar}")

    print("\n" + "=" * 60 + "\n")
