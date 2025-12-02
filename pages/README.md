# Build Order Explorer - Parquet Version

## Overview

The website now uses optimized Parquet files instead of CSV files, providing:
- **83% smaller file sizes** (1.4-1.9 MB per position vs 6-19 MB)
- **Faster loading** with only the first 100 builds per player
- **Same functionality** as the CSV version

## File Structure

```
pages/
  index.html                    # Main website
  test-parquet.html             # Test page for Parquet loading
  data/
    optimized/
      index.parquet               (584 KB) - Player metadata
      lookup_players.parquet      (143 KB) - Player names
      lookup_units.parquet        (11 KB)  - Unit names
      lookup_positions.parquet    (1.8 KB) - Position names
      builds_by_position/
        builds_position_0_front-1.parquet   (1.9 MB)
        builds_position_1_front-2.parquet   (1.8 MB)
        builds_position_2_geo.parquet       (1.9 MB)
        builds_position_3_geo-sea.parquet   (1.7 MB)
        builds_position_4_air.parquet       (1.6 MB)
        builds_position_5_eco.parquet       (1.4 MB)
        builds_position_6_pond.parquet      (1.4 MB)
        builds_position_7_long-sea.parquet  (1.8 MB)
  js/
    build-tree.js               # Old CSV version (kept for reference)
    build-tree-parquet.js       # New Parquet version (active)
  css/
    styles.css
  images/
    logo.png
```

## Testing Locally

### Method 1: Python HTTP Server
```bash
cd pages
python3 -m http.server 8080
```

Then open: http://localhost:8080/index.html

### Method 2: Node.js HTTP Server
```bash
cd pages
npx http-server -p 8080
```

Then open: http://localhost:8080/index.html

### Method 3: VS Code Live Server
1. Install "Live Server" extension
2. Right-click `index.html`
3. Select "Open with Live Server"

## Deploying to GitHub Pages

### Option 1: Deploy from `pages` directory

1. Push to GitHub:
   ```bash
   git add pages/
   git commit -m "Add Parquet-based build tree website"
   git push
   ```

2. Configure GitHub Pages:
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: `master` (or `main`)
   - Folder: `/bar-position-analysis/pages`
   - Click Save

3. Your site will be at: `https://<username>.github.io/<repo>/`

### Option 2: Deploy to separate gh-pages branch

```bash
# From bar-position-analysis/pages directory
cd pages

# Create orphan branch
git checkout --orphan gh-pages
git rm -rf .
git clean -fdx

# Copy website files to root
cp -r ../pages/* .

# Commit and push
git add .
git commit -m "Deploy build tree website"
git push origin gh-pages

# Go back to main branch
git checkout master
```

Then configure GitHub Pages to use `gh-pages` branch.

## Data Constraints

- **Build limit**: First 100 builds per player (~7-14 minutes of gameplay)
- **Total players**: 79,695
- **Total games**: 4,985
- **Positions**: 8 (front-1, front-2, geo, geo-sea, air, eco, pond, long-sea)

## How It Works

1. **On page load**: Loads lookup tables (units, players, positions)
2. **User selects position**: Loads index.parquet + specific position builds
3. **Filtering**: Applies skill/player filters to index
4. **Tree building**: Groups builds by player, creates tree structure
5. **Rendering**: Displays interactive tree with counts and average skills

## Browser Compatibility

- **Chrome/Edge**: ✅ Full support
- **Firefox**: ✅ Full support
- **Safari**: ✅ Full support (ES6 modules required)
- **Mobile**: ✅ Responsive design

## Troubleshooting

### CORS Errors
If you see CORS errors when opening `index.html` directly:
- Use an HTTP server (see "Testing Locally")
- Don't open file:// URLs directly

### Parquet Loading Fails
1. Check browser console for errors
2. Verify files exist in `data/optimized/`
3. Test with `test-parquet.html` first

### Missing Data
If tree is empty:
- Check filters (clear them)
- Verify position has data
- Check console for JavaScript errors

## Maintenance

### Updating Data

1. Re-run the pipeline:
   ```bash
   cd bar-position-analysis
   python3 src/10-enrich-with-winners.py      # Enrich with winners/factions
   python3 src/8-optimize-to-parquet.py       # Create Parquet files
   python3 src/12-split-builds-limited.py     # Split by position (limited)
   ```

2. Copy new files:
   ```bash
   cp output/optimized/*.parquet pages/data/optimized/
   cp output/optimized/builds_by_position_limited/*.parquet pages/data/optimized/builds_by_position/
   ```

3. Test locally, then deploy

### Changing Build Limit

Edit `src/12-split-builds-limited.py`:
```python
BUILD_LIMIT = 100  # Change this number
```

Then re-run the split script.

## Performance

- **Initial load**: ~200 KB (lookups + index)
- **Per position**: ~1.7 MB average
- **Parse time**: <1 second on modern hardware
- **Total for all 8 positions**: ~13.5 MB

## Credits

- **Parquet library**: [hyparquet](https://github.com/hyparam/hyparquet)
- **Data source**: Beyond All Reason replay files
- **Position analysis**: Manual labeling + centroid calculation
