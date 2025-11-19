#!/bin/bash
#
# Fix All CIBD25 Files - One Command Solution
#
# This script fixes all CIBD25 export files in Downloads folder
# and validates them automatically.
#
# Usage:
#   ./FIX_ALL_CIBD25.sh
#   ./FIX_ALL_CIBD25.sh ~/path/to/files
#

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     CIBD25 Comprehensive Fixer - Definitive Solution          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get directory to process (default: Downloads)
SOURCE_DIR="${1:-$HOME/Downloads}"
OUTPUT_DIR="$SOURCE_DIR/fixed_cibd25"

echo -e "${BLUE}Source Directory:${NC} $SOURCE_DIR"
echo -e "${BLUE}Output Directory:${NC} $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Find all cibd25 files
FILES=($(find "$SOURCE_DIR" -maxdepth 1 -name "*.cibd25" -type f))

if [ ${#FILES[@]} -eq 0 ]; then
    echo -e "${RED}No .cibd25 files found in $SOURCE_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Found ${#FILES[@]} files to process${NC}"
echo ""

# Process each file
SUCCESS=0
FAILED=0

for file in "${FILES[@]}"; do
    filename=$(basename "$file")
    output="$OUTPUT_DIR/${filename%.cibd25}_fixed.cibd25"

    echo -e "${BLUE}Processing:${NC} $filename"

    if python3 cibd25_validator_fixer.py "$file" "$output"; then
        ((SUCCESS++))
        echo -e "${GREEN}✅ Success${NC}"
    else
        ((FAILED++))
        echo -e "${RED}❌ Failed${NC}"
    fi
    echo ""
done

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      SUMMARY                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "Total Files:    ${#FILES[@]}"
echo -e "${GREEN}✅ Successful:  $SUCCESS${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ Failed:      $FAILED${NC}"
fi
echo ""
echo -e "${GREEN}Fixed files saved to:${NC} $OUTPUT_DIR"
echo ""

# Test one fixed file with CBECC (if available)
if [ -f "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" ]; then
    echo "Testing first fixed file with CBECC 2025..."
    FIRST_FIXED=$(ls "$OUTPUT_DIR"/*.cibd25 2>/dev/null | head -1)

    if [ -n "$FIRST_FIXED" ]; then
        echo -e "${BLUE}Testing:${NC} $(basename "$FIRST_FIXED")"
        timeout 30 "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b "$FIRST_FIXED" > /dev/null 2>&1 &
        PID=$!
        sleep 2

        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✅ CBECC started successfully${NC}"
            kill $PID 2>/dev/null || true
        else
            echo -e "${RED}❌ CBECC failed to start${NC}"
        fi
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "               🎉 All files processed! 🎉"
echo "═══════════════════════════════════════════════════════════════"
echo ""
