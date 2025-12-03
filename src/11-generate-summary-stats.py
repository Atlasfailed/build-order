#!/usr/bin/env python3
"""
Generate aggregated summary statistics for the data summary page.
Creates small JSON files with pre-computed data for charts.
"""

import pyarrow.parquet as pq
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / 'output' / 'optimized'
    pages_output_dir = base_dir / 'pages' / 'data' / 'optimized'
    
    print("Loading parquet files...")
    
    # Load the data
    positions_table = pq.read_table(output_dir / 'positions_metadata.parquet')
    index_table = pq.read_table(output_dir / 'index.parquet')
    
    positions_df = positions_table.to_pandas()
    index_df = index_table.to_pandas()
    
    print(f"Loaded {len(positions_df)} position records")
    print(f"Loaded {len(index_df)} index records")
    
    # 1. Generate games by date aggregation
    print("\nAggregating games by date...")
    date_counts = positions_df.groupby('game_date').size().reset_index(name='player_count')
    # Estimate games (assuming ~16 players per game on average)
    date_counts['games'] = (date_counts['player_count'] / 16).round().astype(int)
    date_counts = date_counts.sort_values('game_date')
    
    games_by_date = {
        'dates': date_counts['game_date'].tolist(),
        'games': date_counts['games'].tolist()
    }
    
    print(f"  Date range: {date_counts['game_date'].min()} to {date_counts['game_date'].max()}")
    print(f"  Total dates: {len(date_counts)}")
    print(f"  Total games (estimated): {date_counts['games'].sum()}")
    
    # 2. Generate skill distribution
    print("\nAggregating skill distribution...")
    # Filter out zero skills and create histogram bins
    valid_skills = index_df[index_df['skill'] > 0]['skill']
    
    # Create histogram with 50 bins
    hist, bin_edges = pd.cut(valid_skills, bins=50, retbins=True, include_lowest=True)
    skill_counts = hist.value_counts().sort_index()
    
    # Convert intervals to midpoints for easier plotting
    skill_bins = [(interval.left + interval.right) / 2 for interval in skill_counts.index]
    skill_values = skill_counts.values.tolist()
    
    skill_distribution = {
        'skill_values': valid_skills.tolist(),  # Include raw values for histogram
        'min_skill': float(valid_skills.min()),
        'max_skill': float(valid_skills.max()),
        'mean_skill': float(valid_skills.mean()),
        'median_skill': float(valid_skills.median())
    }
    
    print(f"  Valid skills: {len(valid_skills)}")
    print(f"  Skill range: {skill_distribution['min_skill']:.1f} to {skill_distribution['max_skill']:.1f}")
    print(f"  Mean skill: {skill_distribution['mean_skill']:.1f}")
    
    # 3. Generate overall statistics
    print("\nCalculating summary statistics...")
    unique_games = positions_df['replay_id'].nunique()
    total_players = len(index_df)
    min_date = positions_df['game_date'].min()
    max_date = positions_df['game_date'].max()
    avg_skill = float(valid_skills.mean())
    
    summary_stats = {
        'total_games': unique_games,
        'total_players': total_players,
        'date_range': {
            'min': min_date,
            'max': max_date
        },
        'avg_skill': round(avg_skill, 1)
    }
    
    print(f"  Total games: {unique_games}")
    print(f"  Total players: {total_players}")
    print(f"  Date range: {min_date} to {max_date}")
    print(f"  Average skill: {avg_skill:.1f}")
    
    # Save to JSON files
    print("\nSaving JSON files...")
    pages_output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(pages_output_dir / 'summary_games_by_date.json', 'w') as f:
        json.dump(games_by_date, f)
    print(f"  Saved: summary_games_by_date.json")
    
    with open(pages_output_dir / 'summary_skill_distribution.json', 'w') as f:
        json.dump(skill_distribution, f)
    print(f"  Saved: summary_skill_distribution.json")
    
    with open(pages_output_dir / 'summary_stats.json', 'w') as f:
        json.dump(summary_stats, f)
    print(f"  Saved: summary_stats.json")
    
    print("\n✓ Summary statistics generated successfully!")

if __name__ == '__main__':
    main()
