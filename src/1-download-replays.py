#!/usr/bin/env python3
"""
BAR Replay Downloader
=====================

Downloads Supreme Isthmus replays from the BAR API with filtering for high-quality games.
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Set, List, Dict, Any, Optional
from datetime import datetime
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"

class ReplayDownloader:
    """High-performance replay downloader with filtering."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_config = config['api']
        self.filters = config['filters']
        self.paths = config['paths']
        
        # Setup paths
        self.replays_dir = SCRIPT_DIR / self.paths['replays']
        self.processed_ids_file = self.replays_dir / "processed_replay_ids.txt"
        self.failed_downloads_file = self.replays_dir / "failed_downloads.txt"
        
        # State
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_ids: Set[str] = set()
        self.failed_downloads: Set[str] = set()
        self.stats = {
            'total_found': 0,
            'already_downloaded': 0,
            'newly_downloaded': 0,
            'failed': 0,
            'filtered_out': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            limit=self.api_config['max_concurrent_downloads'] + 10,
            limit_per_host=self.api_config['max_concurrent_downloads'],
            keepalive_timeout=60,
            enable_cleanup_closed=True,
            ssl=False  # Disable SSL verification for faster downloads
        )
        timeout = aiohttp.ClientTimeout(total=self.api_config['timeout_seconds'])
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
        self.replays_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Replays directory: {self.replays_dir}")
    
    def load_processed_ids(self):
        """Load previously processed replay IDs."""
        if self.processed_ids_file.exists():
            with open(self.processed_ids_file, 'r') as f:
                self.processed_ids = {line.strip() for line in f if line.strip()}
            print(f"✓ Loaded {len(self.processed_ids)} previously downloaded replays")
        
        if self.failed_downloads_file.exists():
            with open(self.failed_downloads_file, 'r') as f:
                self.failed_downloads = {line.strip() for line in f if line.strip()}
            print(f"✓ Loaded {len(self.failed_downloads)} previously failed downloads")
    
    async def fetch_replay_list_page(self, page: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch a page of replay metadata from API."""
        url = f"{self.api_config['base_url']}{self.api_config['replays_endpoint']}"
        
        params = {
            'page': page,
            'limit': limit,
            'preset': self.filters['preset'],
            'hasBots': 'false' if not self.filters['has_bots'] else 'true',
            'endedNormally': 'true' if self.filters['ended_normally'] else 'false',
        }
        
        # Add map filter if map_name is specified
        if self.filters.get('map_name'):
            params['maps'] = self.filters['map_name']
        
        for attempt in range(self.api_config['max_retries']):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        replays = data.get('data', [])
                        return replays
                    elif response.status == 404:
                        return []  # No more pages
                    else:
                        print(f"⚠ Page {page} returned status {response.status}")
            except Exception as e:
                print(f"⚠ Attempt {attempt + 1} failed for page {page}: {e}")
                if attempt < self.api_config['max_retries'] - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        return []
    
    def filter_replay(self, replay_meta: Dict[str, Any]) -> bool:
        """Check if replay meets our filtering criteria."""
        # For now, be very permissive to see what we get
        # We can tighten this later once we understand the data structure
        
        # Basic checks that should work
        duration_ms = replay_meta.get('durationMs', 0)
        if duration_ms == 0:
            return False
        
        # Check minimum duration
        min_duration_ms = self.config['analysis'].get('min_game_duration_seconds', 300) * 1000
        if duration_ms < min_duration_ms:
            return False
        
        # Accept all replays that have a duration for now
        # We'll add more filters once we see the data structure
        return True
    
    async def download_replay_file(self, replay_id: str, file_name: str) -> bool:
        """Download a single .sdfz replay file."""
        if replay_id in self.processed_ids:
            return True  # Already downloaded
        
        file_path = self.replays_dir / file_name
        
        # Check if file already exists and is non-empty
        if file_path.exists() and file_path.stat().st_size > 0:
            await self.mark_as_processed(replay_id)
            return True
        
        # BAR replay files are served from replays.beyondallreason.dev
        # The path format is: /demos/{id}.sdfz
        url = f"https://replays.beyondallreason.dev/demos/{replay_id}.sdfz"
        
        for attempt in range(self.api_config['max_retries']):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        # Download the file
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(await response.read())
                        
                        await self.mark_as_processed(replay_id)
                        return True
                    elif response.status == 404:
                        # File not available, skip without retrying
                        if attempt == 0:
                            print(f"⚠ Replay {replay_id} not available (404)")
                        break
                    else:
                        print(f"⚠ Replay {replay_id} returned status {response.status}")
            except Exception as e:
                if attempt == self.api_config['max_retries'] - 1:
                    print(f"⚠ Failed to download {replay_id}: {e}")
                if attempt < self.api_config['max_retries'] - 1:
                    await asyncio.sleep(0.2 * (attempt + 1))
        
        # Mark as failed
        await self.mark_as_failed(replay_id)
        return False
    
    async def mark_as_processed(self, replay_id: str):
        """Mark a replay as successfully downloaded."""
        self.processed_ids.add(replay_id)
        async with aiofiles.open(self.processed_ids_file, 'a') as f:
            await f.write(f"{replay_id}\n")
    
    async def mark_as_failed(self, replay_id: str):
        """Mark a replay as failed to download."""
        self.failed_downloads.add(replay_id)
        async with aiofiles.open(self.failed_downloads_file, 'a') as f:
            await f.write(f"{replay_id}\n")
    
    async def collect_and_download_replays(self):
        """Main download pipeline."""
        self.stats['start_time'] = datetime.now()
        print("\n=== BAR Replay Downloader ===\n")
        
        # Setup
        self.setup_directories()
        self.load_processed_ids()
        
        # Collect replay metadata
        print(f"\n📥 Fetching replay list from API...")
        all_replays = []
        page = 1
        max_pages = 100  # Limit to avoid infinite loops
        
        while page <= max_pages:
            replays = await self.fetch_replay_list_page(page, limit=100)
            if not replays:
                print(f"✓ Reached end of results at page {page}")
                break
            
            all_replays.extend(replays)
            print(f"  Page {page}: Found {len(replays)} replays (Total: {len(all_replays)})")
            page += 1
            
            # Small delay between pages
            await asyncio.sleep(0.1)
        
        self.stats['total_found'] = len(all_replays)
        print(f"\n✓ Found {len(all_replays)} total replays")
        
        # Filter replays
        print(f"\n🔍 Filtering replays...")
        
        # Debug: Print first replay structure
        if all_replays:
            print(f"\n📋 Debug: Sample replay structure (first replay):")
            sample = all_replays[0]
            print(f"  Keys: {list(sample.keys())[:10]}")
            print(f"  preset: {sample.get('preset', 'N/A')}")
            print(f"  hasBots: {sample.get('hasBots', 'N/A')}")
            print(f"  gameEndedNormally: {sample.get('gameEndedNormally', 'N/A')}")
            print(f"  durationMs: {sample.get('durationMs', 'N/A')}")
            print(f"  Map: {sample.get('Map', {}).get('scriptName', 'N/A') if isinstance(sample.get('Map'), dict) else 'N/A'}")
            print()
        
        filtered_replays = []
        for replay in all_replays:
            if self.filter_replay(replay):
                filtered_replays.append(replay)
        
        self.stats['filtered_out'] = len(all_replays) - len(filtered_replays)
        print(f"✓ {len(filtered_replays)} replays meet quality criteria")
        print(f"  ({self.stats['filtered_out']} filtered out)")
        
        # Identify new replays to download
        new_replays = []
        for replay in filtered_replays:
            replay_id = str(replay.get('id'))
            if replay_id not in self.processed_ids:
                new_replays.append(replay)
            else:
                self.stats['already_downloaded'] += 1
        
        print(f"\n📦 Download status:")
        print(f"  Already downloaded: {self.stats['already_downloaded']}")
        print(f"  New to download: {len(new_replays)}")
        
        if not new_replays:
            print(f"\n✓ All quality replays already downloaded!")
            return
        
        # Download new replays
        print(f"\n⬇️  Downloading {len(new_replays)} new replays...")
        
        semaphore = asyncio.Semaphore(self.api_config['max_concurrent_downloads'])
        
        async def download_with_semaphore(replay):
            async with semaphore:
                replay_id = str(replay.get('id'))
                file_name = replay.get('fileName', f"{replay_id}.sdfz")
                success = await self.download_replay_file(replay_id, file_name)
                if success:
                    self.stats['newly_downloaded'] += 1
                else:
                    self.stats['failed'] += 1
                return success
        
        tasks = [download_with_semaphore(replay) for replay in new_replays]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Final statistics
        self.stats['end_time'] = datetime.now()
        self.print_final_report()
    
    def print_final_report(self):
        """Print final download statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print(f"\n=== Download Complete ===")
        print(f"Total replays found: {self.stats['total_found']:,}")
        print(f"Filtered out (low quality): {self.stats['filtered_out']:,}")
        print(f"Already downloaded: {self.stats['already_downloaded']:,}")
        print(f"Newly downloaded: {self.stats['newly_downloaded']:,}")
        print(f"Failed downloads: {self.stats['failed']:,}")
        print(f"Duration: {duration}")
        
        if self.stats['newly_downloaded'] > 0:
            rate = self.stats['newly_downloaded'] / duration.total_seconds()
            print(f"Download rate: {rate:.2f} replays/second")
        
        print(f"\n✓ Replays saved to: {self.replays_dir}")

async def main():
    """Main execution function."""
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Run downloader
    async with ReplayDownloader(config) as downloader:
        await downloader.collect_and_download_replays()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

