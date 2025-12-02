#!/usr/bin/env python3
"""
Remove JSON files from replay_jsons_v2 directory if their corresponding
.sdfz replay file already exists in the replays directory.
"""

import json
import os
from pathlib import Path


def main():
    """Main function to clean up duplicate JSON files"""
    # Define paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    json_dir = data_dir / 'replay_jsons_v2'
    replays_dir = data_dir / 'replays'
    
    # Check if directories exist
    if not json_dir.exists():
        print(f"Error: JSON directory not found: {json_dir}")
        return
    
    if not replays_dir.exists():
        print(f"Error: Replays directory not found: {replays_dir}")
        return
    
    # Get all existing .sdfz files in replays directory
    print(f"Scanning replays directory: {replays_dir}")
    existing_replays = set()
    for sdfz_file in replays_dir.glob('*.sdfz'):
        existing_replays.add(sdfz_file.name)
    
    print(f"Found {len(existing_replays)} .sdfz files in replays directory")
    
    # Get all JSON files
    json_files = [f for f in json_dir.glob('*.json') 
                  if f.name != 'download_metadata.json' and not f.name.startswith('.')]
    
    print(f"Found {len(json_files)} JSON files to check")
    
    # Track files to delete
    files_to_delete = []
    errors = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the fileName field
            file_name = data.get('fileName', '')
            
            if file_name and file_name in existing_replays:
                files_to_delete.append((json_file, file_name))
        
        except Exception as e:
            error_msg = f"Error processing {json_file.name}: {str(e)}"
            errors.append(error_msg)
    
    # Show what will be deleted and ask for confirmation
    if files_to_delete:
        print(f"\n{len(files_to_delete)} JSON files have corresponding .sdfz files already downloaded:")
        print("\nSample of files to be deleted (first 10):")
        for json_file, sdfz_name in files_to_delete[:10]:
            print(f"  - {json_file.name} -> {sdfz_name}")
        
        if len(files_to_delete) > 10:
            print(f"  ... and {len(files_to_delete) - 10} more")
        
        # Ask for confirmation
        response = input(f"\nDelete these {len(files_to_delete)} JSON files? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            deleted_count = 0
            for json_file, sdfz_name in files_to_delete:
                try:
                    json_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    error_msg = f"Error deleting {json_file.name}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
            
            print(f"\n✓ Successfully deleted {deleted_count} JSON files")
        else:
            print("\nDeletion cancelled")
    else:
        print("\nNo JSON files found with corresponding .sdfz files")
    
    if errors:
        print(f"\n⚠ Encountered {len(errors)} errors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")


if __name__ == '__main__':
    main()
