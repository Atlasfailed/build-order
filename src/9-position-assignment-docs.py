#!/usr/bin/env python3
"""
Documentation: How Position Assignment Works

This script explains the complete pipeline from raw coordinates to named positions
and demonstrates the position clustering algorithm.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import math

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent

print("=" * 80)
print("📍 BAR Position Analysis - Position Assignment Documentation")
print("=" * 80)

print("""
OVERVIEW
========

The position assignment system identifies where players spawn on the map and 
classifies them into strategic positions (front-1, front-2, eco, air, etc.).

COORDINATE SYSTEM
=================

Supreme Isthmus v2.1 Map:
- Map size: 12288 x 12288 units
- Origin (0,0) is at top-left corner
- X increases going right
- Z increases going down

Team Spawns:
- Team 0: Bottom-right corner (high X, high Z)
- Team 1: Top-left corner (low X, low Z)
- Teams are mirrored diagonally across the map

POSITION TYPES
==============

1. front-1     : First frontline position (closest to enemy)
2. front-2     : Second frontline position
3. eco         : Economy/expansion position (side/back)
4. air         : Air player position
5. geo         : Geothermal position (middle of map)
6. geo-sea     : Geothermal accessible from sea
7. pond        : Small water body position
8. long-sea    : Extended sea lane position

POSITION ASSIGNMENT ALGORITHM
==============================

Step 1: Manual Labeling
-----------------------
Expert players manually label representative games:
- File: archive/POSITION-LABELS-MANUAL.txt
- Format: game_id,player_name,position_name
- Example: "2025-11-28_23-25-49-055,Cloud_,front-1"

Step 2: Calculate Centroids
---------------------------
For each position, calculate the average spawn coordinates from labeled examples.
Since teams are mirrored, we calculate TWO centroids per position:
""")

# Load manual labels
def load_manual_labels():
    """Load manually labeled positions."""
    labels_file = BASE_DIR / "archive" / "POSITION-LABELS-MANUAL.txt"
    
    if not labels_file.exists():
        print(f"⚠️  Manual labels file not found: {labels_file}")
        return {}
    
    labels = {}
    with open(labels_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        game_id, player_name, position = parts[0], parts[1], parts[2]
                        labels[(game_id, player_name)] = position
                except Exception as e:
                    continue
    
    return labels

# Calculate distance
def euclidean_distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

# Mirror position
def mirror_position(x: float, z: float, map_size: int = 12288) -> Tuple[float, float]:
    """Mirror a position across the diagonal."""
    return map_size - z, map_size - x

# Load example data
labels = load_manual_labels()
if labels:
    print(f"✓ Loaded {len(labels)} manually labeled positions\n")
    
    # Show examples
    print("Example labeled positions:")
    for i, ((game_id, player_name), position) in enumerate(list(labels.items())[:5]):
        print(f"  • {player_name}: {position}")
    print()

print("""
Example Centroid Calculation:
------------------------------

If we have 3 "front-1" positions for Team 0:
  Player A: (8500, 2200)
  Player B: (8400, 2300)  
  Player C: (8600, 2100)

Team 0 Centroid = ((8500+8400+8600)/3, (2200+2300+2100)/3) = (8500, 2200)

Team 1 Centroid (mirrored) = mirror(8500, 2200) = (12288-2200, 12288-8500) 
                            = (10088, 3788)

Step 3: Assign Positions
------------------------
For each new player:
1. Get their spawn coordinates (x, z)
2. Determine their ally team (0 or 1)
3. Calculate distance to all centroids for their team
4. Assign to the nearest centroid's position

Example:
  New player spawns at (8520, 2180) on Team 0
  
  Distances to Team 0 centroids:
    front-1: distance((8520,2180), (8500,2200)) = 28.3 units
    front-2: distance((8520,2180), (7800,2500)) = 756.2 units
    eco:     distance((8520,2180), (9200,3100)) = 1142.8 units
    ...
  
  → Assigned to "front-1" (closest match)

FACTION MAPPING
===============

The game supports 3 factions with different naming conventions:

Full Names:
- Armada (default)
- Cortex 
- Legion

Short codes (3 letters):
- arm → Armada
- cor → Cortex  
- leg → Legion

The parser extracts the full faction name from replay metadata.

WIN RATE CALCULATION
====================

Issue: winningAllyTeamIds is empty in parsed data
------------------------------------------------------

The demo parser attempts to read game winners from:
  demo.info.meta.winningAllyTeamIds

However, this field is often empty in .sdfz replay files, resulting in:
  wonGame: false for ALL players

Potential Solutions:
1. Check if replay files contain winner data at all
2. Use alternative data source (BAR API, replay JSON files)
3. Analyze game duration and unit counts as proxy for winners
4. Download games with verified outcomes only

Current Status:
  All players show wonGame: false (0% win rate)
  This needs to be fixed by finding a reliable winner data source

FILE STRUCTURE
==============

Input Files:
  data/replays/*.sdfz                      - Raw replay files
  archive/POSITION-LABELS-MANUAL.txt       - Hand-labeled positions

Intermediate Files:
  data/parsed/positions.jsonl              - All player spawn positions
  data/parsed/builds.jsonl                 - All build orders (3.88 GB)
  data/parsed/game-*.json                  - Individual game metadata
  data/analysis/position-assignments.jsonl - Position assignments

Output Files:
  output/optimized/index.parquet           - Player/game metadata (0.9 MB)
  output/optimized/builds.parquet          - Build steps (79.3 MB)
  output/optimized/lookup_*.parquet        - ID lookup tables (241 KB)
  output/position_csvs/position_*.csv      - Build data by position

OPTIMIZATION DETAILS
====================

Data reduction achieved:
  3.88 GB (JSON) → 80.4 MB (Parquet) = 49.6x compression

Techniques used:
1. Numerical encoding (IDs instead of strings)
2. Optimized dtypes (uint8, uint16, float32)
3. Separate lookup tables
4. Parquet columnar storage with Snappy compression
5. Removed redundant fields
6. Simplified time precision (1 decimal place)

Storage breakdown:
  - replay_id: uint16 (0-4984)
  - player_id: uint16 (0-7887)  
  - unit_id: uint8 (0-589)
  - time: float32 (saves 50% vs float64)
  - build_index: uint16

POSITION VISUALIZATION
======================

To visualize positions on the map:
  1. Open: output/visualizations/index.html
  2. Or run: open output/visualizations/index.html

The visualization shows:
  - Position centroids for both teams
  - Player spawn distributions
  - Win rates by position
  - Build order archetypes
""")

print("\n" + "=" * 80)
print("📚 Additional Resources")
print("=" * 80)
print("""
Source Files:
  src/2-parse-demos.ts              - Parses .sdfz files, extracts builds & positions
  src/3-cluster-positions.py        - Clusters positions into named categories
  src/7-assign-positions-and-export.py - Assigns positions and exports CSVs
  src/8-optimize-to-parquet.py      - Optimizes data to Parquet format

Documentation:
  USAGE.md                          - Complete usage guide
  QUICKSTART.md                     - Quick start guide
  README.md                         - Project overview
""")

print("\n✅ Documentation complete!\n")
