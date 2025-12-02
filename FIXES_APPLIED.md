# Issues Fixed and Documentation

## Issues Identified and Resolved

### 1. ✅ Missing Faction Data in builds.jsonl
**Problem**: Faction field was not being saved in builds.jsonl
**Solution**: Added `faction: player.faction` to the build records in `2-parse-demos.ts`
**Status**: Fixed - needs re-parsing to apply

### 2. ✅ Faction Normalization 
**Problem**: Needed consistent 3-letter faction codes
**Solution**: Added `normalize_faction()` function in `8-optimize-to-parquet.py`
**Mapping**:
- Armada → arm
- Cortex → cor
- Legion → leg
- Unknown → unk

### 3. ⚠️  Win Rate Always 0%
**Problem**: `winningAllyTeamIds` is empty in all parsed replay files
**Root Cause**: The .sdfz replay files don't contain winner information, or the demo parser isn't extracting it
**Current Status**: All players show `wonGame: false`

**Potential Solutions**:
1. Check if newer replay format includes winner data
2. Use BAR API to fetch game outcomes
3. Download replay_jsons from API (includes winner data)
4. Infer winners from game duration and final unit counts

### 4. ✅ Position Assignment Documentation
**Created**: `src/9-position-assignment-docs.py`
**Contents**:
- Complete explanation of coordinate system
- How centroids are calculated
- Position assignment algorithm
- Faction mapping
- Win rate issue explanation
- File structure overview
- Optimization details

## To Apply Fixes

### Re-parse Replays with Faction Data:
```bash
cd /Users/gerthuybrechts/pyprojects/demo-parser
npx ts-node bar-position-analysis/src/2-parse-demos.ts
```

### Re-optimize to Parquet:
```bash
cd bar-position-analysis
python3 src/8-optimize-to-parquet.py
```

## Files Modified

1. **src/2-parse-demos.ts**
   - Added faction field to build records

2. **src/8-optimize-to-parquet.py**
   - Added `normalize_faction()` function
   - Faction normalized to 3-letter codes in index

3. **src/9-position-assignment-docs.py** (NEW)
   - Comprehensive documentation
   - Position assignment algorithm explained
   - Coordinate system details
   - Known issues documented

## Next Steps

1. **Fix Win Rate Data** (Priority: HIGH)
   - Option A: Check if demo parser can extract winners from different packet types
   - Option B: Use BAR API to get game outcomes
   - Option C: Match replay IDs with replay_jsons that have winner data

2. **Re-parse All Replays**
   - Apply faction fix
   - ~1-2 hours for 4,985 replays

3. **Run Position Assignment**
   - Need manual position labels first
   - Or run clustering to auto-detect positions

## Win Rate Data - Detailed Investigation Needed

The `demo.info.meta.winningAllyTeamIds` field is consistently empty. Need to:

1. Check BAR demo parser source code
2. Verify if .sdfz format includes game outcome
3. Consider alternative data sources:
   - BAR replay API: `https://api.bar-rts.com/replays/{id}`
   - Replay JSON files (already downloaded in data/replay_jsons_v2/)
   - Match parsed data with API data by replay ID

## Faction Distribution (After Fix)

Expected distribution after re-parsing:
- Armada (arm): ~50-60% (default/most popular)
- Cortex (cor): ~30-40%
- Legion (leg): ~5-10% (newer faction)
