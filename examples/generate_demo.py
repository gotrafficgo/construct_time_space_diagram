"""Generate reproducible synthetic point observations, not real trajectories."""

import csv
from pathlib import Path

import numpy as np


def main():
    rng = np.random.default_rng(42)
    n = 20_000
    time = rng.uniform(0, 900, n)
    location = rng.uniform(0, 1000, n)
    # Congested bands travel upstream at -16 km/h: t - x/c = constant.
    tau = time + location/(16/3.6)
    distance_to_wave = (tau+90) % 180-90
    speed = np.clip(85-65*np.exp(-0.5*(distance_to_wave/20)**2)
                    + rng.normal(0, 3, n), 0, 100)
    output = Path("outputs/demo/input.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["VehID", "Time", "Position", "Speed"])
        for t, x, v in zip(time, location, speed):
            writer.writerow(["unused", f"{t:.6f}", f"{x:.6f}", f"{v:.6f}"])
    print(output)


if __name__ == "__main__":
    main()
