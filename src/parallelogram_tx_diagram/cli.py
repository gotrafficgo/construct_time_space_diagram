"""Command-line plotting and export."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .core import aggregate, fill_empty, read_csv


def export_csv(grid, path):
    t, x = grid.vertices()
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["space_index", "time_index", "time_center_s", "location_center_m",
                         "speed_kmh", "sample_count", "filled",
                         "t_bottom_left_s", "t_bottom_right_s", "t_top_right_s",
                         "t_top_left_s", "x_bottom_m", "x_top_m"])
        for j, i in np.argwhere(grid.active):
            times = [t[j, i], t[j, i+1], t[j+1, i+1], t[j+1, i]]
            writer.writerow([j, i, np.mean(times), (x[j, i]+x[j+1, i])/2,
                             grid.speed[j, i] if np.isfinite(grid.speed[j, i]) else "",
                             grid.count[j, i], int(grid.filled[j, i]),
                             *times, x[j, i], x[j+1, i]])


def plot(grids, output, vmax):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    fig, axes = plt.subplots(len(grids), 1, figsize=(13, 4*len(grids)),
                             sharex=True, sharey=True, squeeze=False,
                             constrained_layout=True)
    cmap = plt.get_cmap("jet_r").copy()
    cmap.set_bad("#eeeeee")
    norm = Normalize(vmin=0, vmax=vmax)
    for ax, (name, grid) in zip(axes[:, 0], grids.items()):
        t, x = grid.vertices()
        values = np.ma.masked_where(~grid.active | ~np.isfinite(grid.speed), grid.speed)
        mesh = ax.pcolormesh(t/60, x, values, shading="flat", cmap=cmap,
                             norm=norm, rasterized=True)
        ax.set_xlim(grid.bounds[0]/60, grid.bounds[1]/60)
        ax.set_ylim(grid.bounds[2:])
        subtitle = "rectangular cells" if grid.shear == 0 else f"wave speed = {3.6/grid.shear:g} km/h"
        ax.set_title(f"{name.upper()} — {subtitle}", loc="left")
        ax.set_ylabel("Location (m)")
        ax.set_facecolor("#eeeeee")
    axes[-1, 0].set_xlabel("Time (min)")
    fig.colorbar(mesh, ax=list(axes[:, 0]), label="Speed (km/h)", pad=0.02)
    fig.savefig(output / "comparison.png", dpi=180)
    fig.savefig(output / "comparison.svg", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Build speed diagrams without vehicle IDs.")
    parser.add_argument("input", type=Path, help="Four-column CSV: ID, time(s), location(m), speed(km/h)")
    parser.add_argument("--mode", choices=["rectangular", "parallelogram", "both"], default="both")
    parser.add_argument("--dt", type=float, default=30, help="Cell time width in seconds (default: 30)")
    parser.add_argument("--dx", type=float, default=50, help="Cell spatial height in meters (default: 50)")
    parser.add_argument("--wave-speed", type=float, default=-16, help="Wave speed in km/h (default: -16)")
    parser.add_argument("--fill", choices=["none", "neighbors"], default="none")
    parser.add_argument("--bounds", nargs=4, type=float, metavar=("T_MIN", "T_MAX", "X_MIN", "X_MAX"))
    parser.add_argument("--vmax", type=float, help="Colorbar maximum in km/h; default is observed maximum")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    try:
        points = read_csv(args.input)
        modes = ["rectangular", "parallelogram"] if args.mode == "both" else [args.mode]
        grids = {}
        stats = {}
        for mode in modes:
            grid = aggregate(points, args.dt, args.dx,
                             None if mode == "rectangular" else args.wave_speed,
                             args.bounds)
            empty_before = int(np.sum(grid.active & (grid.count == 0)))
            if args.fill == "neighbors":
                grid = fill_empty(grid)
            grids[mode] = grid
            stats[mode] = {"samples": int(grid.count.sum()),
                           "active_cells": int(grid.active.sum()),
                           "empty_before": empty_before,
                           "filled_cells": int(grid.filled.sum()),
                           "empty_after": int(np.sum(grid.active & ~np.isfinite(grid.speed))),
                           "shear_s_per_m": grid.shear}
        vmax = args.vmax if args.vmax is not None else max(float(points[:, 2].max()), 1.0)
        if not np.isfinite(vmax) or vmax <= 0:
            raise ValueError("vmax must be finite and positive")
        args.output.mkdir(parents=True, exist_ok=True)
        for mode, grid in grids.items():
            export_csv(grid, args.output / f"{mode}.csv")
        plot(grids, args.output, vmax)
        metadata = {"input": str(args.input), "input_rows": len(points), "dt_s": args.dt,
                    "dx_m": args.dx, "wave_speed_kmh": args.wave_speed,
                    "fill": args.fill, "bounds": list(next(iter(grids.values())).bounds),
                    "vmax_kmh": vmax, "statistics": stats}
        (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        print(f"Saved diagrams and cell data to {args.output.resolve()}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
