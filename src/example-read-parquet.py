#!/usr/bin/env python3
"""
Example: How to read and query the optimized Parquet files
"""

import pandas as pd
from pathlib import Path

# Load the data
BASE_DIR = Path(__file__).parent.parent
OPTIMIZED_DIR = BASE_DIR / "output" / "optimized"

print("🔍 Loading Parquet files...\n")

# Load index (player/game metadata)
index_df = pd.read_parquet(OPTIMIZED_DIR / "index.parquet")
print(f"✓ Loaded {len(index_df):,} players from {index_df['replay_id'].nunique():,} games")

# Load builds (individual build steps)
builds_df = pd.read_parquet(OPTIMIZED_DIR / "builds.parquet")
print(f"✓ Loaded {len(builds_df):,} build steps")

# Load lookup tables
lookup_replays = pd.read_parquet(OPTIMIZED_DIR / "lookup_replays.parquet")
lookup_players = pd.read_parquet(OPTIMIZED_DIR / "lookup_players.parquet")
lookup_units = pd.read_parquet(OPTIMIZED_DIR / "lookup_units.parquet")
print(f"✓ Loaded {len(lookup_replays):,} replays, {len(lookup_players):,} players, {len(lookup_units):,} units\n")

# Example queries
print("=" * 70)
print("📊 Example Queries")
print("=" * 70)

# 1. Top 10 highest skilled players
print("\n1️⃣  Top 10 Highest Skilled Players:")
top_players = index_df.nlargest(10, 'skill').copy()
# Join with player names
top_players = top_players.merge(lookup_players, on='player_id')
print(top_players[['player_name', 'skill', 'game_date']].to_string(index=False))

# 2. Players with skill > 50
high_skill = index_df[index_df['skill'] > 50]
print(f"\n2️⃣  High skill players (>50): {len(high_skill):,} games")

# 3. Get build order for a specific player
print("\n3️⃣  Example Build Order:")
sample_player = index_df.iloc[0]
player_builds = builds_df[
    (builds_df['replay_id'] == sample_player['replay_id']) &
    (builds_df['player_id'] == sample_player['player_id'])
].head(10)

# Join with unit names
player_builds = player_builds.merge(lookup_units, on='unit_id')
player_name = lookup_players[lookup_players['player_id'] == sample_player['player_id']]['player_name'].iloc[0]

print(f"\nPlayer: {player_name} (Skill: {sample_player['skill']:.1f})")
print("First 10 builds:")
for _, build in player_builds.iterrows():
    print(f"  {build['time']:.1f}s - {build['unit_name']}")

# 4. Most common first build
print("\n4️⃣  Most Common First Builds:")
first_builds = builds_df[builds_df['build_index'] == 0]
first_build_counts = first_builds['unit_id'].value_counts().head(10)
# Map to unit names
first_build_counts.index = first_build_counts.index.map(
    lambda x: lookup_units[lookup_units['unit_id'] == x]['unit_name'].iloc[0]
)
print(first_build_counts.to_string())

# 5. Average number of builds per player
print(f"\n5️⃣  Average builds per player: {len(builds_df) / len(index_df):.1f}")

# 6. Date range and game distribution
print(f"\n6️⃣  Date Range: {index_df['game_date'].min()} to {index_df['game_date'].max()}")
games_per_day = index_df.groupby('game_date').size()
print(f"   Games per day: {games_per_day.mean():.1f} avg (max: {games_per_day.max()})")

print("\n" + "=" * 70)
print("💡 File Sizes:")
print("=" * 70)
print(f"index.parquet:         {(OPTIMIZED_DIR / 'index.parquet').stat().st_size / 1024 / 1024:.1f} MB")
print(f"builds.parquet:        {(OPTIMIZED_DIR / 'builds.parquet').stat().st_size / 1024 / 1024:.1f} MB")
print(f"lookup_replays.parquet: {(OPTIMIZED_DIR / 'lookup_replays.parquet').stat().st_size / 1024:.1f} KB")
print(f"lookup_players.parquet: {(OPTIMIZED_DIR / 'lookup_players.parquet').stat().st_size / 1024:.1f} KB")
print(f"lookup_units.parquet:   {(OPTIMIZED_DIR / 'lookup_units.parquet').stat().st_size / 1024:.1f} KB")
print(f"Total:                  {sum(f.stat().st_size for f in OPTIMIZED_DIR.glob('*.parquet')) / 1024 / 1024:.1f} MB")
