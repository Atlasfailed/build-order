#!/bin/bash
# BAR Position Analysis - Simplified Workflow
# Run the complete workflow from download to CSV export

set -e  # Exit on error

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  BAR Position Analysis                     ║${NC}"
echo -e "${BLUE}║  Supreme Isthmus Build Order Analysis     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Parse arguments
SKIP_DOWNLOAD=0
SKIP_PARSE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-download)
            SKIP_DOWNLOAD=1
            shift
            ;;
        --skip-parse)
            SKIP_PARSE=1
            shift
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            echo "Usage: $0 [--skip-download] [--skip-parse]"
            exit 1
            ;;
    esac
done

# Step 1: Download replays
if [ $SKIP_DOWNLOAD -eq 0 ]; then
    echo -e "${BLUE}Step 1: Downloading Replays${NC}"
    echo "────────────────────────────────────────"
    npm run download
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping download step${NC}"
    echo ""
fi

# Step 2: Parse demos
if [ $SKIP_PARSE -eq 0 ]; then
    echo -e "${BLUE}Step 2: Parsing Replays${NC}"
    echo "────────────────────────────────────────"
    npm run parse
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping parse step${NC}"
    echo ""
fi

# Step 3: Export CSVs
echo -e "${BLUE}Step 3: Generating Position CSVs${NC}"
echo "────────────────────────────────────────"
npm run export-csv
echo ""

# Complete
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Workflow Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Results:${NC}"
echo -e "  📊 Position CSVs: ${GREEN}output/position_csvs/${NC}"
echo -e "  🌐 Visualization: ${GREEN}pages/index.html${NC}"
echo ""
echo -e "${YELLOW}To view the visualization:${NC}"
echo -e "  ${GREEN}open pages/index.html${NC}"
echo ""
