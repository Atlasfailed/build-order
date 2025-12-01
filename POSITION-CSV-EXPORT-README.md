# Position Assignment & CSV Export

This document describes the position assignment system and CSV export functionality.

## Overview

The system assigns players to one of 8 map positions based on their spawn coordinates, then generates CSV files containing build orders for each position.

## The 8 Positions

The map has **8 mirrored positions** across the top-left to bottom-right diagonal:

1. **front-1** - Front line position 1
2. **front-2** - Front line position 2
3. **geo** - Geothermal position
4. **geo-sea** - Geothermal near sea
5. **air** - Air position
6. **eco** - Economy position
7. **pond** - Pond position
8. **long-sea** - Long sea position

Each position exists in two mirrored locations (one for Team 0, one for Team 1).

## How It Works

### 1. Manual Position Labels

The `POSITION-LABELING-LINKS-WITH-PLAYERS.txt` file contains manually labeled positions for a subset of games. This provides ground truth data for calculating position centroids.

### 2. Centroid Calculation

For each position, the script calculates:
- **Team 0 centroid**: Average spawn coordinates for Team 0 players
- **Team 1 centroid**: Average spawn coordinates for Team 1 players

This accounts for the mirrored nature of positions across the diagonal.

### 3. Position Assignment

For each player in every game:
1. Get player's spawn coordinates (x, z)
2. Compare to centroids for their team
3. Assign to the closest position
4. Calculate distance from centroid

### 4. CSV Export

One CSV file per position with format:

**Columns**: Each column represents one player-game
**Rows**:
- Metadata rows:
  - Player Name
  - Game ID
  - Result (Win/Loss)
  - Player Skill
  - Avg Game Skill
  - Position
  - Distance from Centroid
  - `---` (separator)
- Build order rows:
  - Build 1, Build 2, ..., Build N
  - Format: `Unit Name (time in seconds)`

## Script Usage

```bash
cd bar-position-analysis
python3 src/7-assign-positions-and-export.py
```

## Output

The script generates:
- 8 CSV files in `output/position_csvs/`
- Each file named `position_<name>.csv`
- Files range from 1.8MB to 5.9MB
- Approximately 250-300 games per position

### Example Output Statistics

From a run with 137 games:
- Total players assigned: 2,168
- Players per position: ~270 average
- Build orders captured: First 6 minutes (360 seconds)

## Data Quality

### Position Distribution
Each position has roughly equal distribution (~270 players), validating the assignment algorithm.

### Distance Metrics
The "Distance from Centroid" field indicates how closely a player's spawn matched the expected position:
- Lower distance = better match
- Can be used to filter outliers or wrong positions

### Wrong Positions
Players manually labeled as "wrong" position are excluded from centroid calculations but are still assigned to their nearest position.

## Use Cases

### Build Order Analysis
- Compare build orders across different positions
- Analyze which builds correlate with wins
- Study position-specific strategies

### Player Performance
- Track player performance by position
- Analyze skill levels by position
- Compare player build orders across multiple games

### Meta Analysis
- Evolution of build orders over time
- Position popularity and success rates
- Skill-based build order patterns

## Technical Details

### Coordinate System
- Map size: 12,288 x 12,288
- Team 0: Bottom-right area (high x, low z)
- Team 1: Top-left area (low x, high z)

### Mirroring
Positions are mirrored across the diagonal line where x = z. This means:
- Each position has two centroids (one per team)
- Assignment considers team membership
- Distances are calculated within team

### Build Order Capture
- Time window: 0-360 seconds (6 minutes)
- Source: Parsed from replay files
- Includes: Unit name, display name, builder type, timestamp

## Dependencies

- Python 3.x
- JSON (standard library)
- CSV (standard library)
- Math (standard library)
- Pathlib (standard library)

## File Paths

```
bar-position-analysis/
├── POSITION-LABELING-LINKS-WITH-PLAYERS.txt (input: manual labels)
├── data/
│   ├── parsed/
│   │   ├── game-*.json (input: parsed game data)
│   │   └── builds.jsonl (input: build orders)
│   └── highskill_sdfz/ (input: replay files)
└── output/
    └── position_csvs/ (output: CSV files)
        ├── position_front-1.csv
        ├── position_front-2.csv
        ├── position_geo.csv
        ├── position_geo-sea.csv
        ├── position_air.csv
        ├── position_eco.csv
        ├── position_pond.csv
        └── position_long-sea.csv
```

## Next Steps

Potential enhancements:
1. Add visualization of position centroids on map
2. Export position assignment data separately for further analysis
3. Add filtering by skill level or date range
4. Generate summary statistics per position
5. Create comparison views between positions
