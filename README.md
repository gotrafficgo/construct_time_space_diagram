# Constructing time-space diagrams by considering wave speed

**[Background]** Spatiotemporal speed contour diagrams describe how traffic speed changes over time and space. They are commonly constructed by averaging speed observations within rectangular cells.

**[Gap]** Rectangular cells do not follow the propagation direction of traffic waves, which can blur stop-and-go patterns and affect travel-time estimates.

**[Contribution]** This project implements a simple method that aggregates speed observations within non-rectangular parallelogram cells aligned with backward-moving traffic waves. A Python tool supports both rectangular and parallelogram cells for direct comparison.

**[Impact]** The method provides a practical way to construct speed contour diagrams from trajectory or probe data using only time, location, and speed, without requiring vehicle identities. The paper reports improvements particularly under congested conditions and with relatively large cells.

**[Paper]** [Constructing spatiotemporal speed contour diagrams: using rectangular or non-rectangular parallelogram cells?](https://doi.org/10.1080/21680566.2017.1320774)

## Comparison with rectangular cells

<p align="center">
  <img src="results/trj11_lane1/F001/comparison.png"
       alt="Rectangular and parallelogram speed contour diagrams for ZenTrafficData TRJ_11 Lane 1"
       width="600">
</p>

**Top:** rectangular cells. **Bottom:** parallelogram cells. The example uses ZenTrafficData `TRJ_11/Lane1/F001.csv`, with cells of **30 s × 50 m** and a wave speed of **−16 km/h**. Both panels use reversed jet (`jet_r`): red indicates low speed and blue indicates high speed. Gray regions have no observations. The wave speed is configurable and has not been calibrated to this dataset.

## Code

The code is written in **Python** and requires Python 3.9 or later. Clone the repository, install the package, and unzip the data before running:

```bash
git clone https://github.com/gotrafficgo/construct_time_space_diagram.git
cd construct_time_space_diagram
python -m pip install -e .
python -m zipfile -e data/ZenTrafficData/TRJ_11.zip data/ZenTrafficData
tx-diagram data/ZenTrafficData/TRJ_11/Lane1/F001.csv --output results/trj11_lane1/F001
```

To use your own data, replace the CSV path. By default, the tool generates both diagrams with a **30 s** cell width, **50 m** cell height, **−16 km/h** wave speed, and no empty-cell filling. Use `--dt`, `--dx`, and `--wave-speed` to change these settings; `--mode rectangular` or `--mode parallelogram` selects one method. Run `tx-diagram --help` for all options.

Results include PNG/SVG figures, cell statistics in CSV format, and a JSON parameter record. Published examples are saved in [results/](results/). Dataset ZIP archives are kept in [data/](data/); extracted files can be deleted after generating the results.

## Input Trajectory Data Format

The input file should be in **CSV format**, with each row corresponding to a trajectory data point. It contains **4 columns** in the following order:

| Column | Name | Unit | Description |
| --- | --- | --- | --- |
| 1 | Vehicle ID | – | Vehicle identifier; **not used by this method**. |
| 2 | Time | s | Timestamp in seconds. |
| 3 | Location | m | Position along the road in meters. |
| 4 | Speed | km/h | Vehicle speed. |

Columns are read by position. A header is optional; if included, its second column should be `Time` or `Timestamp`. The location column may be named `Location` or `Position`. Each speed observation has equal weight in its cell.

## Citation

If you find this work useful, please consider citing our paper:

> **Constructing spatiotemporal speed contour diagrams: using rectangular or non-rectangular parallelogram cells?**  
> Zhengbing He, Ying Lv, Lili Lu, Wei Guan  
> *Transportmetrica B: Transport Dynamics*, 7(1), 44–60, 2019.  
> [doi:10.1080/21680566.2017.1320774](https://doi.org/10.1080/21680566.2017.1320774)

```bibtex
@article{he2019constructing,
  title   = {Constructing spatiotemporal speed contour diagrams: using rectangular or non-rectangular parallelogram cells?},
  author  = {He, Zhengbing and Lv, Ying and Lu, Lili and Guan, Wei},
  journal = {Transportmetrica B: Transport Dynamics},
  year    = {2019},
  volume  = {7},
  number  = {1},
  pages   = {44--60},
  doi     = {10.1080/21680566.2017.1320774}
}
```
