import tempfile
import unittest
from pathlib import Path

import numpy as np

from parallelogram_tx_diagram import aggregate, fill_empty, read_csv


class GridTests(unittest.TestCase):
    def test_rectangle_means_and_upper_boundary(self):
        points = [[0, 0, 10], [5, 5, 30], [10, 10, 60], [20, 20, 80]]
        grid = aggregate(points, 10, 10, None, (0, 20, 0, 20))
        np.testing.assert_array_equal(grid.count, [[2, 0], [0, 2]])
        np.testing.assert_allclose(grid.speed[[0, 1], [0, 1]], [20, 70])
        self.assertEqual(grid.shear, 0)

    def test_wave_geometry_and_point_assignment(self):
        # c=-1 m/s: (t=15,x=5) and (t=5,x=15) lie on one wave.
        grid = aggregate([[15, 5, 20], [5, 15, 40]], 10, 10, -3.6, (0, 30, 0, 20))
        self.assertEqual(grid.count[0, 2], 1)
        self.assertEqual(grid.count[1, 2], 1)
        t, x = grid.vertices()
        np.testing.assert_allclose(np.diff(x, axis=0)/np.diff(t, axis=0), -1)

    def test_against_direct_geometric_membership(self):
        rng = np.random.default_rng(123)
        points = rng.uniform([0, 0, 0], [100, 80, 100], (500, 3))
        for c in [-16, 16, None]:
            grid = aggregate(points, 17, 13, c, (0, 100, 0, 80))
            self.assertEqual(grid.count.sum(), len(points))
            for j, i in np.argwhere(grid.active):
                lo = grid.tau_edges[i] + grid.shear*points[:, 1]
                hi = grid.tau_edges[i+1] + grid.shear*points[:, 1]
                mask = ((points[:, 0] >= lo) & (points[:, 0] < hi)
                        & (points[:, 1] >= grid.x_edges[j])
                        & (points[:, 1] < grid.x_edges[j+1]))
                self.assertEqual(grid.count[j, i], mask.sum())
                if mask.any():
                    self.assertAlmostEqual(grid.speed[j, i], points[mask, 2].mean())

    def test_fill_preserves_observations_and_counts(self):
        grid = aggregate([[1, 1, 20], [29, 29, 60]], 10, 10, None, (0, 30, 0, 30))
        result = fill_empty(grid)
        self.assertTrue(np.isfinite(result.speed).all())
        self.assertEqual(result.speed[1, 1], 40)
        np.testing.assert_array_equal(grid.count, result.count)
        self.assertEqual(result.speed[0, 0], 20)
        self.assertEqual(result.speed[2, 2], 60)
        self.assertEqual(result.filled.sum(), 7)
        self.assertTrue(np.isnan(grid.speed[1, 1]))

    def test_vehicle_id_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"input.csv"
            path.write_text("VehID,Time,Position,Speed\nanything,0,0,20\n,10,10,30\n")
            np.testing.assert_array_equal(read_csv(path), [[0, 0, 20], [10, 10, 30]])

    def test_reject_invalid_parameters(self):
        points = [[0, 0, 20], [10, 10, 30]]
        for kwargs in [{"wave_speed_kmh": 0}, {"dt": 0}, {"dx": -1}, {"dt": float("nan")}]:
            with self.assertRaises(ValueError):
                aggregate(points, **kwargs)


if __name__ == "__main__":
    unittest.main()
