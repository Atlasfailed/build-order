#!/usr/bin/env python3
"""
Enrich parsed data with winner and faction information from replay JSON files.
This fixes the missing wonGame and faction data.
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent

def load_replay_jsons(replay_jsons_dir: Path) -> dict:
    """Load all replay JSON files into memory."""
    print(f"📖 Loading replay JSON files from {replay_jsons_dir.name}...")
    
    replay_data = {}
    json_files = list(replay_jsons_dir.glob("*.json"))
    failed = 0
    
    for i, json_file in enumerate(json_files):
        if i % 1000 == 0:
            print(f"  Loaded {i}/{len(json_files)} files...")
        
        try:
            with open(json_file, 'r') as f:
                content = f.read()
                # Try to fix common JSON errors (trailing commas before })
                content = content.replace(',}', '}').replace(',]', ']')
                data = json.loads(content)
                # Use the fileName from JSON to match with builds
                file_name = data.get('fileName', '')
                if file_name:
                    replay_data[file_name] = data
        except Exception as e:
            failed += 1
            continue
    
    print(f"✓ Loaded {len(replay_data):,} replay JSON files ({failed} failed)\n")
    return replay_data

def extract_winner_and_faction_data(replay_data: dict) -> dict:
    """
    Extract winner and faction information for each player.
    Returns: dict[fileName][player_name] = {wonGame: bool, faction: str}
    """
    enrichment_data = defaultdict(dict)
    
    for file_name, data in replay_data.items():
        # Get AllyTeams with winner info
        ally_teams = data.get('AllyTeams', [])
        winning_ally_team_ids = set()
        
        for ally_team in ally_teams:
            if ally_team.get('winningTeam'):
                winning_ally_team_ids.add(ally_team.get('id'))
        
        # Players are nested inside AllyTeams
        for ally_team in ally_teams:
            ally_team_id = ally_team.get('id')
            players = ally_team.get('Players', [])
            
            for player in players:
                player_name = player.get('name')
                faction = player.get('faction', 'Unknown')
                
                if player_name:
                    won_game = ally_team_id in winning_ally_team_ids
                    
                    enrichment_data[file_name][player_name] = {
                        'wonGame': won_game,
                        'faction': faction
                    }
    
    return enrichment_data

def enrich_builds_jsonl(builds_file: Path, enrichment_data: dict, output_file: Path, limit: int = None):
    """
    Read builds.jsonl and add wonGame and faction from replay JSONs.
    Optionally limit to first N entries for testing.
    """
    print(f"📝 Enriching {builds_file.name}...")
    
    enriched_count = 0
    not_found_count = 0
    processed_count = 0
    
    with open(builds_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if not line.strip():
                continue
            
            # Apply limit for testing
            if limit and processed_count >= limit:
                print(f"\n⚠️  Limit reached: Processing only first {limit} records for testing")
                break
            
            processed_count += 1
            if processed_count % 5000 == 0:
                print(f"  Progress: {processed_count:,} records ({enriched_count:,} enriched, {not_found_count:,} not found)")
                outfile.flush()  # Ensure data is written to disk
            
            build = json.loads(line)
            
            # Match by fileName
            file_name = build.get('fileName', '')
            player_name = build.get('playerName', '')
            
            # Look up in enrichment data
            if file_name in enrichment_data and player_name in enrichment_data[file_name]:
                # Update faction and wonGame
                build['faction'] = enrichment_data[file_name][player_name]['faction']
                build['wonGame'] = enrichment_data[file_name][player_name]['wonGame']
                enriched_count += 1
            else:
                not_found_count += 1
            
            # Write enriched record
            outfile.write(json.dumps(build) + '\n')
    
    print(f"\n✓ Enrichment complete!")
    print(f"  Total processed: {processed_count:,}")
    print(f"  Enriched: {enriched_count:,}")
    print(f"  Not found: {not_found_count:,}")
    print(f"  Output: {output_file}")

def main():
    # Test mode: limit to first 100 entries
    TEST_MODE = False
    TEST_LIMIT = 100 if TEST_MODE else None
    
    print("=" * 70)
    print("🔧 Enrich Builds Data with Winners and Factions")
    print("=" * 70)
    
    if TEST_MODE:
        print(f"\n⚠️  TEST MODE: Processing only first {TEST_LIMIT} entries\n")
    
    # Paths
    replay_jsons_dir = BASE_DIR / "data" / "replay_jsons_v2"
    parsed_dir = BASE_DIR / "data" / "parsed"
    builds_file = parsed_dir / "builds.jsonl"
    output_file = parsed_dir / "builds-enriched.jsonl"
    
    # Check files exist
    if not replay_jsons_dir.exists():
        print(f"❌ Error: {replay_jsons_dir} not found")
        sys.exit(1)
    
    if not builds_file.exists():
        print(f"❌ Error: {builds_file} not found")
        sys.exit(1)
    
    # Step 1: Load all replay JSON files
    replay_data = load_replay_jsons(replay_jsons_dir)
    
    # Step 2: Extract winner and faction data
    print("🔍 Extracting winner and faction information...")
    enrichment_data = extract_winner_and_faction_data(replay_data)
    print(f"✓ Found data for {len(enrichment_data):,} replays\n")
    
    # Step 3: Enrich builds.jsonl
    enrich_builds_jsonl(builds_file, enrichment_data, output_file, limit=TEST_LIMIT)
    
    print("\n" + "=" * 70)
    print("✅ Enrichment Complete!")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Review {output_file}")
    print(f"2. If looks good, replace builds.jsonl:")
    print(f"   mv {output_file} {builds_file}")
    print(f"3. Run position assignment and Parquet optimization")

if __name__ == "__main__":
    main()
