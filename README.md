# BAR Position Analysis

Analyze spawn positions and build orders from Beyond All Reason replays of Supreme Isthmus map.

## Workflow

1. **Configure parameters** - Edit `config/config.json` to define replay filters
2. **Download replay JSONs** - Fetch replay metadata from BAR API
3. **Download replay SDFZ files** - Download actual replay files
4. **Parse replays** - Extract positions and build orders from SDFZ files
5. **Generate position CSVs** - Export build orders organized by spawn position
6. **Generate HTML** - Create interactive visualization at `pages/index.html`

## Quick Start

### Run All Steps

```bash
./run.sh
```

This runs the complete workflow from download to CSV export.

### Or Run Steps Individually

#### 1. Configure Parameters

Edit `config/config.json`:

```json
{
  "filters": {
    "map_name": "Supreme Isthmus v2.1",
    "min_skill_threshold": 35,
    "date_from": "2025-07-01",
    "date_to": "2025-12-31"
  }
}
```

#### 2. Download Replay JSONs & SDFZ Files

```bash
npm run download
```

This downloads replay metadata and SDFZ files to `data/replays/`.

#### 3. Parse Replays

```bash
npm run parse
```

Extracts spawn positions and build orders from SDFZ files. Creates:
- `data/parsed/positions.jsonl` - Player spawn positions
- `data/parsed/builds.jsonl` - Build orders

#### 4. Generate Position CSVs

```bash
npm run export-csv
```

Creates CSV files in `output/position_csvs/`, one per spawn position (front-1, front-2, air, eco, etc.).

#### 5. View Results

Open `pages/index.html` in your browser to view the interactive visualization.

## Setup

### Python Dependencies

```bash
pip install -r requirements.txt
```

### TypeScript Setup

```bash
cd ..
npm install
npm run build
cd bar-position-analysis
```

## Output

- **Position CSVs**: `output/position_csvs/position_*.csv`
- **Interactive HTML**: `pages/index.html`
- **Parsed Data**: `data/parsed/*.jsonl`

## Project Structure

```
bar-position-analysis/
├── config/
│   └── config.json              # Configuration
├── data/
│   ├── replays/                 # Downloaded .sdfz files
│   └── parsed/                  # Parsed JSON data
├── src/
│   ├── 1-download-replays.py    # Download replays
│   ├── 2-parse-demos.ts         # Parse .sdfz files
│   └── 7-assign-positions-and-export.py  # Generate CSVs
├── output/
│   └── position_csvs/           # CSV files per position
├── pages/
│   └── index.html               # Interactive visualization
└── archive/                     # Old documentation
```

## Configuration

All settings in `config/config.json`:

### API Filters
- `map_name`: Map to analyze (default: "Supreme Isthmus v2.1")
- `min_skill_threshold`: Minimum player skill (default: 35)
- `date_from` / `date_to`: Date range for replays

### Analysis Parameters
- `time_window_seconds`: How much of each game to analyze (default: 360 = 6 minutes)
- `high_skill_threshold`: Define "high skill" players (default: 40)

### Paths
- `replays`: Where to download SDFZ files
- `parsed`: Where to store parsed data
- Output directories for CSVs and visualizations

## The 8 Positions

The map has 8 mirrored spawn positions:

1. **front-1** - Front line position 1
2. **front-2** - Front line position 2
3. **geo** - Geothermal position
4. **geo-sea** - Geothermal near sea
5. **air** - Air position
6. **eco** - Economy position
7. **pond** - Pond position
8. **long-sea** - Long sea position

Each CSV contains build orders from players who spawned at that position.

## Troubleshooting

### No replays downloaded
- Check internet connection
- Verify filters in `config.json` aren't too restrictive
- Check BAR API status

### Parsing errors
- Ensure demo parser is built: `cd .. && npm run build`
- Check replay files exist in `data/replays/`

### Position assignment errors
- Need manual position labels in root directory (legacy system)
- Or use clustering scripts in archive/ for automated position detection

## Archive

Old documentation and experimental scripts are in `archive/`:
- Automated clustering pipeline (steps 3-6)
- Extended usage guides
- Implementation details

