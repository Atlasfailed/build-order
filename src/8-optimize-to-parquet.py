#!/usr/bin/env python3
"""
Optimize parsed data to Parquet format for efficient storage and querying.

This script:
1. Merges builds.jsonl and positions data
2. Creates optimized Parquet files with only essential data
3. Generates separate index file for metadata
4. Reduces file size by 80-90% compared to JSON
"""

import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import sys

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent

# Paths
PARSED_DIR = BASE_DIR / "data" / "parsed"
OUTPUT_DIR = BASE_DIR / "output" / "optimized"

# Position names mapping
POSITION_NAMES = [
    "front-1",   # 0
    "front-2",   # 1
    "geo",       # 2
    "geo-sea",   # 3
    "air",       # 4
    "eco",       # 5
    "pond",      # 6
    "long-sea"   # 7
]

# Test mode: limit processing for faster testing
TEST_MODE = False
TEST_LIMIT = 100 if TEST_MODE else None

def load_all_builds(builds_file: Path, limit: int = None) -> List[Dict]:
    """Load builds from JSONL file, optionally limiting for testing."""
    builds = []
    print(f"📖 Loading builds from {builds_file.name}...")
    
    if limit:
        print(f"⚠️  TEST MODE: Loading only first {limit} records")
    
    with open(builds_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if limit and len(builds) >= limit:
                break
                
            if line.strip():
                try:
                    builds.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Skipping line {line_num}: {e}")
    
    print(f"✓ Loaded {len(builds):,} builds")
    return builds

def load_position_assignments(assignments_file: Path) -> Dict:
    """Load position assignments if available."""
    if not assignments_file.exists():
        print("⚠️  No position assignments found - will run without position data")
        return {}
    
    assignments = {}
    with open(assignments_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                key = (data['game_id'], data['player_name'])
                assignments[key] = data
    
    print(f"✓ Loaded {len(assignments):,} position assignments")
    return assignments

def simplify_time(time_ms: float) -> float:
    """Round time to 1 decimal place in seconds."""
    return round(time_ms, 1)

def normalize_faction(faction: str) -> str:
    """
    Normalize faction names to 3-letter codes.
    Full names: Armada, Cortex, Legion
    Short codes: arm, cor, leg
    """
    if not faction or faction == 'Unknown':
        return 'unk'
    
    faction_lower = faction.lower()
    
    # Map full names to short codes
    faction_map = {
        'armada': 'arm',
        'cortex': 'cor',
        'legion': 'leg',
        'arm': 'arm',
        'cor': 'cor',
        'leg': 'leg'
    }
    
    return faction_map.get(faction_lower, 'unk')

def optimize_builds(builds: List[Dict], assignments: Dict) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Optimize builds data by:
    1. Removing unnecessary fields
    2. Simplifying time precision
    3. Creating separate index and builds tables
    4. Using numerical IDs with lookup tables
    """
    print("\n🔨 Optimizing builds data...")
    
    # Create lookup tables for categorical data
    replay_ids = []
    player_names = []
    unit_names = []
    
    # Create index records (one per player/game)
    index_records = []
    # Create build records (multiple per player/game)
    build_records = []
    # Create positions metadata records (spawn coordinates and dates)
    positions_metadata_records = []
    
    for idx, build_data in enumerate(builds):
        if idx % 10000 == 0 and idx > 0:
            print(f"  Processed {idx:,}/{len(builds):,} builds...")
        
        replay_id = build_data['replayId']
        player_name = build_data['playerName']
        
        # Collect unique values for lookup tables
        if replay_id not in replay_ids:
            replay_ids.append(replay_id)
        if player_name not in player_names:
            player_names.append(player_name)
        
        # Get position assignment if available
        assignment_key = (replay_id, player_name)
        assignment = assignments.get(assignment_key, {})
        
        # Create index record (metadata only, one per player)
        # Use indices instead of strings
        # Normalize faction to 3-letter code
        faction_normalized = normalize_faction(build_data.get('faction', 'Unknown'))
        
        # Get position ID from assignment (0-7 based on POSITION_NAMES)
        position_name = assignment.get('position')
        position_id = POSITION_NAMES.index(position_name) if position_name in POSITION_NAMES else None
        
        index_record = {
            'replay_id': replay_ids.index(replay_id),
            'player_id': player_names.index(player_name),
            'skill': round(build_data['skill'], 2),
            'rank': build_data.get('rank'),
            'won_game': build_data['wonGame'],
            'position_id': position_id,  # 0-7 or None
            'distance_from_centroid': round(assignment.get('distance', 0), 1) if assignment.get('distance') else None,
            'faction': faction_normalized,
        }
        index_records.append(index_record)
        
        # Create positions metadata record (spawn coordinates and date)
        positions_metadata_record = {
            'replay_id': replay_ids.index(replay_id),
            'player_id': player_names.index(player_name),
            'spawn_x': round(build_data['position']['x'], 1),
            'spawn_z': round(build_data['position']['z'], 1),
            'game_date': build_data['gameDate'],
        }
        positions_metadata_records.append(positions_metadata_record)
        
        # Create build order records (one per build step)
        for build_idx, build_step in enumerate(build_data['buildOrder']):
            unit_name = build_step['unitDisplayName']
            if unit_name not in unit_names:
                unit_names.append(unit_name)
            
            build_record = {
                'replay_id': replay_ids.index(replay_id),
                'player_id': player_names.index(player_name),
                'build_index': build_idx,
                'time': simplify_time(build_step['time']),
                'unit_id': unit_names.index(unit_name)
            }
            build_records.append(build_record)
    
    print(f"✓ Created {len(index_records):,} index records")
    print(f"✓ Created {len(build_records):,} build step records")
    print(f"✓ Created {len(positions_metadata_records):,} positions metadata records")
    
    # Convert to DataFrames with appropriate dtypes
    index_df = pd.DataFrame(index_records)
    builds_df = pd.DataFrame(build_records)
    positions_metadata_df = pd.DataFrame(positions_metadata_records)
    
    # Optimize dtypes for even smaller file size
    index_df['replay_id'] = index_df['replay_id'].astype('uint16')
    index_df['player_id'] = index_df['player_id'].astype('uint16')
    if 'rank' in index_df.columns:
        index_df['rank'] = index_df['rank'].astype('Int8')  # Nullable int
    if 'position_id' in index_df.columns:
        index_df['position_id'] = index_df['position_id'].astype('Int8')  # Nullable int (0-7)
    
    builds_df['replay_id'] = builds_df['replay_id'].astype('uint16')
    builds_df['player_id'] = builds_df['player_id'].astype('uint16')
    builds_df['build_index'] = builds_df['build_index'].astype('uint16')
    builds_df['unit_id'] = builds_df['unit_id'].astype('uint8')
    builds_df['time'] = builds_df['time'].astype('float32')
    
    # Optimize positions metadata dtypes
    positions_metadata_df['replay_id'] = positions_metadata_df['replay_id'].astype('uint16')
    positions_metadata_df['player_id'] = positions_metadata_df['player_id'].astype('uint16')
    positions_metadata_df['spawn_x'] = positions_metadata_df['spawn_x'].astype('float32')
    positions_metadata_df['spawn_z'] = positions_metadata_df['spawn_z'].astype('float32')
    
    # Create lookup tables
    lookup_tables = {
        'replays': pd.DataFrame({'replay_id': range(len(replay_ids)), 'replay_name': replay_ids}),
        'players': pd.DataFrame({'player_id': range(len(player_names)), 'player_name': player_names}),
        'units': pd.DataFrame({'unit_id': range(len(unit_names)), 'unit_name': unit_names}),
        'positions': pd.DataFrame({'position_id': range(len(POSITION_NAMES)), 'position_name': POSITION_NAMES})
    }
    
    print(f"\n📚 Lookup Tables Created:")
    print(f"  • Replays: {len(replay_ids):,} unique")
    print(f"  • Players: {len(player_names):,} unique")
    print(f"  • Units: {len(unit_names):,} unique")
    
    return index_df, builds_df, positions_metadata_df, lookup_tables

def save_to_parquet(df: pd.DataFrame, output_path: Path, compression: str = 'snappy'):
    """Save DataFrame to Parquet with compression."""
    print(f"\n💾 Saving {output_path.name}...")
    
    # Get size info
    memory_usage = df.memory_usage(deep=True).sum()
    print(f"  DataFrame memory: {memory_usage / 1024 / 1024:.1f} MB")
    
    # Save to Parquet
    df.to_parquet(
        output_path,
        engine='pyarrow',
        compression=compression,
        index=False
    )
    
    # Report file size
    file_size = output_path.stat().st_size
    print(f"  File size: {file_size / 1024 / 1024:.1f} MB")
    print(f"  Compression ratio: {memory_usage / file_size:.1f}x")

def create_summary_stats(index_df: pd.DataFrame, positions_metadata_df: pd.DataFrame) -> Dict:
    """Generate summary statistics."""
    stats = {
        'total_games': index_df['replay_id'].nunique(),
        'total_players': len(index_df),
        'total_builds': len(index_df),
        'date_range': {
            'from': positions_metadata_df['game_date'].min(),
            'to': positions_metadata_df['game_date'].max()
        },
        'skill_range': {
            'min': float(index_df['skill'].min()),
            'max': float(index_df['skill'].max()),
            'mean': float(index_df['skill'].mean()),
            'median': float(index_df['skill'].median())
        },
        'win_rate': {
            'overall': float(index_df['won_game'].mean()),
        },
        'positions': index_df['assigned_position'].value_counts().to_dict() if 'assigned_position' in index_df.columns else {}
    }
    
    return stats

def main():
    print("=" * 70)
    print("🚀 BAR Build Data Optimization to Parquet")
    print("=" * 70)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Load builds data (prefer enriched version if available)
    enriched_builds = PARSED_DIR / "builds-enriched.jsonl"
    builds_file = enriched_builds if enriched_builds.exists() else PARSED_DIR / "builds.jsonl"
    
    if not builds_file.exists():
        print(f"❌ Error: {builds_file} not found")
        print("   Run 2-parse-demos.ts first")
        sys.exit(1)
    
    if TEST_MODE:
        print(f"\n⚠️  TEST MODE ENABLED - Processing only {TEST_LIMIT} records\n")
    
    builds = load_all_builds(builds_file, limit=TEST_LIMIT)
    
    # Step 2: Load position assignments (optional)
    assignments_file = BASE_DIR / "data" / "analysis" / "position-assignments.jsonl"
    assignments = load_position_assignments(assignments_file)
    
    # Step 3: Optimize and split data
    index_df, builds_df, positions_metadata_df, lookup_tables = optimize_builds(builds, assignments)
    
    # Step 4: Save to Parquet
    save_to_parquet(index_df, OUTPUT_DIR / "index.parquet", compression='snappy')
    save_to_parquet(builds_df, OUTPUT_DIR / "builds.parquet", compression='snappy')
    save_to_parquet(positions_metadata_df, OUTPUT_DIR / "positions_metadata.parquet", compression='snappy')
    
    # Save lookup tables
    print("\n💾 Saving lookup tables...")
    for name, df in lookup_tables.items():
        lookup_path = OUTPUT_DIR / f"lookup_{name}.parquet"
        save_to_parquet(df, lookup_path, compression='snappy')
    
    # Step 5: Create summary stats
    stats = create_summary_stats(index_df, positions_metadata_df)
    stats_file = OUTPUT_DIR / "summary.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\n✓ Summary saved to {stats_file}")
    
    # Step 6: Compare sizes
    print("\n" + "=" * 70)
    print("📊 SIZE COMPARISON")
    print("=" * 70)
    
    original_size = builds_file.stat().st_size
    parquet_size = (OUTPUT_DIR / "index.parquet").stat().st_size + (OUTPUT_DIR / "builds.parquet").stat().st_size + (OUTPUT_DIR / "positions_metadata.parquet").stat().st_size
    
    print(f"Original (builds.jsonl):  {original_size / 1024 / 1024 / 1024:.2f} GB")
    print(f"Optimized (Parquet):      {parquet_size / 1024 / 1024:.1f} MB")
    print(f"Space saved:              {(original_size - parquet_size) / 1024 / 1024 / 1024:.2f} GB")
    print(f"Compression ratio:        {original_size / parquet_size:.1f}x")
    
    print("\n" + "=" * 70)
    print("✅ Optimization Complete!")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  • {OUTPUT_DIR / 'index.parquet'} - Player/game metadata")
    print(f"  • {OUTPUT_DIR / 'builds.parquet'} - Build order steps")
    print(f"  • {OUTPUT_DIR / 'positions_metadata.parquet'} - Spawn coordinates and dates")
    print(f"  • {OUTPUT_DIR / 'summary.json'} - Summary statistics")
    
    print("\n📈 Summary Statistics:")
    print(f"  • Games: {stats['total_games']:,}")
    print(f"  • Players: {stats['total_players']:,}")
    print(f"  • Skill range: {stats['skill_range']['min']:.1f} - {stats['skill_range']['max']:.1f} (avg: {stats['skill_range']['mean']:.1f})")
    print(f"  • Win rate: {stats['win_rate']['overall']*100:.1f}%")
    
    if stats['positions']:
        print(f"\n  Position distribution:")
        for pos, count in sorted(stats['positions'].items(), key=lambda x: x[1], reverse=True):
            if pos:  # Skip None values
                print(f"    {pos}: {count:,}")

if __name__ == "__main__":
    main()
