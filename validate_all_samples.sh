#!/bin/bash
# Validate all three sample models in CBECC 2025 and collect results

echo "=========================================="
echo "CIBD25 Sample Model Validation"
echo "=========================================="
echo ""

# Array of models to test
models=(
    "/Users/DavidM/Downloads/Warehouse_Test.cibd25:Warehouse"
    "/Users/DavidM/Downloads/Hotel_Test.cibd25:Hotel"
    "/Users/DavidM/Downloads/Office_Test.cibd25:Office"
)

for model_info in "${models[@]}"; do
    IFS=':' read -r path name <<< "$model_info"
    log_file="${path%.cibd25}_validation.log"

    echo "──────────────────────────────────────────"
    echo "Testing: $name"
    echo "File: $(basename "$path")"
    echo "──────────────────────────────────────────"

    # Run CBECC validation
    "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -nrp -b "$path" > "$log_file" 2>&1

    # Check results
    if grep -q "Model load successful" "$log_file" 2>/dev/null; then
        echo "✅ SUCCESS: Model loaded successfully"

        # Count errors if any
        error_count=$(grep -c "ERROR" "$log_file" 2>/dev/null || echo "0")
        if [ "$error_count" -gt 0 ]; then
            echo "   ⚠️  $error_count errors found (may be non-fatal)"
        else
            echo "   ✓ No errors reported"
        fi
    else
        echo "❌ FAILED: Model did not load"
        echo "   Check log: $log_file"
    fi

    echo ""
done

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Validation logs saved:"
for model_info in "${models[@]}"; do
    IFS=':' read -r path name <<< "$model_info"
    log_file="${path%.cibd25}_validation.log"
    echo "  - $log_file"
done
echo ""
