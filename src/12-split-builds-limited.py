#!/usr/bin/env python3
"""
Split builds.parquet into separate files per position, limiting to first 100 builds per player.
This creates much smaller files optimized for web loading.
"""

import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
INPUT_DIR = BASE_DIR / "output" / "optimized"
OUTPUT_DIR = BASE_DIR / "output" / "optimized" / "builds_by_position_limited"

POSITION_NAMES = ['front-1', 'front-2', 'geo', 'geo-sea', 'air', 'eco', 'pond', 'long-sea']
BUILD_LIMIT = 100  # First N builds per player

def split_builds_by_position_limited():
    """Split builds.parquet into 8 position-specific files with build limit."""
    print("=" * 70)
    print(f"🔪 Split Builds by Position (Limited to {BUILD_LIMIT} builds/player)")
    print("=" * 70)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load index to get position mappings
    print("\n📖 Loading index...")
    index_df = pd.read_parquet(INPUT_DIR / "index.parquet")
    print(f"✓ Loaded {len(index_df):,} index records")
    
    # Load builds
    print("\n📖 Loading builds...")
    builds_df = pd.read_parquet(INPUT_DIR / "builds.parquet")
    print(f"✓ Loaded {len(builds_df):,} build records")
    
    # Merge to add position_id to builds
    print("\n🔗 Merging position data...")
    builds_with_position = builds_df.merge(
        index_df[['replay_id', 'player_id', 'position_id']],
        on=['replay_id', 'player_id'],
        how='left'
    )
    print(f"✓ Merged data")
    
    # Limit builds per player
    print(f"\n✂️  Limiting to first {BUILD_LIMIT} builds per player...")
    builds_limited = builds_with_position[builds_with_position['build_index'] < BUILD_LIMIT].copy()
    
    original_count = len(builds_with_position)
    limited_count = len(builds_limited)
    reduction_pct = (1 - limited_count / original_count) * 100
    
    print(f"  Original: {original_count:,} records")
    print(f"  Limited:  {limited_count:,} records")
    print(f"  Reduced:  {reduction_pct:.1f}%")
    
    # Split by position
    print("\n✂️  Splitting by position...")
    total_size_original = (INPUT_DIR / "builds.parquet").stat().st_size / 1024 / 1024
    total_size_split = 0
    
    stats = []
    
    for position_id, position_name in enumerate(POSITION_NAMES):
        # Filter builds for this position
        position_builds = builds_limited[builds_limited['position_id'] == position_id].copy()
        
        # Drop position_id column (not needed in split files)
        position_builds = position_builds.drop(columns=['position_id'])
        
        # Save to parquet
        output_file = OUTPUT_DIR / f"builds_position_{position_id}_{position_name}.parquet"
        position_builds.to_parquet(output_file, compression='snappy', index=False)
        
        file_size = output_file.stat().st_size / 1024 / 1024
        total_size_split += file_size
        
        stats.append({
            'position_id': position_id,
            'name': position_name,
            'records': len(position_builds),
            'size_mb': file_size
        })
        
        print(f"  ✓ Position {position_id} ({position_name:10s}): {len(position_builds):>9,} records → {file_size:>5.1f} MB")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Original file:     {total_size_original:.1f} MB (all builds)")
    print(f"Split files total: {total_size_split:.1f} MB (limited to {BUILD_LIMIT} builds/player)")
    print(f"Size reduction:    {(1 - total_size_split / total_size_original) * 100:.1f}%")
    print(f"Files created:     {len(POSITION_NAMES)}")
    print(f"Average per file:  {total_size_split / len(POSITION_NAMES):.1f} MB")
    
    # Show largest files
    print("\n📦 Largest files:")
    for stat in sorted(stats, key=lambda x: x['size_mb'], reverse=True)[:3]:
        print(f"  {stat['name']:10s}: {stat['size_mb']:.1f} MB ({stat['records']:,} records)")
    
    print(f"\n✓ Files saved to: {OUTPUT_DIR}")
    
    print("\n💡 Trade-offs:")
    print(f"  ✅ Much smaller files (easier to load on GitHub Pages)")
    print(f"  ✅ First {BUILD_LIMIT} builds capture early game strategy")
    print(f"  ⚠️  Late game builds (index > {BUILD_LIMIT}) not included")
    print(f"  💡 Most strategic info is in first {BUILD_LIMIT} builds anyway")

if __name__ == "__main__":
    split_builds_by_position_limited()
