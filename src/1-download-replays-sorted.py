#!/usr/bin/env python3
"""
BAR Replay Downloader - Sorted by Skill
=========================================

Downloads replays from highest average skill to lowest, using data from:
- replay_jsons_v2: For replay metadata (fileName, id)
- replay_parameters.csv: For sorted list by average skill

Keeps track of downloads to handle interruptions gracefully.
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
import csv
from pathlib import Path
from typing import Set, Dict, Any, Optional
from datetime import datetime
from urllib.parse import quote
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent
REPLAYS_DIR = SCRIPT_DIR / "data" / "replays"
JSON_DIR = SCRIPT_DIR / "data" / "replay_jsons_v2"
CSV_FILE = SCRIPT_DIR / "output" / "replay_parameters.csv"
DOWNLOADED_IDS_FILE = REPLAYS_DIR / "downloaded_replay_ids.txt"
FAILED_DOWNLOADS_FILE = REPLAYS_DIR / "failed_downloads.txt"

# Download settings
MAX_CONCURRENT_DOWNLOADS = 5
TIMEOUT_SECONDS = 300
MAX_RETRIES = 3

class SortedReplayDownloader:
    """Downloads replays sorted by average skill (highest first)."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.downloaded_ids: Set[str] = set()
        self.failed_ids: Set[str] = set()
        self.stats = {
            'total_in_csv': 0,
            'already_downloaded': 0,
            'newly_downloaded': 0,
            'failed': 0,
            'skipped_missing_json': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            limit=MAX_CONCURRENT_DOWNLOADS + 10,
            limit_per_host=MAX_CONCURRENT_DOWNLOADS,
            keepalive_timeout=60,
            enable_cleanup_closed=True,
            ssl=False
        )
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'BAR-Position-Analysis/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def setup_directories(self):
        """Create necessary directories."""
        REPLAYS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✓ Replays directory: {REPLAYS_DIR}")
    
    def load_tracking_files(self):
        """Load previously downloaded and failed replay IDs."""
        if DOWNLOADED_IDS_FILE.exists():
            with open(DOWNLOADED_IDS_FILE, 'r') as f:
                self.downloaded_ids = {line.strip() for line in f if line.strip()}
            print(f"✓ Loaded {len(self.downloaded_ids)} previously downloaded replays")
        
        if FAILED_DOWNLOADS_FILE.exists():
            with open(FAILED_DOWNLOADS_FILE, 'r') as f:
                self.failed_ids = {line.strip() for line in f if line.strip()}
            print(f"✓ Loaded {len(self.failed_ids)} previously failed downloads")
    
    def load_sorted_replay_list(self):
        """Load replay list from CSV, already sorted by average skill (high to low)."""
        replays = []
        
        with open(CSV_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                replay_id = row['id']
                replays.append({
                    'id': replay_id,
                    'average_skill': float(row['average_skill']),
                    'startTime': row['startTime'],
                    'mapname': row['mapname']
                })
        
        self.stats['total_in_csv'] = len(replays)
        print(f"✓ Loaded {len(replays)} replays from CSV (sorted by average skill)")
        
        if replays:
            print(f"  Highest skill: {replays[0]['average_skill']:.2f} (ID: {replays[0]['id']})")
            print(f"  Lowest skill: {replays[-1]['average_skill']:.2f} (ID: {replays[-1]['id']})")
        
        return replays
    
    def get_replay_metadata(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """Get replay metadata from JSON file."""
        json_path = JSON_DIR / f"{replay_id}.json"
        
        if not json_path.exists():
            return None
        
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Error reading JSON for {replay_id}: {e}")
            return None
    
    async def download_replay_file(self, replay_id: str, file_name: str) -> bool:
        """Download a single .sdfz replay file."""
        if replay_id in self.downloaded_ids:
            self.stats['already_downloaded'] += 1
            return True
        
        file_path = REPLAYS_DIR / file_name
        
        # Check if file already exists and is non-empty
        if file_path.exists() and file_path.stat().st_size > 0:
            await self.mark_as_downloaded(replay_id)
            self.stats['already_downloaded'] += 1
            return True
        
        # BAR replay files are served from OVH storage
        # URL encode the filename to handle spaces and special characters
        encoded_filename = quote(file_name)
        url = f"https://storage.uk.cloud.ovh.net/v1/AUTH_10286efc0d334efd917d476d7183232e/BAR/demos/{encoded_filename}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        # Download the file
                        content = await response.read()
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        file_size_mb = len(content) / (1024 * 1024)
                        await self.mark_as_downloaded(replay_id)
                        self.stats['newly_downloaded'] += 1
                        print(f"  ✓ Downloaded {file_name} ({file_size_mb:.2f} MB)")
                        return True
                    elif response.status == 404:
                        # File not available
                        if attempt == 0:
                            print(f"  ⚠ Replay {replay_id} not available (404)")
                        break
                    else:
                        print(f"  ⚠ Replay {replay_id} returned status {response.status}")
            except asyncio.TimeoutError:
                print(f"  ⚠ Timeout downloading {replay_id} (attempt {attempt + 1}/{MAX_RETRIES})")
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"  ⚠ Failed to download {replay_id}: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        # Mark as failed
        await self.mark_as_failed(replay_id)
        self.stats['failed'] += 1
        return False
    
    async def mark_as_downloaded(self, replay_id: str):
        """Mark a replay as successfully downloaded."""
        if replay_id not in self.downloaded_ids:
            self.downloaded_ids.add(replay_id)
            async with aiofiles.open(DOWNLOADED_IDS_FILE, 'a') as f:
                await f.write(f"{replay_id}\n")
    
    async def mark_as_failed(self, replay_id: str):
        """Mark a replay as failed to download."""
        if replay_id not in self.failed_ids:
            self.failed_ids.add(replay_id)
            async with aiofiles.open(FAILED_DOWNLOADS_FILE, 'a') as f:
                await f.write(f"{replay_id}\n")
    
    async def download_replays_sorted(self):
        """Main download pipeline - downloads replays sorted by skill."""
        self.stats['start_time'] = datetime.now()
        print("\n=== BAR Replay Downloader (Sorted by Skill) ===\n")
        
        # Setup
        self.setup_directories()
        self.load_tracking_files()
        
        # Load sorted replay list from CSV
        print(f"\n📥 Loading sorted replay list from CSV...")
        replays = self.load_sorted_replay_list()
        
        if not replays:
            print("❌ No replays found in CSV")
            return
        
        # Filter out already downloaded replays and check for JSON files
        print(f"\n🔍 Checking which replays need to be downloaded...")
        replays_to_download = []
        
        for replay in replays:
            replay_id = replay['id']
            
            # Skip if already downloaded
            if replay_id in self.downloaded_ids:
                self.stats['already_downloaded'] += 1
                continue
            
            # Skip if previously failed (can retry manually later)
            if replay_id in self.failed_ids:
                continue
            
            # Check if we have the JSON metadata
            metadata = self.get_replay_metadata(replay_id)
            if not metadata:
                self.stats['skipped_missing_json'] += 1
                continue
            
            # Add fileName to replay info
            replay['fileName'] = metadata.get('fileName', f"{replay_id}.sdfz")
            replays_to_download.append(replay)
        
        print(f"\n📦 Download status:")
        print(f"  Total replays in CSV: {self.stats['total_in_csv']}")
        print(f"  Already downloaded: {self.stats['already_downloaded']}")
        print(f"  Missing JSON metadata: {self.stats['skipped_missing_json']}")
        print(f"  Previously failed: {len(self.failed_ids)}")
        print(f"  Ready to download: {len(replays_to_download)}")
        
        if not replays_to_download:
            print(f"\n✓ All replays already downloaded!")
            return
        
        # Show skill range of replays to download
        if replays_to_download:
            skills = [r['average_skill'] for r in replays_to_download]
            print(f"\n📊 Skill range to download:")
            print(f"  Highest: {max(skills):.2f}")
            print(f"  Lowest: {min(skills):.2f}")
            print(f"  Average: {sum(skills)/len(skills):.2f}")
        
        # Download replays with concurrency control
        print(f"\n⬇️  Downloading {len(replays_to_download)} replays (from highest skill to lowest)...")
        print(f"  Concurrent downloads: {MAX_CONCURRENT_DOWNLOADS}")
        print()
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        
        async def download_with_semaphore(replay, index):
            async with semaphore:
                replay_id = replay['id']
                file_name = replay['fileName']
                skill = replay['average_skill']
                
                print(f"[{index+1}/{len(replays_to_download)}] Downloading (skill: {skill:.2f}): {file_name}")
                success = await self.download_replay_file(replay_id, file_name)
                return success
        
        # Download all replays
        tasks = [download_with_semaphore(replay, i) for i, replay in enumerate(replays_to_download)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Final statistics
        self.stats['end_time'] = datetime.now()
        self.print_final_report()
    
    def print_final_report(self):
        """Print final download statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print(f"\n=== Download Complete ===")
        print(f"Total replays in CSV: {self.stats['total_in_csv']:,}")
        print(f"Already downloaded: {self.stats['already_downloaded']:,}")
        print(f"Newly downloaded: {self.stats['newly_downloaded']:,}")
        print(f"Failed downloads: {self.stats['failed']:,}")
        print(f"Missing JSON files: {self.stats['skipped_missing_json']:,}")
        print(f"Duration: {duration}")
        
        if self.stats['newly_downloaded'] > 0:
            rate = self.stats['newly_downloaded'] / duration.total_seconds()
            print(f"Download rate: {rate:.2f} replays/second")
        
        total_downloaded = len(self.downloaded_ids)
        print(f"\n✓ Total replays now downloaded: {total_downloaded:,}")
        print(f"✓ Replays saved to: {REPLAYS_DIR}")

async def main():
    """Main execution function."""
    async with SortedReplayDownloader() as downloader:
        await downloader.download_replays_sorted()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
        print("   Progress has been saved. Run the script again to resume.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
