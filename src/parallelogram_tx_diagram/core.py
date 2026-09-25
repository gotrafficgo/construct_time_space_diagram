"""Pure aggregation and optional eight-neighbor filling."""

import csv
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np


def read_csv(path):
    """Read four-column CSV (ID ignored), returning columns time, position, speed.

    A header is optional. All rows must have exactly four columns. Nonfinite
    measurements and negative speeds are rejected rather than silently dropped.
    """
    points = []
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        for line, row in enumerate(csv.reader(stream), 1):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) != 4:
                raise ValueError(f"Line {line}: expected four columns, got {len(row)}")
            if not points and row[1].strip().lower() in {"time", "timestamp"}:
                continue
            try:
                values = [float(value) for value in row[1:]]
            except ValueError as exc:
                raise ValueError(f"Line {line}: invalid time, location or speed") from exc
            if not np.isfinite(values).all() or values[2] < 0:
                raise ValueError(f"Line {line}: measurements must be finite; speed >= 0")
            points.append(values)
    if not points:
        raise ValueError("CSV contains no observations")
    return np.asarray(points, dtype=float)


@dataclass
class SpeedGrid:
    tau_edges: np.ndarray
    x_edges: np.ndarray
    speed: np.ndarray
    count: np.ndarray
    active: np.ndarray
    filled: np.ndarray
    shear: float
    t_origin: float
    x_origin: float
    bounds: tuple

    def vertices(self):
        """Return time and location coordinates of all cell corners."""
        tau, x = np.meshgrid(self.tau_edges, self.x_edges)
        return self.t_origin + tau + self.shear * (x - self.x_origin), x


def aggregate(points, dt=30.0, dx=50.0, wave_speed_kmh=-16.0,
              bounds=None, max_cells=2_000_000):
    """Aggregate sample speeds in km/h, using time in s and location in m.

    wave_speed_kmh=None selects rectangles (zero shear). Otherwise shear=1/c,
    with c in m/s. Bounds are (t_min, t_max, x_min, x_max), inclusive for input.
    The lower bounds anchor the lattice. Interior boundaries belong to the
    following cell; observations on the outer upper edges enter the last cell.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points):
        raise ValueError("points must be a nonempty (N, 3) array: time, location, speed")
    if not np.isfinite(points).all() or np.any(points[:, 2] < 0):
        raise ValueError("Measurements must be finite and speeds nonnegative")
    if not np.isfinite([dt, dx]).all() or dt <= 0 or dx <= 0:
        raise ValueError("dt and dx must be finite and positive")
    if wave_speed_kmh is None:
        shear = 0.0
    else:
        if not np.isfinite(wave_speed_kmh) or wave_speed_kmh == 0:
            raise ValueError("Wave speed must be finite and nonzero; use None for rectangles")
        shear = 3.6 / wave_speed_kmh
    if bounds is None:
        bounds = (points[:, 0].min(), points[:, 0].max(),
                  points[:, 1].min(), points[:, 1].max())
    t0, t1, x0, x1 = map(float, bounds)
    if not np.isfinite([t0, t1, x0, x1]).all() or t1 <= t0 or x1 <= x0:
        raise ValueError("Bounds must be finite and have positive time and space spans")
    inside = ((points[:, 0] >= t0) & (points[:, 0] <= t1)
              & (points[:, 1] >= x0) & (points[:, 1] <= x1))
    selected = points[inside]
    if not len(selected):
        raise ValueError("No observations inside the requested bounds")
    corners = np.array([0, t1-t0, -shear*(x1-x0), t1-t0-shear*(x1-x0)])
    first = int(np.floor(corners.min() / dt))
    last = int(np.ceil(corners.max() / dt))
    nx = int(np.ceil((x1-x0) / dx))
    nt = last - first
    if nt * nx > max_cells:
        raise ValueError("Too many cells; increase dt/dx or narrow the bounds")
    tau_edges = np.arange(first, last+1, dtype=float) * dt
    x_edges = x0 + np.arange(nx+1, dtype=float) * dx
    # Clip the final spatial band to the observation window.
    x_edges[-1] = x1
    tau = selected[:, 0] - t0 - shear*(selected[:, 1]-x0)
    i = np.clip(np.floor(tau/dt).astype(int)-first, 0, nt-1)
    j = np.clip(np.floor((selected[:, 1]-x0)/dx).astype(int), 0, nx-1)
    flat = j*nt+i
    count = np.bincount(flat, minlength=nx*nt).reshape(nx, nt)
    total = np.bincount(flat, weights=selected[:, 2], minlength=nx*nt).reshape(nx, nt)
    speed = np.full((nx, nt), np.nan)
    np.divide(total, count, out=speed, where=count > 0)
    left = t0 + tau_edges[:-1][None, :] + shear*(x_edges[:-1, None]-x0)
    right = t0 + tau_edges[1:][None, :] + shear*(x_edges[1:, None]-x0)
    offset = shear*np.diff(x_edges)[:, None]
    low = np.minimum(left, left+offset)
    high = np.maximum(right, right-offset)
    active = ((high > t0) & (low < t1)) | (count > 0)
    return SpeedGrid(tau_edges, x_edges, speed, count, active,
                     np.zeros_like(active), shear, t0, x0, (t0, t1, x0, x1))


def _neighbor_sum(values):
    padded = np.pad(values, 1, mode="constant")
    result = np.zeros_like(values)
    rows, cols = values.shape
    for dj in range(3):
        for di in range(3):
            if dj != 1 or di != 1:
                result += padded[dj:dj+rows, di:di+cols]
    return result


def fill_empty(grid):
    """Fill by eight-neighbor means, prioritizing fewest missing neighbors.

    Ties are filled simultaneously, then priorities are recalculated. Outside
    cells do not count as neighbors. Cells unreachable from observations stay
    NaN. Returns a new grid; observed values and counts are preserved.
    """
    speed = grid.speed.copy()
    filled = grid.filled.copy()
    neighbor_count = _neighbor_sum(grid.active.astype(int))
    while True:
        known = grid.active & np.isfinite(speed)
        missing = grid.active & ~known
        if not missing.any():
            break
        known_count = _neighbor_sum(known.astype(int))
        eligible = missing & (known_count > 0)
        if not eligible.any():
            break
        empty_count = neighbor_count-known_count
        chosen = eligible & (empty_count == empty_count[eligible].min())
        totals = _neighbor_sum(np.where(known, speed, 0.0))
        speed[chosen] = totals[chosen]/known_count[chosen]
        filled[chosen] = True
    return replace(grid, speed=speed, filled=filled)
