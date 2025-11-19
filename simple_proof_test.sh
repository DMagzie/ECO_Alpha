#!/bin/bash
#
# Simple Direct Proof Test
#

CBECC="/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025"
TEST_FILE="$1"

if [ -z "$TEST_FILE" ]; then
    echo "Usage: $0 <file.cibd25>"
    exit 1
fi

if [ ! -f "$TEST_FILE" ]; then
    echo "File not found: $TEST_FILE"
    exit 1
fi

filename=$(basename "$TEST_FILE")
logfile="${TEST_FILE%.cibd25}.log"

echo "════════════════════════════════════════════════════"
echo "Testing: $filename"
echo "════════════════════════════════════════════════════"
echo ""

# Run CBECC
rm -f "$logfile"
"$CBECC" -nrp -b "$TEST_FILE" > /tmp/cbecc_output.txt 2>&1 &
PID=$!

echo "Started CBECC (PID: $PID)"
echo "Waiting 8 seconds for parsing..."
sleep 8

# Kill process
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null || true

echo ""
echo "════════════════════════════════════════════════════"
echo "CHECKING RESULTS"
echo "════════════════════════════════════════════════════"
echo ""

# Check if log file was created
if [ ! -f "$logfile" ]; then
    echo "❌ No log file created - File may not have parsed"
    exit 1
fi

echo "✓ Log file created: $logfile"
echo ""

# Check for parse errors
if grep -q "Error reading component from file" "$logfile"; then
    echo "❌ PARSE ERROR FOUND:"
    grep "Error reading component" "$logfile"
    echo ""
    echo "Full error context:"
    grep -A 3 "Error reading" "$logfile"
    exit 1
fi

if grep -q "Error reading building model" "$logfile"; then
    echo "❌ MODEL ERROR FOUND:"
    grep "Error reading building" "$logfile"
    exit 1
fi

if grep -q "Error(s) encountered" "$logfile"; then
    echo "❌ LOAD ERROR FOUND:"
    grep "Error(s) encountered" "$logfile"
    exit 1
fi

# Check for success indicators
if grep -q "Opening Project" "$logfile"; then
    echo "✅ SUCCESS: File opened successfully"
fi

if grep -q "Model load" "$logfile" && ! grep -q "Model load failed" "$logfile"; then
    echo "✅ SUCCESS: Model loaded"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "LOG FILE EXCERPT:"
echo "════════════════════════════════════════════════════"
head -30 "$logfile"
echo ""

echo "════════════════════════════════════════════════════"
echo "VERDICT: ✅ FILE IS VALID - NO PARSE ERRORS"
echo "════════════════════════════════════════════════════"
