#!/usr/bin/env python3
"""
Create a 2-tier build order system with lazy loading:
- Tier 1: Unique 10-step prefixes (small, loaded immediately)
- Tier 2: Full builds for each prefix (lazy loaded on click)

This dramatically reduces initial page load by only loading the first 10 steps
of each unique build path. When users expand beyond step 10, the full builds
are loaded on-demand.
"""

import pandas as pd
import hashlib
from pathlib import Path
from collections import defaultdict
import json

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
INPUT_DIR = BASE_DIR / "output" / "optimized"
OUTPUT_DIR = BASE_DIR / "output" / "optimized" / "builds_lazy_load"

POSITION_NAMES = ['front-1', 'front-2', 'geo', 'geo-sea', 'air', 'eco', 'pond', 'long-sea']
PREFIX_LENGTH = 10  # First N builds to include in prefix
CHUNK_SIZE = 100  # Group this many prefixes into one Tier 2 file

def create_prefix_hash(unit_ids):
    """Create a short hash for a build sequence."""
    s = ','.join(map(str, unit_ids))
    return hashlib.md5(s.encode()).hexdigest()[:8]

def extract_prefixes_by_position():
    """Create prefix tree files for each position."""
    print("=" * 70)
    print(f"🌳 Creating Build Prefix Tree (First {PREFIX_LENGTH} steps)")
    print("=" * 70)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load index and builds
    print("\n📖 Loading data...")
    index_df = pd.read_parquet(INPUT_DIR / "index.parquet")
    builds_df = pd.read_parquet(INPUT_DIR / "builds.parquet")
    
    print(f"   Loaded {len(index_df):,} players and {len(builds_df):,} builds")
    
    # Merge to add position_id
    builds_with_position = builds_df.merge(
        index_df[['replay_id', 'player_id', 'position_id', 'skill', 'won_game', 'faction']],
        on=['replay_id', 'player_id'],
        how='left'
    )
    
    total_size_tier1 = 0
    total_size_tier2 = 0
    total_tier2_files = 0
    stats = []
    
    for position_id, position_name in enumerate(POSITION_NAMES):
        print(f"\n📍 Processing position {position_id}: {position_name}")
        
        position_builds = builds_with_position[
            builds_with_position['position_id'] == position_id
        ].copy()
        
        if len(position_builds) == 0:
            print(f"  ⚠️  No builds for this position")
            continue
        
        # Group by player to extract prefixes
        prefix_to_players = defaultdict(lambda: {
            'player_ids': [],
            'skills': [],
            'won_games': [],
            'factions': [],
            'full_builds': []
        })
        
        player_count = 0
        for (replay_id, player_id), player_builds in position_builds.groupby(['replay_id', 'player_id']):
            player_count += 1
            # Sort by build_index
            player_builds = player_builds.sort_values('build_index')
            
            # Get prefix (first N builds)
            prefix_builds = player_builds.head(PREFIX_LENGTH)
            prefix_units = tuple(prefix_builds['unit_id'].tolist())
            
            # Get player metadata
            player_skill = player_builds['skill'].iloc[0]
            player_won = player_builds['won_game'].iloc[0]
            player_faction = player_builds['faction'].iloc[0]
            
            # Store prefix info
            prefix_to_players[prefix_units]['player_ids'].append({
                'replay_id': int(replay_id),
                'player_id': int(player_id)
            })
            prefix_to_players[prefix_units]['skills'].append(float(player_skill))
            prefix_to_players[prefix_units]['won_games'].append(bool(player_won))
            prefix_to_players[prefix_units]['factions'].append(str(player_faction))
            
            # Store full builds for Tier 2 (only builds after the prefix)
            if len(player_builds) > PREFIX_LENGTH:
                remaining_builds = player_builds.iloc[PREFIX_LENGTH:].copy()
                prefix_to_players[prefix_units]['full_builds'].append({
                    'replay_id': int(replay_id),
                    'player_id': int(player_id),
                    'builds': remaining_builds[['build_index', 'time', 'unit_id']].to_dict('records')
                })
        
        print(f"  Found {player_count:,} players, {len(prefix_to_players):,} unique prefixes")
        
        # Create Tier 1: Prefix file
        tier1_records = []
        tier2_files = []
        
        # Collect all prefix data first
        prefix_data_list = []
        for prefix_units, data in prefix_to_players.items():
            prefix_hash = create_prefix_hash(prefix_units)
            player_count_prefix = len(data['player_ids'])
            avg_skill = sum(data['skills']) / player_count_prefix
            win_rate = sum(data['won_games']) / player_count_prefix
            
            prefix_data_list.append({
                'prefix_hash': prefix_hash,
                'prefix_units': prefix_units,
                'player_count': player_count_prefix,
                'avg_skill': avg_skill,
                'win_rate': win_rate,
                'has_continuation': len(data['full_builds']) > 0,
                'faction_counts': {
                    'arm': data['factions'].count('arm'),
                    'cor': data['factions'].count('cor'),
                    'leg': data['factions'].count('leg')
                },
                'full_builds': data['full_builds']
            })
        
        # Sort by player count (descending) to group popular prefixes together
        prefix_data_list.sort(key=lambda x: x['player_count'], reverse=True)
        
        # Group prefixes into chunks for Tier 2
        prefix_to_chunk = {}
        chunk_idx = 0
        for i in range(0, len(prefix_data_list), CHUNK_SIZE):
            chunk_prefixes = prefix_data_list[i:i+CHUNK_SIZE]
            
            # Collect all builds for this chunk
            chunk_builds = []
            for prefix_data in chunk_prefixes:
                prefix_hash = prefix_data['prefix_hash']
                prefix_to_chunk[prefix_hash] = chunk_idx
                
                if prefix_data['full_builds']:
                    for b in prefix_data['full_builds']:
                        for build in b['builds']:
                            chunk_builds.append({
                                'prefix_hash': prefix_hash,
                                'replay_id': b['replay_id'],
                                'player_id': b['player_id'],
                                'build_index': build['build_index'],
                                'time': build['time'],
                                'unit_id': build['unit_id']
                            })
            
            # Save chunk if it has builds
            if chunk_builds:
                tier2_file = OUTPUT_DIR / f"builds_position_{position_id}_chunk_{chunk_idx}.parquet"
                tier2_df = pd.DataFrame(chunk_builds)
                
                # Optimize dtypes
                tier2_df['replay_id'] = tier2_df['replay_id'].astype('uint32')
                tier2_df['player_id'] = tier2_df['player_id'].astype('uint16')
                tier2_df['build_index'] = tier2_df['build_index'].astype('uint16')
                tier2_df['unit_id'] = tier2_df['unit_id'].astype('uint8')
                tier2_df['time'] = tier2_df['time'].astype('float32')
                
                tier2_df.to_parquet(tier2_file, compression='snappy', index=False)
                tier2_size = tier2_file.stat().st_size / 1024
                total_size_tier2 += tier2_size
                total_tier2_files += 1
                tier2_files.append((chunk_idx, tier2_size, len(chunk_prefixes)))
                
                chunk_idx += 1
        
        # Build Tier 1 records with chunk references
        for prefix_data in prefix_data_list:
            tier1_records.append({
                'prefix_hash': prefix_data['prefix_hash'],
                'prefix_units': list(prefix_data['prefix_units']),
                'player_count': prefix_data['player_count'],
                'avg_skill': round(prefix_data['avg_skill'], 2),
                'win_rate': round(prefix_data['win_rate'], 3),
                'has_continuation': prefix_data['has_continuation'],
                'chunk_id': prefix_to_chunk.get(prefix_data['prefix_hash']),
                'faction_counts': prefix_data['faction_counts']
            })
        
        # Save Tier 1 prefix file as JSON (easier to parse in JS)
        tier1_file = OUTPUT_DIR / f"builds_position_{position_id}_{position_name}_prefixes.json"
        with open(tier1_file, 'w') as f:
            json.dump({
                'position_id': position_id,
                'position_name': position_name,
                'prefix_length': PREFIX_LENGTH,
                'unique_prefixes': len(tier1_records),
                'prefixes': tier1_records
            }, f, separators=(',', ':'))  # Compact JSON
        
        tier1_size = tier1_file.stat().st_size / 1024
        total_size_tier1 += tier1_size
        
        avg_tier2_size = sum(s for _, s, _ in tier2_files) / len(tier2_files) if tier2_files else 0
        total_tier2_size = sum(s for _, s, _ in tier2_files)
        
        print(f"  ✅ Tier 1 (prefixes): {tier1_size:.1f} KB ({len(tier1_records)} unique paths)")
        print(f"  ✅ Tier 2 (full builds): {len(tier2_files)} chunks, avg {avg_tier2_size:.1f} KB, total {total_tier2_size:.1f} KB")
        print(f"     ({len(tier1_records)} prefixes grouped into {len(tier2_files)} files, ~{CHUNK_SIZE} prefixes/file)")
        
        stats.append({
            'position': position_name,
            'position_id': position_id,
            'tier1_size': tier1_size,
            'tier2_files': len(tier2_files),
            'tier2_total_size': total_tier2_size,
            'unique_prefixes': len(tier1_records)
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    # Get original size
    original_dir = INPUT_DIR / "builds_by_position_limited"
    original_size = 0
    if original_dir.exists():
        for f in original_dir.glob("*.parquet"):
            original_size += f.stat().st_size / 1024 / 1024
    
    print(f"\n📦 File Sizes:")
    print(f"   Original (limited builds): {original_size:.1f} MB")
    print(f"   Tier 1 (prefixes):         {total_size_tier1/1024:.2f} MB (loaded immediately)")
    print(f"   Tier 2 (full builds):      {total_size_tier2/1024:.2f} MB ({total_tier2_files} files, lazy loaded)")
    print(f"   Total:                     {(total_size_tier1+total_size_tier2)/1024:.2f} MB")
    
    if original_size > 0:
        reduction = (1 - (total_size_tier1/1024)/original_size) * 100
        print(f"\n💡 Initial load reduction: {reduction:.1f}%")
        print(f"   From {original_size:.1f} MB → {total_size_tier1/1024:.2f} MB")
    
    print("\n📍 Per Position:")
    for stat in stats:
        print(f"   {stat['position']:10s}: {stat['unique_prefixes']:3d} prefixes, "
              f"Tier1={stat['tier1_size']:5.1f}KB, "
              f"Tier2={stat['tier2_files']:3d} files ({stat['tier2_total_size']:6.1f}KB)")
    
    print(f"\n✅ Files saved to: {OUTPUT_DIR}")
    
    # Save metadata for JavaScript
    metadata_file = OUTPUT_DIR / "lazy_load_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump({
            'prefix_length': PREFIX_LENGTH,
            'positions': stats,
            'total_tier1_kb': round(total_size_tier1, 1),
            'total_tier2_kb': round(total_size_tier2, 1),
            'total_tier2_files': total_tier2_files,
            'original_size_mb': round(original_size, 2) if original_size > 0 else None,
            'reduction_percent': round(reduction, 1) if original_size > 0 else None
        }, f, indent=2)
    
    print(f"✅ Metadata saved to: {metadata_file}")
    
    print("\n" + "=" * 70)
    print("🎉 Lazy loading structure created successfully!")
    print("=" * 70)

if __name__ == "__main__":
    extract_prefixes_by_position()
