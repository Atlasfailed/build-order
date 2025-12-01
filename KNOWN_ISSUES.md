# Known Issues & Limitations

## Replay Downloader

### Issue: Failed to Download Replays

**Symptoms:**
- `Cannot connect to host replays.beyondallreason.dev`
- All downloads return 404 errors
- 9,940 failed downloads out of 9,940

**Root Cause:**
The BAR API provides replay metadata for thousands of games, but:
1. The actual `.sdfz` replay files are not always preserved
2. The CDN hosting may have connectivity issues
3. The replay file download URLs may have changed

**Workaround:**

### 1. Use Existing Replays (Recommended)

```bash
# Copy your existing test replays
find ../test -name "*.sdfz" -exec cp {} data/replays/ \;
```

### 2. Manual Download from BAR Website

1. Visit: https://www.beyondallreason.info/replays
2. Filter for:
   - Map: Supreme Isthmus v2.1
   - Preset: Team
   - No Bots
   - Ended Normally
3. Download replays manually
4. Place in `bar-position-analysis/data/replays/`

### 3. Use BAR Lobby Client

The Beyond All Reason game client has access to replays:
1. Open BAR game client
2. Go to Replays section
3. Browse and download Supreme Isthmus games
4. Copy from: `~/.spring/demos/` or your BAR installation demos folder
5. Place in `bar-position-analysis/data/replays/`

## All Win Rates Show 0%

**Symptoms:**
All positions show 0% win rate in analysis

**Root Cause:**
The test dataset (14 replays) contains games without recorded winners, likely because:
- Games were custom/practice matches
- Games ended abnormally
- Older replay format doesn't record winners

**Solution:**
Download replays from ranked/ladder games which will have proper win/loss data.

## Position Clustering Shows "Noise Points"

**Symptoms:**
Some players marked as "noise points" (unclustered)

**Root Cause:**
Players who spawn in unusual positions that don't match the common 8 spawn positions.

**Solution:**
This is normal - players can place anywhere. Adjust `position_clustering.eps` in config.json to be more permissive if needed.

## Build Order Data Empty

**Symptoms:**
`builds.jsonl` is empty or has very few entries

**Root Cause:**
- Need to include `STARTPOS` packet in parser
- Build commands not being captured

**Solution:**
Already fixed - ensure `STARTPOS` packet is included in `includePackets` array.

## Performance

### Large Dataset Processing

For datasets with 1000+ games:
- **Parsing**: ~10-20 seconds per replay
- **Clustering**: Scales well, < 1 minute for 10,000 positions
- **Visualization**: May be slow with 100+ archetypes

**Optimization Tips:**
- Process in batches
- Use `--from-step N` to resume from specific step
- Consider sampling for very large datasets

## Compatibility

### Python Version

Requires Python 3.8+. Tested on:
- ✅ Python 3.8
- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.13

### SciPy API Changes

If you see `'binom_test' has no attribute`:
- Update to use `binomtest()` instead of `binom_test()`
- Already fixed in current version

### Node.js Version

Requires Node.js 16+. The demo parser uses ES modules.

## Future Improvements

### Replay Availability

The replay download system could be improved by:
1. Finding alternative CDN sources
2. Caching available replay IDs
3. Using the BAR community's shared replay archives
4. Integrating with SpringFiles or other replay repositories

### Win Rate Accuracy

For better win rate analysis:
1. Filter for only ranked/ladder games
2. Ensure games have complete metadata
3. Validate winner information is present
4. Consider only games with duration > 10 minutes

## Getting Help

If you encounter other issues:

1. **Check logs**: Look in terminal output for specific errors
2. **Verify data**: Check that files in `data/` directories are not empty
3. **Test individual steps**: Use `./run-step.sh N` to run steps one at a time
4. **Try with sample data**: Use the 14 test replays to verify pipeline works

## Contributing

If you solve any of these issues or find workarounds, please share them!

