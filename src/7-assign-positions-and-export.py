#!/usr/bin/env python3
"""
Assign players to positions based on manual labels, calculate centroids,
and export CSV files with build orders per position.
"""

import json
import re
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import math

# Position names
POSITION_NAMES = [
    "front-1",
    "front-2", 
    "geo",
    "geo-sea",
    "air",
    "eco",
    "pond",
    "long-sea"
]

def parse_position_labels(labels_file: Path) -> Dict[str, List[Tuple[str, int, str, float, float]]]:
    """
    Parse the position labels file and extract all labeled positions.
    Returns: Dict[position_name -> List[(game_id, team_id, player_name, x, z)]]
    """
    labeled_positions = defaultdict(list)
    
    with open(labels_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by game sections
    game_sections = re.split(r'Game: ([^\n]+)', content)
    
    for i in range(1, len(game_sections), 2):
        game_id = game_sections[i].strip()
        game_content = game_sections[i + 1]
        
        # Extract replay ID from game filename
        replay_id = game_id.replace('.sdfz', '')
        
        # Find all player position assignments
        # Format: PlayerName | Team X | Position: position-name
        pattern = r'(\S+)\s+\|\s+Team\s+(\d+)\s+\|\s+Position:\s+(\S+)'
        matches = re.findall(pattern, game_content)
        
        for player_name, team_id, position in matches:
            if position != "wrong":  # Skip wrong positions for centroid calculation
                labeled_positions[position].append({
                    'game_id': replay_id,
                    'team_id': int(team_id),
                    'player_name': player_name,
                    'position': position
                })
    
    return labeled_positions


def load_parsed_data(parsed_dir: Path) -> Tuple[Dict, Dict]:
    """
    Load all parsed game data and build orders.
    Returns: (game_data_dict, builds_dict)
    """
    game_data = {}
    builds_data = defaultdict(list)
    
    # Load all game JSON files
    for game_file in parsed_dir.glob("game-*.json"):
        with open(game_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            game_data[data['replayId']] = data
    
    # Load builds-with-winners.jsonl (has correct won_game data)
    builds_file = parsed_dir / "builds-with-winners.jsonl"
    if builds_file.exists():
        with open(builds_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    build = json.loads(line)
                    key = (build['replayId'], build['playerName'])
                    builds_data[key] = build
    
    return game_data, builds_data


def mirror_position(x: float, z: float, map_size: int = 12288) -> Tuple[float, float]:
    """
    Mirror a position across the top-left to bottom-right diagonal.
    This swaps coordinates across the line x = z.
    """
    # Mirror across diagonal: swap x and z, then flip to opposite corner
    return map_size - z, map_size - x


def calculate_centroids(labeled_positions: Dict, game_data: Dict, map_size: int = 12288) -> Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Calculate centroid for each position based on labeled examples.
    Since positions are mirrored across the diagonal, we calculate TWO centroids per position:
    one for team 0 (bottom-right) and one for team 1 (top-left).
    
    Returns: Dict[position_name -> (team0_centroid, team1_centroid)]
    """
    centroids = {}
    
    for position, labels in labeled_positions.items():
        team0_coords = []  # Team 0 (bottom-right, high x, low z)
        team1_coords = []  # Team 1 (top-left, low x, high z)
        
        for label in labels:
            game_id = label['game_id']
            player_name = label['player_name']
            team_id = label['team_id']
            
            if game_id in game_data:
                # Find the player in the game data
                for player in game_data[game_id]['players']:
                    if player['name'] == player_name and player.get('startPos'):
                        x = player['startPos']['x']
                        z = player['startPos']['z']
                        
                        # Determine which team based on ally team
                        if player['allyTeamId'] == 0:
                            team0_coords.append((x, z))
                        else:  # allyTeamId == 1
                            team1_coords.append((x, z))
                        break
        
        if team0_coords and team1_coords:
            # Calculate team 0 centroid
            team0_x = sum(x for x, z in team0_coords) / len(team0_coords)
            team0_z = sum(z for x, z in team0_coords) / len(team0_coords)
            
            # Calculate team 1 centroid
            team1_x = sum(x for x, z in team1_coords) / len(team1_coords)
            team1_z = sum(z for x, z in team1_coords) / len(team1_coords)
            
            centroids[position] = ((team0_x, team0_z), (team1_x, team1_z))
            print(f"Position '{position}':")
            print(f"  Team 0 centroid: ({team0_x:.1f}, {team0_z:.1f}) from {len(team0_coords)} examples")
            print(f"  Team 1 centroid: ({team1_x:.1f}, {team1_z:.1f}) from {len(team1_coords)} examples")
    
    return centroids


def calculate_distance(x1: float, z1: float, x2: float, z2: float) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)


def assign_position(player_pos: Tuple[float, float], ally_team_id: int, 
                   centroids: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]) -> Tuple[str, float]:
    """
    Assign a player to the closest position centroid based on their team.
    Returns: (position_name, distance)
    """
    x, z = player_pos
    min_distance = float('inf')
    best_position = "unknown"
    
    for position, (team0_centroid, team1_centroid) in centroids.items():
        # Select the appropriate centroid based on ally team
        if ally_team_id == 0:
            cx, cz = team0_centroid
        else:
            cx, cz = team1_centroid
        
        dist = calculate_distance(x, z, cx, cz)
        if dist < min_distance:
            min_distance = dist
            best_position = position
    
    return best_position, min_distance


def assign_all_positions(game_data: Dict, centroids: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]], builds_data: Dict) -> Dict:
    """
    Assign positions to all players in all games.
    Returns: Dict[(game_id, player_name) -> {position, distance, ...}]
    """
    assignments = {}
    
    for game_id, game in game_data.items():
        for player in game['players']:
            if player.get('startPos'):
                pos = (player['startPos']['x'], player['startPos']['z'])
                position, distance = assign_position(pos, player['allyTeamId'], centroids)
                
                key = (game_id, player['name'])
                
                # Get won_game from builds_data (which has correct data from builds-with-winners.jsonl)
                build_data = builds_data.get(key, {})
                won_game = build_data.get('won_game', False)
                
                assignments[key] = {
                    'game_id': game_id,
                    'player_name': player['name'],
                    'player_id': player['playerId'],
                    'team_id': player['teamId'],
                    'ally_team_id': player['allyTeamId'],
                    'position': position,
                    'distance': distance,
                    'skill': player['skill'],
                    'rank': player.get('rank'),
                    'faction': player.get('faction', 'Unknown'),
                    'startPos': player['startPos'],
                    'won_game': won_game
                }
    
    return assignments


def calculate_average_skill(game_data: Dict, game_id: str) -> float:
    """Calculate average skill for a game."""
    game = game_data.get(game_id)
    if not game:
        return 0.0
    
    skills = [p['skill'] for p in game['players'] if p.get('skill')]
    return sum(skills) / len(skills) if skills else 0.0


def export_position_csvs(assignments: Dict, builds_data: Dict, game_data: Dict, output_dir: Path):
    """
    Export CSV files per position with build orders.
    Each column is a player-game, rows contain metadata and build order.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group assignments by position
    by_position = defaultdict(list)
    for key, assignment in assignments.items():
        position = assignment['position']
        if position != "unknown":
            by_position[position].append((key, assignment))
    
    # Create CSV for each position
    for position in POSITION_NAMES:
        if position not in by_position:
            print(f"⚠ No data for position '{position}'")
            continue
        
        csv_file = output_dir / f"position_{position}.csv"
        player_games = by_position[position]
        
        print(f"\n📊 Exporting {len(player_games)} games for position '{position}'")
        
        # Collect all data for each player-game
        columns_data = []
        max_build_length = 0
        
        for (game_id, player_name), assignment in player_games:
            build_key = (game_id, player_name)
            build_info = builds_data.get(build_key)
            
            if not build_info:
                continue
            
            # Limit to first 100 builds
            build_order = build_info.get('buildOrder', [])[:100]
            
            # Normalize times: find first build with unique time (actual game start)
            # Skip builds that share the same timestamp (pre-game queue)
            if build_order:
                # Find the first build time that appears after initial queued builds
                first_build_time = build_order[0]['time']
                
                # Look for the first time that's different from the initial timestamp
                # This indicates when actual construction started
                for build in build_order:
                    if build['time'] > first_build_time:
                        # Use the initial queued time as reference
                        # This represents when player started giving commands (game start)
                        break
                
                normalized_build_order = []
                for build in build_order:
                    normalized_build = build.copy()
                    normalized_build['time'] = build['time'] - first_build_time
                    normalized_build_order.append(normalized_build)
                build_order = normalized_build_order
            
            avg_skill = calculate_average_skill(game_data, game_id)
            
            column_data = {
                'player_game_id': f"{player_name}_{game_id[:19]}",  # Truncate for readability
                'player_name': player_name,
                'game_id': game_id,
                'won_game': 'Win' if assignment['won_game'] else 'Loss',
                'player_skill': assignment['skill'],
                'avg_game_skill': avg_skill,
                'position': position,
                'distance_from_centroid': assignment['distance'],
                'faction': assignment.get('faction', 'Unknown'),
                'build_order': build_order
            }
            
            columns_data.append(column_data)
            max_build_length = max(max_build_length, len(build_order))
        
        if not columns_data:
            print(f"⚠ No build data for position '{position}'")
            continue
        
        # Sort columns by player skill (highest first)
        columns_data.sort(key=lambda x: x['player_skill'], reverse=True)
        
        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header row (column names)
            header = ['Metadata'] + [col['player_game_id'] for col in columns_data]
            writer.writerow(header)
            
            # Write metadata rows
            metadata_rows = [
                ('Player Name', [col['player_name'] for col in columns_data]),
                ('Game ID', [col['game_id'] for col in columns_data]),
                ('Result', [col['won_game'] for col in columns_data]),
                ('Player Skill', [f"{col['player_skill']:.2f}" for col in columns_data]),
                ('Avg Game Skill', [f"{col['avg_game_skill']:.2f}" for col in columns_data]),
                ('Position', [col['position'] for col in columns_data]),
                ('Distance from Centroid', [f"{col['distance_from_centroid']:.1f}" for col in columns_data]),
                ('Faction', [col['faction'] for col in columns_data]),
                ('---', ['---'] * len(columns_data)),  # Separator
            ]
            
            for label, values in metadata_rows:
                writer.writerow([label] + values)
            
            # Write build order rows with actual times
            for i in range(max_build_length):
                row = [f'Build {i+1}']
                for col in columns_data:
                    if i < len(col['build_order']):
                        build = col['build_order'][i]
                        # Format: "unitDisplayName (time)" with 1 decimal place
                        time_seconds = build['time']
                        row.append(f"{build['unitDisplayName']} ({time_seconds:.1f}s)")
                    else:
                        row.append('')
                writer.writerow(row)
        
        print(f"  ✓ Saved to {csv_file}")


def main():
    print("\n" + "=" * 60)
    print("Position Assignment and CSV Export")
    print("=" * 60 + "\n")
    
    # Setup paths
    base_dir = Path(__file__).parent.parent
    labels_file = base_dir / "POSITION-LABELING-LINKS-WITH-PLAYERS.txt"
    parsed_dir = base_dir / "data" / "parsed"
    output_dir = base_dir / "output" / "position_csvs"
    
    # Step 1: Parse manual labels
    print("📖 Step 1: Parsing manual position labels...")
    labeled_positions = parse_position_labels(labels_file)
    print(f"   Found {len(labeled_positions)} position types with labels")
    for pos, labels in labeled_positions.items():
        print(f"   - {pos}: {len(labels)} labeled examples")
    
    # Step 2: Load parsed data
    print("\n📂 Step 2: Loading parsed game data...")
    game_data, builds_data = load_parsed_data(parsed_dir)
    print(f"   Loaded {len(game_data)} games")
    print(f"   Loaded {len(builds_data)} build orders")
    
    # Step 3: Calculate centroids
    print("\n📍 Step 3: Calculating position centroids...")
    centroids = calculate_centroids(labeled_positions, game_data)
    print(f"   Calculated {len(centroids)} centroids")
    
    # Step 4: Assign all positions
    print("\n🎯 Step 4: Assigning positions to all players...")
    assignments = assign_all_positions(game_data, centroids, builds_data)
    print(f"   Assigned {len(assignments)} player positions")
    
    # Statistics
    position_counts = defaultdict(int)
    for assignment in assignments.values():
        position_counts[assignment['position']] += 1
    
    print("\n   Position distribution:")
    for pos in POSITION_NAMES:
        count = position_counts.get(pos, 0)
        print(f"   - {pos}: {count} players")
    
    # Step 5: Export CSVs
    print("\n📄 Step 5: Exporting CSV files per position...")
    export_position_csvs(assignments, builds_data, game_data, output_dir)
    
    print("\n" + "=" * 60)
    print("✅ Export Complete!")
    print("=" * 60)
    print(f"\nCSV files saved to: {output_dir}")
    print(f"Total positions exported: {len([p for p in POSITION_NAMES if (output_dir / f'position_{p}.csv').exists()])}")


if __name__ == "__main__":
    main()
