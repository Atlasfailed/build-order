#!/usr/bin/env python3
"""
Verify replay parameters from JSON files.
Extracts: id, startTime, numteams, mapname, average skill for all players
"""

import json
import os
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional


def extract_skill_value(skill_str: str) -> Optional[float]:
    """Extract numeric skill value from string like '[21.92]'"""
    if not skill_str:
        return None
    try:
        # Remove brackets and convert to float
        return float(skill_str.strip('[]'))
    except (ValueError, AttributeError):
        return None


def calculate_skill_stats(replay_data: Dict[str, Any]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Calculate average, min, and max skill across all players (from both ally teams)"""
    skills = []
    
    # Extract skills from all ally teams
    ally_teams = replay_data.get('AllyTeams', [])
    for ally_team in ally_teams:
        players = ally_team.get('Players', [])
        for player in players:
            skill_str = player.get('skill')
            skill_value = extract_skill_value(skill_str)
            if skill_value is not None:
                skills.append(skill_value)
    
    # Extract skills from spectators (if any)
    spectators = replay_data.get('Spectators', [])
    for spectator in spectators:
        skill_str = spectator.get('skill')
        skill_value = extract_skill_value(skill_str)
        if skill_value is not None:
            skills.append(skill_value)
    
    if not skills:
        return None, None, None
    
    return sum(skills) / len(skills), min(skills), max(skills)


def process_replay_file(file_path: Path) -> Dict[str, Any]:
    """Process a single replay JSON file and extract required parameters"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract required fields
    replay_id = data.get('id', '')
    start_time = data.get('startTime', '')
    
    # Get numteams from hostSettings
    host_settings = data.get('hostSettings', {})
    num_teams = host_settings.get('numteams', '')
    map_name = host_settings.get('mapname', '')
    
    # Calculate skill statistics
    avg_skill, min_skill, max_skill = calculate_skill_stats(data)
    
    return {
        'id': replay_id,
        'startTime': start_time,
        'numteams': num_teams,
        'mapname': map_name,
        'average_skill': avg_skill,
        'min_skill': min_skill,
        'max_skill': max_skill
    }


def main():
    """Main function to process all replay JSON files"""
    # Define paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data' / 'replay_jsons_v2'
    output_dir = script_dir.parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / 'replay_parameters.csv'
    
    # Check if data directory exists
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return
    
    # Get all JSON files (excluding download_metadata.json and other non-replay files)
    json_files = [f for f in data_dir.glob('*.json') 
                  if f.name != 'download_metadata.json' and not f.name.startswith('.')]
    
    print(f"Found {len(json_files)} replay JSON files to process")
    
    # Process all files
    results = []
    errors = []
    
    for i, json_file in enumerate(json_files, 1):
        if i % 100 == 0:
            print(f"Processing file {i}/{len(json_files)}...")
        
        try:
            result = process_replay_file(json_file)
            results.append(result)
        except Exception as e:
            error_msg = f"Error processing {json_file.name}: {str(e)}"
            errors.append(error_msg)
    
    # Sort results by average skill (highest to lowest)
    results.sort(key=lambda x: x['average_skill'] if x['average_skill'] is not None else -1, reverse=True)
    
    # Write results to CSV
    if results:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'startTime', 'numteams', 'mapname', 'average_skill', 'min_skill', 'max_skill']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        
        print(f"\n✓ Successfully processed {len(results)} replays")
        print(f"✓ Output saved to: {output_file}")
        
        # Print some statistics
        skills = [r['average_skill'] for r in results if r['average_skill'] is not None]
        if skills:
            print(f"\nSkill statistics:")
            print(f"  - Average skill across all replays: {sum(skills) / len(skills):.2f}")
            print(f"  - Min skill: {min(skills):.2f}")
            print(f"  - Max skill: {max(skills):.2f}")
            print(f"  - Replays with skill data: {len(skills)}/{len(results)}")
        
        # Print map distribution
        map_counts = {}
        for result in results:
            map_name = result['mapname']
            map_counts[map_name] = map_counts.get(map_name, 0) + 1
        
        print(f"\nTop 10 maps:")
        for map_name, count in sorted(map_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {map_name}: {count} games")
    
    if errors:
        print(f"\n⚠ Encountered {len(errors)} errors")
        error_file = output_dir / 'processing_errors.txt'
        with open(error_file, 'w') as f:
            f.write('\n'.join(errors))
        print(f"Error details saved to: {error_file}")


if __name__ == '__main__':
    main()
