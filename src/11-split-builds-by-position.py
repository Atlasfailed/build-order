#!/usr/bin/env python3
"""
Split builds.parquet into separate files per position for easier web loading.
This creates 8 smaller files (~10 MB each) instead of one 80 MB file.
"""

import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
INPUT_DIR = BASE_DIR / "output" / "optimized"
OUTPUT_DIR = BASE_DIR / "output" / "optimized" / "builds_by_position"

POSITION_NAMES = ['front-1', 'front-2', 'geo', 'geo-sea', 'air', 'eco', 'pond', 'long-sea']

def split_builds_by_position():
    """Split builds.parquet into 8 position-specific files."""
    print("=" * 70)
    print("🔪 Split Builds by Position")
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
    
    # Split by position
    print("\n✂️  Splitting by position...")
    total_size_original = (INPUT_DIR / "builds.parquet").stat().st_size / 1024 / 1024
    total_size_split = 0
    
    for position_id, position_name in enumerate(POSITION_NAMES):
        # Filter builds for this position
        position_builds = builds_with_position[builds_with_position['position_id'] == position_id].copy()
        
        # Drop position_id column (not needed in split files)
        position_builds = position_builds.drop(columns=['position_id'])
        
        # Save to parquet
        output_file = OUTPUT_DIR / f"builds_position_{position_id}_{position_name}.parquet"
        position_builds.to_parquet(output_file, compression='snappy', index=False)
        
        file_size = output_file.stat().st_size / 1024 / 1024
        total_size_split += file_size
        
        print(f"  ✓ Position {position_id} ({position_name:10s}): {len(position_builds):>9,} records → {file_size:>5.1f} MB")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Original file:     {total_size_original:.1f} MB")
    print(f"Split files total: {total_size_split:.1f} MB")
    print(f"Files created:     {len(POSITION_NAMES)}")
    print(f"Average per file:  {total_size_split / len(POSITION_NAMES):.1f} MB")
    print(f"\n✓ Files saved to: {OUTPUT_DIR}")
    
    print("\n💡 Usage:")
    print("  - Load only the position file(s) needed on your website")
    print("  - Each file is ~10 MB, easy to fetch individually")
    print("  - Use position_id (0-7) to determine which file to load")

if __name__ == "__main__":
    split_builds_by_position()
