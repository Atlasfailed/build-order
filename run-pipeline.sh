#!/bin/bash
# BAR Position Analysis Pipeline
# Runs the complete analysis pipeline from download to visualization

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  BAR Position Analysis Pipeline           ║${NC}"
echo -e "${BLUE}║  Supreme Isthmus Build Order Analysis     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3${NC}"

# Check Node.js/npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm${NC}"

# Check if parent project is built
if [ ! -d "../dist" ]; then
    echo -e "${YELLOW}Building demo parser...${NC}"
    cd ..
    npm install
    npm run build
    cd "$SCRIPT_DIR"
fi
echo -e "${GREEN}✓ Demo parser built${NC}"

echo ""

# Parse command line arguments
SKIP_DOWNLOAD=0
SKIP_PARSE=0
START_STEP=1

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
        --from-step)
            START_STEP=$2
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--skip-download] [--skip-parse] [--from-step N]"
            exit 1
            ;;
    esac
done

# Step 1: Download replays
if [ $START_STEP -le 1 ] && [ $SKIP_DOWNLOAD -eq 0 ]; then
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 1: Downloading Replays${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    python3 src/1-download-replays.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Download failed${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping Step 1: Download Replays${NC}"
    echo ""
fi

# Step 2: Parse demos
if [ $START_STEP -le 2 ] && [ $SKIP_PARSE -eq 0 ]; then
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 2: Parsing Demos${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    cd ..
    npx ts-node bar-position-analysis/src/2-parse-demos.ts
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Parsing failed${NC}"
        exit 1
    fi
    cd "$SCRIPT_DIR"
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping Step 2: Parse Demos${NC}"
    echo ""
fi

# Step 3: Cluster positions
if [ $START_STEP -le 3 ]; then
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 3: Clustering Positions${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    python3 src/3-cluster-positions.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Position clustering failed${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping Step 3: Cluster Positions${NC}"
    echo ""
fi

# Step 4: Cluster build orders
if [ $START_STEP -le 4 ]; then
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 4: Clustering Build Orders${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    python3 src/4-cluster-builds.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Build order clustering failed${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping Step 4: Cluster Build Orders${NC}"
    echo ""
fi

# Step 5: Analyze success
if [ $START_STEP -le 5 ]; then
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 5: Analyzing Success Rates${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    python3 src/5-analyze-success.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Success analysis failed${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping Step 5: Analyze Success${NC}"
    echo ""
fi

# Step 6: Generate visualizations
if [ $START_STEP -le 6 ]; then
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 6: Generating Visualizations${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    python3 src/6-visualize.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Visualization failed${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}⊘ Skipping Step 6: Generate Visualizations${NC}"
    echo ""
fi

# Complete
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Pipeline Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Results:${NC}"
echo -e "  📊 Reports: ${GREEN}output/reports/${NC}"
echo -e "  🌐 Dashboard: ${GREEN}output/visualizations/index.html${NC}"
echo ""
echo -e "${YELLOW}To view the dashboard, open:${NC}"
echo -e "  ${GREEN}file://$(pwd)/output/visualizations/index.html${NC}"
echo ""

