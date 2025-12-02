# GitHub Pages Integration Guide

## File Structure for Website

Upload these files to your GitHub Pages repository:

```
data/
  optimized/
    index.parquet                    (584 KB) - Player metadata with position_id
    positions_metadata.parquet       (691 KB) - Spawn coordinates and dates
    lookup_players.parquet           (143 KB) - Player ID → name mapping
    lookup_replays.parquet           (88 KB)  - Replay ID → filename mapping
    lookup_units.parquet             (11 KB)  - Unit ID → name mapping
    lookup_positions.parquet         (1.8 KB) - Position ID → name mapping
    builds_by_position/
      builds_position_0_front-1.parquet   (6.4 MB)
      builds_position_1_front-2.parquet   (6.3 MB)
      builds_position_2_geo.parquet       (7.2 MB)
      builds_position_3_geo-sea.parquet   (12 MB)
      builds_position_4_air.parquet       (11 MB)
      builds_position_5_eco.parquet       (19 MB)  ⚠️ Largest
      builds_position_6_pond.parquet      (8.3 MB)
      builds_position_7_long-sea.parquet  (8.1 MB)
```

**Total size: ~81 MB** (down from original 3.88 GB JSONL)

## Loading Strategy

### Option 1: Load Only Selected Position (Recommended)
```javascript
// User selects a position from dropdown
const positionId = 0; // front-1

// Load only the data for that position
const [index, builds, lookups] = await Promise.all([
  loadParquet('data/optimized/index.parquet'),
  loadParquet(`data/optimized/builds_by_position/builds_position_${positionId}_front-1.parquet`),
  loadParquet('data/optimized/lookup_units.parquet'),
  loadParquet('data/optimized/lookup_positions.parquet')
]);

// Filter index for this position
const positionPlayers = index.filter(row => row.position_id === positionId);

// Now builds already contains only this position's build orders
```

### Option 2: Load Multiple Positions
```javascript
// User can multi-select positions
const selectedPositions = [0, 1, 2]; // front-1, front-2, geo

// Load builds for selected positions in parallel
const buildsArrays = await Promise.all(
  selectedPositions.map(id => 
    loadParquet(`data/optimized/builds_by_position/builds_position_${id}_*.parquet`)
  )
);

// Combine builds
const allBuilds = buildsArrays.flat();
```

### Option 3: Load All (Not Recommended)
If you need all positions, you can load all 8 files (~78 MB total):
```javascript
const allBuilds = await Promise.all(
  [0, 1, 2, 3, 4, 5, 6, 7].map(id => 
    loadParquet(`data/optimized/builds_by_position/builds_position_${id}_*.parquet`)
  )
).then(arrays => arrays.flat());
```

## Data Schema

### index.parquet
```typescript
{
  replay_id: number,           // Foreign key to lookup_replays
  player_id: number,           // Foreign key to lookup_players
  skill: number,               // OpenSkill rating
  rank: number | null,         // Chevron rank
  won_game: boolean,           // Did this player win?
  position_id: number,         // 0-7 (front-1, front-2, geo, geo-sea, air, eco, pond, long-sea)
  distance_from_centroid: number,  // How close to ideal position spawn
  faction: string              // 'arm', 'cor', 'leg', 'unk'
}
```

### builds_position_X.parquet
```typescript
{
  replay_id: number,           // Links to index.replay_id
  player_id: number,           // Links to index.player_id
  build_index: number,         // 0, 1, 2, ... (order in build queue)
  time: number,                // Game time in milliseconds (float32)
  unit_id: number              // Foreign key to lookup_units
}
```

### positions_metadata.parquet (Optional)
```typescript
{
  replay_id: number,
  player_id: number,
  spawn_x: number,             // Map coordinate (0-12288)
  spawn_z: number,             // Map coordinate (0-12288)
  game_date: string            // 'YYYY-MM-DD'
}
```

## Performance Tips

1. **Lazy Loading**: Only load position files when user selects that position
2. **Caching**: Cache loaded Parquet files in browser memory/localStorage
3. **Progressive Loading**: Show index first, load builds in background
4. **Filter Early**: Apply skill/player filters on index before loading builds
5. **Largest File**: Position 5 (eco) is 19 MB - consider loading indicator

## Migration from CSV

**Old approach** (using position CSVs):
- 8 CSV files, one per position
- Each CSV has full game data + build order
- Redundant metadata in every file

**New approach** (using Parquet):
- Normalized data: index + builds + lookups
- ~50x smaller than original
- Only load what you need
- Better compression and faster parsing

## Example: Full Integration

```javascript
import { parquetRead } from 'hyparquet';

// 1. Load lookups and index (always needed)
const [index, lookupUnits, lookupPositions] = await Promise.all([
  loadParquet('data/optimized/index.parquet'),
  loadParquet('data/optimized/lookup_units.parquet'),
  loadParquet('data/optimized/lookup_positions.parquet')
]);

// 2. User selects position from dropdown
const positionId = 2; // geo

// 3. Filter index for this position
const playersInPosition = index.filter(row => row.position_id === positionId);

// 4. Load builds for this position
const positionName = lookupPositions[positionId].position_name;
const builds = await loadParquet(
  `data/optimized/builds_by_position/builds_position_${positionId}_${positionName}.parquet`
);

// 5. Build tree visualization
const buildTree = createBuildTree(playersInPosition, builds, lookupUnits);
```

## File Size Breakdown by Position

| Position ID | Name      | Records    | Size   | % of Total |
|-------------|-----------|------------|--------|------------|
| 0           | front-1   | 3,262,400  | 6.4 MB | 8%         |
| 1           | front-2   | 3,092,001  | 6.3 MB | 8%         |
| 2           | geo       | 3,254,319  | 7.2 MB | 9%         |
| 3           | geo-sea   | 5,068,361  | 12 MB  | 15%        |
| 4           | air       | 5,697,942  | 11 MB  | 14%        |
| 5           | eco       | 9,798,937  | 19 MB  | 24% ⚠️     |
| 6           | pond      | 4,783,423  | 8.3 MB | 11%        |
| 7           | long-sea  | 3,814,364  | 8.1 MB | 10%        |

**Eco position** has the most build steps (complex economy builds), making it the largest file.

## Next Steps

1. Copy `output/optimized/` folder to your GitHub Pages repo
2. Update JavaScript to use new Parquet files instead of CSVs
3. Add position selector dropdown
4. Implement lazy loading for build files
5. Add loading indicators for larger files (eco position)
