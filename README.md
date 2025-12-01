# BAR Position Analysis Pipeline

Comprehensive build-order analysis system for Beyond All Reason's Supreme Isthmus map.

## Overview

This pipeline downloads replays, clusters spawn positions, analyzes build orders for high-skill players, and generates interactive visualizations showing what strategies work best at each position.

## Project Structure

```
bar-position-analysis/
├── config/
│   └── config.json              # Configuration
├── data/
│   ├── replays/                 # Downloaded .sdfz files
│   ├── parsed/                  # Parsed JSON data from demos
│   └── analysis/                # Analysis results
├── src/
│   ├── 1-download-replays.py    # Download replays from BAR API
│   ├── 2-parse-demos.ts         # Parse .sdfz files, extract positions & builds
│   ├── 3-cluster-positions.py   # Cluster spawn positions into roles
│   ├── 4-cluster-builds.py      # Cluster build orders per position
│   ├── 5-analyze-success.py     # Analyze build success rates
│   └── 6-visualize.py           # Generate interactive visualizations
├── output/
│   ├── reports/                 # JSON/CSV reports
│   └── visualizations/          # HTML dashboards
└── run-pipeline.sh              # Run full pipeline
```

## Setup

### Python Dependencies

```bash
pip install aiohttp aiofiles scikit-learn pandas numpy plotly scipy
```

### TypeScript Setup

This project uses the existing demo parser from the parent directory. Make sure you've run:

```bash
cd ..
npm install
npm run build
```

## Usage

### Run Full Pipeline

```bash
./run-pipeline.sh
```

### Run Individual Steps

```bash
# 1. Download replays
python src/1-download-replays.py

# 2. Parse demos (requires compiled TypeScript)
npm run parse-demos

# 3. Cluster positions
python src/3-cluster-positions.py

# 4. Cluster build orders
python src/4-cluster-builds.py

# 5. Analyze success rates
python src/5-analyze-success.py

# 6. Generate visualizations
python src/6-visualize.py
```

## Configuration

Edit `config/config.json` to customize:
- API filters (date range, skill threshold)
- Clustering parameters
- Output formats

## Output

- **Reports**: CSV and JSON files in `output/reports/`
- **Visualizations**: Interactive HTML dashboards in `output/visualizations/`
- **Raw Data**: Parsed game data in `data/parsed/`

## Key Features

1. **Automated Replay Download**: Fetches filtered replays from BAR API
2. **Position Identification**: Clusters all 8 positions per team
3. **Build Order Clustering**: Finds common build patterns
4. **Success Rate Analysis**: Identifies what works for high-skill players
5. **Interactive Visualizations**: Better insights through visual exploration
6. **Modular Pipeline**: Run individual components independently

