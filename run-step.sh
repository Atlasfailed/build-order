#!/bin/bash
# Run individual pipeline steps

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <step-number>"
    echo ""
    echo "Available steps:"
    echo "  1 - Download replays"
    echo "  2 - Parse demos"
    echo "  3 - Cluster positions"
    echo "  4 - Cluster build orders"
    echo "  5 - Analyze success rates"
    echo "  6 - Generate visualizations"
    exit 1
fi

STEP=$1

case $STEP in
    1)
        echo "Running Step 1: Download Replays"
        python3 src/1-download-replays.py
        ;;
    2)
        echo "Running Step 2: Parse Demos"
        cd ..
        npx ts-node bar-position-analysis/src/2-parse-demos.ts
        ;;
    3)
        echo "Running Step 3: Cluster Positions"
        python3 src/3-cluster-positions.py
        ;;
    4)
        echo "Running Step 4: Cluster Build Orders"
        python3 src/4-cluster-builds.py
        ;;
    5)
        echo "Running Step 5: Analyze Success Rates"
        python3 src/5-analyze-success.py
        ;;
    6)
        echo "Running Step 6: Generate Visualizations"
        python3 src/6-visualize.py
        ;;
    *)
        echo "Invalid step number: $STEP"
        echo "Must be between 1 and 6"
        exit 1
        ;;
esac

