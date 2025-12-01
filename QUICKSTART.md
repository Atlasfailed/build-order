# Quick Start Guide

Get up and running with BAR Position Analysis in 5 minutes!

## Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- Internet connection (for downloading replays)

## Installation

### 1. Install Python Dependencies

```bash
cd bar-position-analysis
pip install -r requirements.txt
```

### 2. Build the Demo Parser

```bash
cd ..
npm install
npm run build
cd bar-position-analysis
```

## Run the Pipeline

### Option 1: Full Pipeline (Recommended)

Run everything from scratch:

```bash
chmod +x run-pipeline.sh
./run-pipeline.sh
```

This will:
1. ⬇️  Download replays from BAR API (~5-30 min)
2. 📊 Parse all replay files (~10-20 min)
3. 🎯 Cluster positions (~1 min)
4. 🏗️  Cluster build orders (~1-5 min)
5. 📈 Analyze success rates (~1 min)
6. 🎨 Generate visualizations (~1 min)

**Total time:** 15-60 minutes depending on network speed

### Option 2: Quick Test with Existing Data

If you already have replays in `test/emre-front1` or `test/test_replays`:

```bash
# Copy existing replays
cp -r ../test/emre-front1/*.sdfz data/replays/
cp -r ../test/test_replays/*.sdfz data/replays/

# Skip download and run from parsing
./run-pipeline.sh --skip-download
```

This runs much faster (~5-10 minutes).

### Option 3: Run Individual Steps

```bash
# Just download
./run-step.sh 1

# Just parse
./run-step.sh 2

# Just visualize (requires previous steps)
./run-step.sh 6
```

## View Results

Once complete, open the dashboard:

```bash
open output/visualizations/index.html
```

Or navigate to `bar-position-analysis/output/visualizations/index.html` in your browser.

## What You'll See

The dashboard includes:

- **📍 Position Map**: Visual map showing where each position spawns
- **📊 Win Rates**: Success rates by position and skill level
- **🏆 Build Archetypes**: Common build patterns and their effectiveness
- **⏱️  Timing Analysis**: What high-skill players do differently

## Configuration

To customize the analysis, edit `config/config.json`:

```json
{
  "filters": {
    "min_skill_threshold": 35,    // Lower to include more players
    "date_from": "2025-07-01"     // Adjust date range
  },
  "analysis": {
    "time_window_seconds": 360    // Analyze first N seconds
  }
}
```

## Troubleshooting

### "No replays found"
- Run `./run-step.sh 1` to download replays
- Or copy existing `.sdfz` files to `data/replays/`

### "Demo parser not found"
```bash
cd ..
npm install
npm run build
cd bar-position-analysis
```

### "Module not found" (Python)
```bash
pip install -r requirements.txt
```

### Permission denied on shell scripts
```bash
chmod +x run-pipeline.sh run-step.sh
```

## Next Steps

- Read [USAGE.md](USAGE.md) for detailed documentation
- Check `output/reports/` for CSV/JSON data exports
- Modify scripts in `src/` to customize analysis

## Example Output

After running the pipeline, you'll have:

```
bar-position-analysis/
├── data/
│   ├── replays/          # 100+ .sdfz files
│   ├── parsed/           # JSON data
│   └── analysis/         # Clustering results
├── output/
│   ├── reports/          # CSV & JSON reports
│   └── visualizations/   # index.html dashboard
```

## Getting Help

- **Documentation**: See [USAGE.md](USAGE.md)
- **Configuration**: Check [README.md](README.md)
- **Issues**: Review error messages in terminal

Happy analyzing! 🎮

