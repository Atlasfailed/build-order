# BAR Position Analysis - Usage Guide

## Quick Start

### 1. Install Dependencies

**Python dependencies:**
```bash
pip install -r requirements.txt
```

**TypeScript setup:**
```bash
cd ..
npm install
npm run build
cd bar-position-analysis
```

### 2. Run the Pipeline

**Full pipeline:**
```bash
chmod +x run-pipeline.sh
./run-pipeline.sh
```

**Run specific step:**
```bash
chmod +x run-step.sh
./run-step.sh 3  # Run step 3 (cluster positions)
```

## Pipeline Steps

### Step 1: Download Replays
```bash
python3 src/1-download-replays.py
```

Downloads Supreme Isthmus v2.1 replays from the BAR API with filtering:
- Team games only (no bots)
- Games that ended normally
- At least 4 players with skill > 35
- Minimum game duration: 5 minutes

**Output:** `data/replays/*.sdfz`

**Options:**
- Edit `config/config.json` to change filters (date range, skill threshold, etc.)

### Step 2: Parse Demos
```bash
cd ..
npx ts-node bar-position-analysis/src/2-parse-demos.ts
```

Parses replay files and extracts:
- Player positions (spawn coordinates)
- Build orders (first 6 minutes)
- Game outcomes
- Player stats (skill, rank, faction)

**Output:**
- `data/parsed/positions.jsonl` - All player positions
- `data/parsed/builds.jsonl` - All build orders
- `data/parsed/game-*.json` - Individual game files
- `data/parsed/parse-summary.json` - Summary statistics

### Step 3: Cluster Positions
```bash
python3 src/3-cluster-positions.py
```

Clusters spawn positions into roles using DBSCAN:
- Handles map symmetry (normalizes coordinates)
- Identifies 8 positions per team
- Assigns labels (front-1, front-2, air, eco, etc.)

**Output:**
- `data/analysis/position-clusters.json` - Cluster information
- `data/analysis/position-assignments.jsonl` - Player→position mapping

**Tuning:**
- Edit `config.json` → `analysis.position_clustering.eps` to adjust clustering sensitivity
- Lower eps = more clusters (stricter matching)
- Higher eps = fewer clusters (looser matching)

### Step 4: Cluster Build Orders
```bash
python3 src/4-cluster-builds.py
```

Finds common build order patterns for each position:
- Groups similar build sequences
- Identifies representative "archetypes"
- Calculates win rates and frequency

**Output:**
- `data/analysis/build-clusters.json` - Build archetypes per position

**Tuning:**
- `analysis.build_clustering.max_clusters` - Maximum archetypes per position
- `analysis.build_clustering.min_cluster_size` - Minimum games to form archetype

### Step 5: Analyze Success
```bash
python3 src/5-analyze-success.py
```

Statistical analysis of build order performance:
- Win rates by position and skill level
- Archetype success rates
- High-skill vs mid-skill comparisons
- Timing differences

**Output:**
- `output/reports/position-summary.csv` - Position overview
- `output/reports/build-success-rates.csv` - Archetype win rates
- `output/reports/high-skill-patterns.json` - High-skill insights
- `output/reports/complete-analysis.json` - Full analysis results

### Step 6: Generate Visualizations
```bash
python3 src/6-visualize.py
```

Creates interactive HTML dashboard with:
- Position cluster map
- Win rate comparisons
- Build archetype analysis
- Skill level comparisons
- Timing difference charts

**Output:**
- `output/visualizations/index.html` - Interactive dashboard

**View:**
```bash
open output/visualizations/index.html
# or
firefox output/visualizations/index.html
```

## Pipeline Options

### Skip Steps

Skip downloading (use existing replays):
```bash
./run-pipeline.sh --skip-download
```

Skip parsing (use existing parsed data):
```bash
./run-pipeline.sh --skip-parse
```

Start from specific step:
```bash
./run-pipeline.sh --from-step 3  # Start from clustering
```

### Incremental Updates

To update with new replays without re-processing everything:

```bash
# 1. Download new replays (appends to existing)
python3 src/1-download-replays.py

# 2. Parse only new replays
npx ts-node src/2-parse-demos.ts

# 3. Re-run analysis (fast)
./run-pipeline.sh --skip-download --skip-parse
```

## Configuration

Edit `config/config.json`:

### API Filters
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

### Analysis Parameters
```json
{
  "analysis": {
    "time_window_seconds": 360,     // Analyze first 6 minutes
    "high_skill_threshold": 40,     // Define "high skill"
    "mid_skill_threshold": 30       // Define "mid skill"
  }
}
```

### Position Clustering
```json
{
  "position_clustering": {
    "eps": 800,                     // Distance tolerance
    "min_samples": 3                // Minimum players per cluster
  }
}
```

## Troubleshooting

### No replays downloaded
- Check internet connection
- Verify API is accessible: `curl https://api.bar-rts.com/replays?page=1`
- Adjust filters in `config.json` (may be too restrictive)

### Parsing errors
- Ensure demo parser is built: `cd .. && npm run build`
- Check replay file integrity
- Try parsing individual files with `check-start-positions.ts`

### Too many/few position clusters
- Adjust `position_clustering.eps` in config
- Check `data/analysis/position-clusters.json` for cluster info
- View position map in dashboard to visualize

### Build clustering not finding patterns
- Reduce `min_cluster_size` in config
- Ensure enough data (need >50 games per position ideally)
- Check `data/parsed/builds.jsonl` to verify build orders were extracted

## Output Files Reference

### Data Files
| File | Description |
|------|-------------|
| `data/replays/*.sdfz` | Downloaded replay files |
| `data/parsed/positions.jsonl` | All player spawn positions |
| `data/parsed/builds.jsonl` | All build orders |
| `data/parsed/game-*.json` | Individual game data |
| `data/analysis/position-clusters.json` | Position clustering results |
| `data/analysis/position-assignments.jsonl` | Player position assignments |
| `data/analysis/build-clusters.json` | Build order archetypes |

### Reports
| File | Description |
|------|-------------|
| `output/reports/position-summary.csv` | Win rates by position |
| `output/reports/build-success-rates.csv` | Archetype performance |
| `output/reports/high-skill-patterns.json` | High-skill player insights |
| `output/reports/complete-analysis.json` | Full analysis results |

### Visualizations
| File | Description |
|------|-------------|
| `output/visualizations/index.html` | Interactive dashboard |

## Advanced Usage

### Custom Analysis

You can write custom scripts using the generated data:

```python
import json

# Load position assignments
with open('data/analysis/position-assignments.jsonl', 'r') as f:
    positions = [json.loads(line) for line in f]

# Filter for specific position
front1_players = [p for p in positions if p['position_name'] == 'front-1']

# Analyze...
```

### Export Data

All data is in JSON/JSONL format for easy integration with other tools:

```bash
# Convert to CSV
python3 -c "
import json
import pandas as pd

positions = []
with open('data/analysis/position-assignments.jsonl', 'r') as f:
    positions = [json.loads(line) for line in f]

df = pd.DataFrame(positions)
df.to_csv('positions.csv', index=False)
"
```

## Performance

Expected runtime on typical dataset (1000 games):

| Step | Time | Bottleneck |
|------|------|------------|
| 1. Download | 5-30 min | Network speed |
| 2. Parse | 10-20 min | Disk I/O |
| 3. Cluster Positions | < 1 min | CPU |
| 4. Cluster Builds | 1-5 min | CPU |
| 5. Analyze | < 1 min | CPU |
| 6. Visualize | < 1 min | CPU |

**Total:** ~15-60 minutes depending on network and dataset size

## Getting Help

If you encounter issues:

1. Check this guide
2. Review error messages in terminal
3. Verify all dependencies are installed
4. Try running individual steps to isolate the problem
5. Check the generated log files in output directories

