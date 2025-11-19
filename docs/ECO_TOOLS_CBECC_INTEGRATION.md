# ECO Tools + CBECC CLI Integration Guide

**Version:** 1.0
**Date:** November 13, 2025
**Status:** Production Ready
**Supported Versions:** CBECC 2022, CBECC 2025

---

## Overview

This document provides complete documentation for integrating ECO Tools with the California Building Energy Code Compliance (CBECC) software command-line interface for automated energy analysis and Title 24 compliance checking.

**What This Integration Enables:**
- Export building models from ECO Tools to CBECC-compatible formats
- Run CBECC energy analysis headlessly (no GUI interaction)
- Parse CBECC results and import back into ECO Tools
- Automate Title 24 compliance workflows
- Batch process multiple building models

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [CBECC CLI Capabilities](#cbecc-cli-capabilities)
3. [ECO Tools Export Workflow](#eco-tools-export-workflow)
4. [Running CBECC Analysis](#running-cbecc-analysis)
5. [Parsing CBECC Results](#parsing-cbecc-results)
6. [Complete Integration Examples](#complete-integration-examples)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)

---

## System Requirements

### Software Requirements

**Required:**
- Python 3.11+
- ECO Tools v7 (with modular import/export system)
- CBECC 2022 and/or CBECC 2025 installed

**CBECC Installation Paths:**
- **macOS:** `/Applications/CBECC 2022.app/` or `/Applications/CBECC 2025.app/`
- **Windows:** `C:\Program Files\CBECC\CBECC-Com-2022\` or similar

### Platform Support

| Platform | CBECC 2022 | CBECC 2025 | Headless Mode | Notes |
|----------|------------|------------|---------------|-------|
| **macOS** | ✅ | ✅ | ✅ | Full support with `-nrp -b` flags |
| **Windows** | ✅ | ✅ | ✅ | Separate CBECC-CLI.exe available |
| **Linux** | ❌ | ❌ | ❌ | CBECC requires Windows/macOS |

---

## CBECC CLI Capabilities

### Command-Line Flags

#### Known Working Flags

| Flag | Description | Required | Example |
|------|-------------|----------|---------|
| `-nrp` | Batch processing mode | Yes | `-nrp` |
| `-b <file>` | Input file path | Yes | `-b "building.cibd22x"` |

**Complete Command:**
```bash
"/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022" -nrp -b "building.cibd22x"
```

#### Flags That Don't Work Headlessly

| Flag | Behavior | Issue |
|------|----------|-------|
| `-h` | Launches GUI dialog | Not suitable for automation |
| `--help` | Launches GUI dialog | Not suitable for automation |
| (no flags) | Opens GUI application | Requires user interaction |

### Headless Operation

**✅ Confirmed Headless:**
- CBECC runs completely without GUI when using `-nrp -b` flags
- No user interaction required
- Suitable for subprocess/automation
- Works on macOS and Windows

**Output Behavior:**
- Creates `.log` file in same directory as input file
- Log contains analysis results and any errors
- Exit code indicates success (0) or failure (non-zero)
- No stdout/stderr output (all output to log file)

### Subprocess Compatibility

**✅ Can Run as Subprocess:**
```python
import subprocess

result = subprocess.run([
    "/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022",
    "-nrp",
    "-b",
    "input.cibd22x"
], timeout=300)  # 5 minute timeout

print(f"Exit code: {result.returncode}")
```

---

## ECO Tools Export Workflow

### Step 1: Import Building Model

ECO Tools can import from multiple formats and convert to CBECC formats:

```python
from eco_tools.translators.cibd22x import CIBD22XImporter
from eco_tools.translators.hbjson import HBJSONImporter

# Option A: Import from existing CIBD22X
importer = CIBD22XImporter()
internal = importer.import_file("original_building.cibd22x")

# Option B: Import from Honeybee JSON
hb_importer = HBJSONImporter()
internal = hb_importer.import_file("building.hbjson")
```

### Step 2: Export to CBECC Format

ECO Tools supports export to all CBECC formats:

#### Export to CIBD22 (Title 24 2022 Text Format)

```python
from eco_tools.translators.cibd22 import CIBD22Exporter

exporter = CIBD22Exporter()
exporter.export(internal, "building_2022.cibd22")
```

**Metadata Automatically Set:**
- `RulesetFilename: "T24N_2022.bin"`
- `SoftwareVersion: "CBECC 2022.3.1 (1343)"`
- `BldgEngyModelVersion: 16`

#### Export to CIBD22X (Title 24 2022 XML Format)

```python
from eco_tools.translators.cibd22x.exporter import CIBD22XExporter

exporter = CIBD22XExporter()
exporter.export_to_file(internal, "building_2022.xml")
```

**When to Use XML vs Text:**
- **Text (.cibd22):** Smaller files, easier to diff, human-readable
- **XML (.cibd22x):** Better for programmatic parsing, official CBECC format

#### Export to CIBD25 (Title 24 2025 Text Format)

```python
from eco_tools.translators.cibd25 import CIBD25Exporter

exporter = CIBD25Exporter()
exporter.export(internal, "building_2025.cibd25")
```

**Metadata Automatically Set:**
- `RulesetFilename: "T24_2025.bin"`
- `SoftwareVersion: "CBECC 2025.2.0 (1390)"`
- `BldgEngyModelVersion: 17`

### Step 3: Verify Export

```python
from pathlib import Path

output_file = Path("building_2022.cibd22")

# Check file exists and has content
if output_file.exists():
    file_size = output_file.stat().st_size
    print(f"✓ Export successful: {file_size:,} bytes")

    # Verify it's a valid CBECC file
    with open(output_file, 'r') as f:
        first_line = f.readline()
        if 'RulesetFilename' in first_line:
            print("✓ Valid CBECC format detected")
else:
    print("✗ Export failed - file not created")
```

---

## Running CBECC Analysis

### Basic Subprocess Execution

```python
import subprocess
from pathlib import Path

def run_cbecc_analysis(cbecc_version, input_file, timeout=300):
    """
    Run CBECC analysis on a building model file.

    Args:
        cbecc_version: "2022" or "2025"
        input_file: Path to CIBD22/CIBD22X/CIBD25 file
        timeout: Maximum execution time in seconds (default: 5 minutes)

    Returns:
        dict with 'success', 'exit_code', 'log_file', and 'duration'
    """
    import time

    # Determine CBECC executable path
    if cbecc_version == "2022":
        cbecc_path = "/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022"
    elif cbecc_version == "2025":
        cbecc_path = "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025"
    else:
        raise ValueError(f"Unknown CBECC version: {cbecc_version}")

    # Check CBECC exists
    if not Path(cbecc_path).exists():
        raise FileNotFoundError(f"CBECC not found at: {cbecc_path}")

    # Check input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Prepare log file path
    log_file = input_path.with_suffix('.log')

    # Remove old log file if exists
    if log_file.exists():
        log_file.unlink()

    print(f"Running CBECC {cbecc_version} analysis...")
    print(f"  Input: {input_path}")
    print(f"  Log: {log_file}")

    # Run CBECC
    start_time = time.time()

    try:
        result = subprocess.run(
            [cbecc_path, "-nrp", "-b", str(input_path)],
            timeout=timeout,
            capture_output=True,
            text=True
        )

        duration = time.time() - start_time

        # Check if log file was created
        if not log_file.exists():
            return {
                'success': False,
                'exit_code': result.returncode,
                'log_file': None,
                'duration': duration,
                'error': 'CBECC did not create log file'
            }

        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'log_file': str(log_file),
            'duration': duration
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'exit_code': -1,
            'log_file': str(log_file) if log_file.exists() else None,
            'duration': timeout,
            'error': f'Analysis timed out after {timeout} seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'exit_code': -1,
            'log_file': None,
            'duration': time.time() - start_time,
            'error': str(e)
        }


# Example usage
result = run_cbecc_analysis("2022", "building.cibd22x")

if result['success']:
    print(f"✓ Analysis complete in {result['duration']:.1f}s")
    print(f"  Log: {result['log_file']}")
else:
    print(f"✗ Analysis failed: {result.get('error', 'Unknown error')}")
```

### Platform-Specific Paths

```python
import platform
from pathlib import Path

def get_cbecc_path(version):
    """Get CBECC executable path for current platform."""

    system = platform.system()

    if system == "Darwin":  # macOS
        return f"/Applications/CBECC {version}.app/Contents/MacOS/CBECC {version}"

    elif system == "Windows":
        # Try common installation paths
        paths = [
            f"C:\\Program Files\\CBECC\\CBECC-Com-{version}\\CBECC-Com.exe",
            f"C:\\Program Files (x86)\\CBECC\\CBECC-Com-{version}\\CBECC-Com.exe",
            f"C:\\CBECC\\CBECC {version}\\CBECC.exe"
        ]

        for path in paths:
            if Path(path).exists():
                return path

        raise FileNotFoundError(f"CBECC {version} not found in standard Windows locations")

    else:
        raise OSError(f"Unsupported platform: {system}")
```

### Monitoring Long-Running Analysis

```python
import subprocess
import time
from pathlib import Path

def run_cbecc_with_monitoring(cbecc_version, input_file, timeout=600):
    """
    Run CBECC with live log monitoring.

    Monitors log file growth and provides progress updates.
    """
    cbecc_path = get_cbecc_path(cbecc_version)
    input_path = Path(input_file)
    log_file = input_path.with_suffix('.log')

    # Remove old log
    if log_file.exists():
        log_file.unlink()

    print(f"Starting CBECC {cbecc_version} analysis...")

    # Start CBECC process
    process = subprocess.Popen(
        [cbecc_path, "-nrp", "-b", str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    start_time = time.time()
    last_log_size = 0

    # Monitor process
    while process.poll() is None:
        elapsed = time.time() - start_time

        # Check timeout
        if elapsed > timeout:
            process.kill()
            return {
                'success': False,
                'error': f'Timeout after {timeout}s',
                'duration': elapsed
            }

        # Check log file growth
        if log_file.exists():
            log_size = log_file.stat().st_size
            if log_size > last_log_size:
                print(f"  Progress: {log_size:,} bytes written ({elapsed:.1f}s elapsed)")
                last_log_size = log_size

        time.sleep(2)  # Check every 2 seconds

    duration = time.time() - start_time
    exit_code = process.returncode

    print(f"CBECC process completed in {duration:.1f}s (exit code: {exit_code})")

    return {
        'success': exit_code == 0,
        'exit_code': exit_code,
        'log_file': str(log_file) if log_file.exists() else None,
        'duration': duration
    }
```

---

## Parsing CBECC Results

### Basic Log File Parsing

```python
def parse_cbecc_log(log_file):
    """
    Parse CBECC log file for results and errors.

    Returns:
        dict with 'success', 'errors', 'warnings', and 'results'
    """
    from pathlib import Path

    log_path = Path(log_file)

    if not log_path.exists():
        return {
            'success': False,
            'errors': ['Log file not found'],
            'warnings': [],
            'results': {}
        }

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    errors = []
    warnings = []
    results = {}

    # Parse for common error patterns
    if 'Error' in content or 'ERROR' in content:
        for line in content.split('\n'):
            if 'error' in line.lower():
                errors.append(line.strip())

    # Parse for warnings
    if 'Warning' in content or 'WARNING' in content:
        for line in content.split('\n'):
            if 'warning' in line.lower():
                warnings.append(line.strip())

    # Check for successful completion
    success = len(errors) == 0 and (
        'Analysis complete' in content or
        'Compliance analysis completed' in content or
        'passed' in content.lower()
    )

    # Extract key results (customize based on your needs)
    results = {
        'log_size': log_path.stat().st_size,
        'lines': len(content.split('\n')),
        'has_errors': len(errors) > 0,
        'has_warnings': len(warnings) > 0
    }

    return {
        'success': success,
        'errors': errors,
        'warnings': warnings,
        'results': results,
        'raw_content': content
    }


# Example usage
log_result = parse_cbecc_log("building.log")

if log_result['success']:
    print("✓ CBECC analysis successful")
    if log_result['warnings']:
        print(f"  ⚠️  {len(log_result['warnings'])} warnings")
else:
    print("✗ CBECC analysis failed")
    for error in log_result['errors'][:5]:  # Show first 5 errors
        print(f"  • {error}")
```

### Advanced Result Extraction

```python
import re

def extract_energy_metrics(log_file):
    """
    Extract energy consumption metrics from CBECC log.

    Returns:
        dict with energy consumption values
    """
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    metrics = {}

    # Pattern examples (customize based on actual CBECC output)
    patterns = {
        'total_energy': r'Total Energy.*?(\d+\.?\d*)\s*kWh',
        'eui': r'EUI.*?(\d+\.?\d*)\s*kBtu/sf',
        'tdc': r'TDV.*?(\d+\.?\d*)',
        'compliance_margin': r'Compliance Margin.*?(\d+\.?\d*)%?',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                metrics[key] = float(match.group(1))
            except (ValueError, IndexError):
                metrics[key] = None

    return metrics


# Example usage
metrics = extract_energy_metrics("building.log")
print(f"Energy Use Intensity: {metrics.get('eui', 'N/A')} kBtu/sf")
print(f"Total Energy: {metrics.get('total_energy', 'N/A')} kWh")
```

### Compliance Status Detection

```python
def check_compliance_status(log_file):
    """
    Determine if building passes Title 24 compliance.

    Returns:
        dict with 'compliant', 'margin', and 'details'
    """
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read().lower()

    # Look for compliance indicators
    passed_keywords = [
        'compliance achieved',
        'building complies',
        'passed',
        'meets requirements'
    ]

    failed_keywords = [
        'compliance not achieved',
        'does not comply',
        'failed',
        'does not meet requirements'
    ]

    compliant = None
    for keyword in passed_keywords:
        if keyword in content:
            compliant = True
            break

    if compliant is None:
        for keyword in failed_keywords:
            if keyword in content:
                compliant = False
                break

    # Extract margin if available
    margin_match = re.search(r'margin.*?(\d+\.?\d*)%?', content)
    margin = float(margin_match.group(1)) if margin_match else None

    return {
        'compliant': compliant,
        'margin': margin,
        'confidence': 'high' if compliant is not None else 'unknown',
        'raw_indicators': {
            'passed_found': any(kw in content for kw in passed_keywords),
            'failed_found': any(kw in content for kw in failed_keywords)
        }
    }


# Example usage
compliance = check_compliance_status("building.log")

if compliance['compliant']:
    print(f"✓ Building COMPLIES with Title 24")
    if compliance['margin']:
        print(f"  Margin: {compliance['margin']}%")
elif compliance['compliant'] is False:
    print(f"✗ Building DOES NOT COMPLY with Title 24")
else:
    print("⚠️  Compliance status unknown - check log manually")
```

---

## Complete Integration Examples

### Example 1: Single Building Analysis Workflow

```python
#!/usr/bin/env python3
"""
Complete workflow: Import HBJSON → Export CIBD25 → Run CBECC 2025 → Parse Results
"""

from eco_tools.translators.hbjson import HBJSONImporter
from eco_tools.translators.cibd25 import CIBD25Exporter
from pathlib import Path
import subprocess

def analyze_building_complete(hbjson_file, output_dir):
    """
    Complete building energy analysis workflow.

    Steps:
    1. Import Honeybee JSON model
    2. Export to CIBD25 format
    3. Run CBECC 2025 analysis
    4. Parse and report results
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Import
    print("Step 1: Importing Honeybee JSON...")
    importer = HBJSONImporter()
    internal = importer.import_file(hbjson_file)
    print(f"  ✓ Loaded: {len(internal.zones)} zones, {len(internal.surfaces)} surfaces")

    # Step 2: Export to CIBD25
    print("\nStep 2: Exporting to CIBD25...")
    cibd25_file = output_dir / "building_analysis.cibd25"
    exporter = CIBD25Exporter()
    exporter.export(internal, str(cibd25_file))
    print(f"  ✓ Exported: {cibd25_file}")
    print(f"  File size: {cibd25_file.stat().st_size:,} bytes")

    # Step 3: Run CBECC 2025
    print("\nStep 3: Running CBECC 2025 analysis...")
    result = run_cbecc_analysis("2025", str(cibd25_file), timeout=600)

    if not result['success']:
        print(f"  ✗ Analysis failed: {result.get('error', 'Unknown error')}")
        return result

    print(f"  ✓ Analysis complete in {result['duration']:.1f}s")

    # Step 4: Parse results
    print("\nStep 4: Parsing results...")
    log_result = parse_cbecc_log(result['log_file'])

    if log_result['success']:
        print("  ✓ CBECC analysis successful")
    else:
        print("  ✗ CBECC reported errors:")
        for error in log_result['errors'][:3]:
            print(f"    • {error}")

    # Step 5: Check compliance
    compliance = check_compliance_status(result['log_file'])

    print("\nCompliance Status:")
    if compliance['compliant']:
        print("  ✓ Building COMPLIES with Title 24 2025")
    elif compliance['compliant'] is False:
        print("  ✗ Building DOES NOT COMPLY with Title 24 2025")
    else:
        print("  ⚠️  Compliance status could not be determined")

    # Step 6: Extract metrics
    metrics = extract_energy_metrics(result['log_file'])

    if metrics:
        print("\nEnergy Metrics:")
        for key, value in metrics.items():
            if value is not None:
                print(f"  {key}: {value}")

    return {
        'zones': len(internal.zones),
        'surfaces': len(internal.surfaces),
        'cibd25_file': str(cibd25_file),
        'log_file': result['log_file'],
        'success': result['success'],
        'compliant': compliance['compliant'],
        'metrics': metrics
    }


# Run analysis
if __name__ == '__main__':
    result = analyze_building_complete(
        hbjson_file="my_building.hbjson",
        output_dir="analysis_output"
    )

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"CIBD25 File: {result['cibd25_file']}")
    print(f"Log File: {result['log_file']}")
    print(f"Compliant: {result['compliant']}")
```

### Example 2: Batch Processing Multiple Buildings

```python
#!/usr/bin/env python3
"""
Batch process multiple buildings through CBECC analysis.
"""

from pathlib import Path
import json
from concurrent.futures import ProcessPoolExecutor, as_completed

def process_single_building(cibd_file, cbecc_version):
    """Process a single building file."""
    try:
        result = run_cbecc_analysis(cbecc_version, cibd_file)

        if result['success']:
            log_result = parse_cbecc_log(result['log_file'])
            compliance = check_compliance_status(result['log_file'])

            return {
                'file': str(cibd_file),
                'success': True,
                'compliant': compliance['compliant'],
                'duration': result['duration'],
                'errors': log_result['errors'],
                'warnings': log_result['warnings']
            }
        else:
            return {
                'file': str(cibd_file),
                'success': False,
                'error': result.get('error', 'Unknown error')
            }

    except Exception as e:
        return {
            'file': str(cibd_file),
            'success': False,
            'error': str(e)
        }


def batch_process_buildings(input_dir, cbecc_version, max_workers=4):
    """
    Process all CIBD files in a directory.

    Args:
        input_dir: Directory containing CIBD files
        cbecc_version: "2022" or "2025"
        max_workers: Number of parallel processes
    """
    input_path = Path(input_dir)

    # Find all CIBD files
    cibd_files = list(input_path.glob("*.cibd22")) + \
                 list(input_path.glob("*.cibd22x")) + \
                 list(input_path.glob("*.cibd25"))

    print(f"Found {len(cibd_files)} files to process")
    print(f"Using CBECC {cbecc_version} with {max_workers} workers\n")

    results = []

    # Process in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        futures = {
            executor.submit(process_single_building, f, cbecc_version): f
            for f in cibd_files
        }

        # Collect results as they complete
        for future in as_completed(futures):
            file = futures[future]
            try:
                result = future.result()
                results.append(result)

                status = "✓" if result['success'] else "✗"
                print(f"{status} {Path(result['file']).name}")

            except Exception as e:
                print(f"✗ {file.name}: {e}")
                results.append({
                    'file': str(file),
                    'success': False,
                    'error': str(e)
                })

    # Summary
    print("\n" + "="*80)
    print("BATCH PROCESSING COMPLETE")
    print("="*80)

    total = len(results)
    successful = sum(1 for r in results if r['success'])
    compliant = sum(1 for r in results if r.get('compliant'))

    print(f"Total files: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Compliant: {compliant}")

    # Save results to JSON
    output_file = input_path / f"batch_results_{cbecc_version}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return results


# Example usage
if __name__ == '__main__':
    batch_process_buildings(
        input_dir="buildings_to_analyze",
        cbecc_version="2025",
        max_workers=4
    )
```

### Example 3: GUI Integration

```python
#!/usr/bin/env python3
"""
Streamlit GUI for CBECC analysis.
"""

import streamlit as st
from pathlib import Path

def run_analysis_page():
    """Streamlit page for running CBECC analysis."""

    st.title("CBECC Energy Analysis")

    # Version selection
    cbecc_version = st.selectbox(
        "CBECC Version",
        ["2022", "2025"]
    )

    # File upload
    uploaded_file = st.file_uploader(
        "Upload Building Model",
        type=["cibd22", "cibd22x", "cibd25", "hbjson"]
    )

    if uploaded_file is not None:
        # Save uploaded file
        input_file = Path("temp") / uploaded_file.name
        input_file.parent.mkdir(exist_ok=True)

        with open(input_file, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Uploaded: {uploaded_file.name}")

        # Run analysis button
        if st.button("Run CBECC Analysis"):
            with st.spinner(f"Running CBECC {cbecc_version} analysis..."):

                # Convert to appropriate format if needed
                if uploaded_file.name.endswith('.hbjson'):
                    st.info("Converting HBJSON to CIBD25...")
                    from eco_tools.translators.hbjson import HBJSONImporter
                    from eco_tools.translators.cibd25 import CIBD25Exporter

                    importer = HBJSONImporter()
                    internal = importer.import_file(str(input_file))

                    cibd_file = input_file.with_suffix('.cibd25')
                    exporter = CIBD25Exporter()
                    exporter.export(internal, str(cibd_file))

                    input_file = cibd_file

                # Run CBECC
                result = run_cbecc_analysis(cbecc_version, str(input_file))

                if result['success']:
                    st.success(f"✓ Analysis complete in {result['duration']:.1f}s")

                    # Parse results
                    log_result = parse_cbecc_log(result['log_file'])
                    compliance = check_compliance_status(result['log_file'])

                    # Display compliance status
                    if compliance['compliant']:
                        st.success("✓ Building COMPLIES with Title 24")
                    elif compliance['compliant'] is False:
                        st.error("✗ Building DOES NOT COMPLY with Title 24")
                    else:
                        st.warning("⚠️ Compliance status unknown")

                    # Show errors/warnings
                    if log_result['errors']:
                        st.error("Errors:")
                        for error in log_result['errors']:
                            st.text(f"• {error}")

                    if log_result['warnings']:
                        st.warning(f"{len(log_result['warnings'])} warnings found")

                    # Download log file
                    with open(result['log_file'], 'r') as f:
                        log_content = f.read()

                    st.download_button(
                        "Download Log File",
                        log_content,
                        file_name=Path(result['log_file']).name,
                        mime="text/plain"
                    )

                else:
                    st.error(f"✗ Analysis failed: {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    run_analysis_page()
```

---

## Error Handling

### Common Errors and Solutions

#### Error 1: CBECC Executable Not Found

**Error Message:**
```
FileNotFoundError: CBECC not found at: /Applications/CBECC 2025.app/...
```

**Solution:**
```python
from pathlib import Path

def find_cbecc_executable(version):
    """Find CBECC executable with fallback paths."""

    possible_paths = [
        f"/Applications/CBECC {version}.app/Contents/MacOS/CBECC {version}",
        f"/Applications/CBECC-Com {version}.app/Contents/MacOS/CBECC-Com",
        f"C:\\Program Files\\CBECC\\CBECC-Com-{version}\\CBECC-Com.exe",
    ]

    for path in possible_paths:
        if Path(path).exists():
            return path

    raise FileNotFoundError(
        f"CBECC {version} not found. Please install CBECC {version} first."
    )
```

#### Error 2: Log File Not Created

**Error Message:**
```
CBECC did not create log file
```

**Solution:**
```python
# Check file permissions on output directory
output_dir = Path(input_file).parent

if not os.access(output_dir, os.W_OK):
    raise PermissionError(f"Cannot write to directory: {output_dir}")

# Ensure input file path has no special characters
# CBECC may have issues with Unicode characters in paths
```

#### Error 3: Analysis Timeout

**Error Message:**
```
Analysis timed out after 300 seconds
```

**Solution:**
```python
# Increase timeout for large buildings
result = run_cbecc_analysis(
    "2025",
    "large_building.cibd25",
    timeout=1200  # 20 minutes for complex models
)
```

#### Error 4: Invalid Input File Format

**Symptoms:** CBECC runs but immediately fails with errors in log

**Solution:**
```python
def validate_cibd_file(file_path):
    """Validate CIBD file before running CBECC."""

    with open(file_path, 'r') as f:
        content = f.read()

    # Check for required elements
    required = ['RulesetFilename', 'Proj']

    for req in required:
        if req not in content:
            raise ValueError(f"Invalid CIBD file: missing '{req}'")

    # Check file size
    file_size = Path(file_path).stat().st_size
    if file_size < 1000:
        raise ValueError(f"CIBD file suspiciously small: {file_size} bytes")

    return True
```

### Error Recovery Strategies

```python
def run_cbecc_with_retry(cbecc_version, input_file, max_attempts=3):
    """
    Run CBECC with automatic retry on failure.
    """
    from time import sleep

    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}...")

        try:
            result = run_cbecc_analysis(cbecc_version, input_file)

            if result['success']:
                return result

            # If failed, wait before retry
            if attempt < max_attempts:
                wait_time = attempt * 5  # 5, 10, 15 seconds
                print(f"  Failed. Waiting {wait_time}s before retry...")
                sleep(wait_time)

        except Exception as e:
            print(f"  Exception: {e}")
            if attempt < max_attempts:
                sleep(attempt * 5)

    # All attempts failed
    return {
        'success': False,
        'error': f'Failed after {max_attempts} attempts'
    }
```

---

## Best Practices

### 1. File Management

```python
# Use consistent naming convention
def get_analysis_filename(original_file, cbecc_version):
    """Generate standardized filename for CBECC analysis."""

    stem = Path(original_file).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"{stem}_CBECC{cbecc_version}_{timestamp}.cibd{version[-2:]}"
```

### 2. Logging

```python
import logging

# Set up logging for CBECC integration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cbecc_integration.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('cbecc_integration')

# Use in analysis
logger.info(f"Starting CBECC {version} analysis for {input_file}")
logger.warning(f"Large building detected: {zone_count} zones")
logger.error(f"Analysis failed: {error_message}")
```

### 3. Resource Management

```python
# Clean up temporary files after analysis
def cleanup_analysis_files(input_file, keep_log=True):
    """Clean up temporary files created during analysis."""

    input_path = Path(input_file)

    # List of files CBECC might create
    temp_extensions = ['.tmp', '.bak', '.xml~']

    for ext in temp_extensions:
        temp_file = input_path.with_suffix(ext)
        if temp_file.exists():
            temp_file.unlink()
            print(f"Deleted: {temp_file.name}")

    # Optionally remove log file
    if not keep_log:
        log_file = input_path.with_suffix('.log')
        if log_file.exists():
            log_file.unlink()
```

### 4. Version Compatibility

```python
def check_version_compatibility(internal_repr, target_version):
    """
    Check if building model is compatible with target CBECC version.
    """
    warnings = []

    # Check Title 24 version
    ruleset = internal_repr.proj_metadata.get('RulesetFilename', '')

    if target_version == "2022" and "2025" in ruleset:
        warnings.append("Building uses 2025 ruleset but targeting CBECC 2022")
    elif target_version == "2025" and "2022" in ruleset:
        warnings.append("Building uses 2022 ruleset but targeting CBECC 2025")

    # Check for features only in certain versions
    if target_version == "2022":
        # Check for 2025-only features
        if hasattr(internal_repr, 'battery_systems') and internal_repr.battery_systems:
            warnings.append("Battery systems may not be fully supported in 2022")

    return warnings
```

---

## Troubleshooting

### Issue: GUI Launches Instead of Headless Run

**Symptoms:** CBECC opens GUI window even with `-nrp -b` flags

**Solutions:**
1. Check exact executable path - ensure it's the CBECC binary, not a launcher script
2. Verify flags are correct: `-nrp -b "file.cibd22x"` (no extra flags)
3. On macOS, try running from Terminal first to see if GUI restriction is in place

### Issue: Log File Empty or Missing Content

**Symptoms:** Log file created but has no content or incomplete results

**Solutions:**
1. Check file permissions on output directory
2. Ensure input file is valid (run through CBECC GUI first)
3. Look for crash logs in system logs (Console.app on macOS)
4. Try with simpler building model to isolate issue

### Issue: Extremely Long Analysis Times

**Symptoms:** Analysis takes hours for simple buildings

**Solutions:**
1. Check if CBECC is actually running (monitor CPU usage)
2. Look for infinite loops in log file
3. Simplify building model (reduce zones, surfaces)
4. Ensure adequate system resources (RAM, disk space)

### Issue: "Button returned:OK" Message

**Symptoms:** Running CBECC returns "button returned:OK" instead of running

**Cause:** Help flags triggered GUI dialog that was auto-dismissed

**Solution:**
```python
# Don't use help flags - use -nrp -b directly
# WRONG:
subprocess.run([cbecc_path, "-h"])

# CORRECT:
subprocess.run([cbecc_path, "-nrp", "-b", input_file])
```

---

## Advanced Usage

### Custom CBECC Wrapper Class

```python
class CBECCRunner:
    """High-level wrapper for CBECC CLI operations."""

    def __init__(self, version="2025", timeout=600):
        self.version = version
        self.timeout = timeout
        self.cbecc_path = get_cbecc_path(version)
        self.logger = logging.getLogger(f'CBECC{version}')

    def analyze(self, input_file, output_dir=None):
        """
        Run CBECC analysis with comprehensive error handling.

        Returns CBECCResult object with all analysis data.
        """
        # Implementation here
        pass

    def batch_analyze(self, file_list, parallel=True, max_workers=4):
        """Run multiple analyses in parallel or series."""
        # Implementation here
        pass

    def validate_before_run(self, input_file):
        """Pre-flight checks before running CBECC."""
        # Implementation here
        pass

    def export_results(self, log_file, format='json'):
        """Export parsed results to various formats."""
        # Implementation here
        pass
```

### Integration with ECO Tools Pipeline

```python
from eco_tools.core.internal_repr import InternalRepresentation

class CBECCAnalysisPipeline:
    """
    Complete pipeline: Import → Process → Export → Analyze → Results
    """

    def __init__(self, cbecc_version="2025"):
        self.cbecc_version = cbecc_version
        self.cbecc_runner = CBECCRunner(version=cbecc_version)

    def run(self, input_file, input_format='auto'):
        """
        Complete analysis pipeline.

        Args:
            input_file: Path to input file (any supported format)
            input_format: 'hbjson', 'cibd22x', 'gem', or 'auto'

        Returns:
            Complete analysis results with compliance status
        """

        # Step 1: Import to InternalRepresentation
        internal = self._import_file(input_file, input_format)

        # Step 2: Validate and enhance model
        self._validate_model(internal)

        # Step 3: Export to CBECC format
        cibd_file = self._export_to_cbecc(internal)

        # Step 4: Run CBECC analysis
        cbecc_result = self.cbecc_runner.analyze(cibd_file)

        # Step 5: Parse and structure results
        results = self._structure_results(cbecc_result)

        # Step 6: Optionally import results back to InternalRepresentation
        if results['success']:
            self._import_results_to_internal(internal, results)

        return results

    def _import_file(self, input_file, format_hint):
        """Import file to InternalRepresentation."""
        # Auto-detect format if needed
        # Use appropriate importer
        pass

    def _validate_model(self, internal):
        """Validate model before CBECC export."""
        # Check for required elements
        # Verify zone assignments
        # Validate constructions
        pass

    def _export_to_cbecc(self, internal):
        """Export InternalRepresentation to CBECC format."""
        # Choose appropriate exporter based on version
        # Apply version-specific metadata
        pass

    def _structure_results(self, cbecc_result):
        """Structure raw CBECC results into organized format."""
        pass

    def _import_results_to_internal(self, internal, results):
        """Add CBECC results to InternalRepresentation."""
        # Add as metadata or annotations
        internal.metadata['cbecc_analysis'] = results
```

---

## Summary

### What Works ✅

- **Headless operation:** CBECC runs without GUI using `-nrp -b` flags
- **Subprocess integration:** Can be called from Python subprocess
- **Batch processing:** Multiple files can be processed in parallel
- **Cross-version support:** Works with CBECC 2022 and 2025
- **Log file output:** Results captured in `.log` file
- **ECO Tools export:** All formats (CIBD22, CIBD22X, CIBD25) working

### Limitations ⚠️

- **No stdout/stderr:** All output goes to log file only
- **Limited CLI documentation:** Flag meanings not officially documented
- **No progress reporting:** Cannot monitor progress during analysis
- **Platform-specific paths:** Executable locations vary by OS
- **No help text:** `-h` and `--help` launch GUI instead of printing help

### Recommended Workflow

1. **Import** building model to ECO Tools (any supported format)
2. **Validate** model has required elements (zones, constructions, systems)
3. **Export** to appropriate CBECC format (CIBD22/22X/25)
4. **Run** CBECC with `-nrp -b` flags via subprocess
5. **Monitor** log file for completion and errors
6. **Parse** results from log file
7. **Report** compliance status and energy metrics

---

## Additional Resources

- **CBECC GitHub:** https://github.com/CBECC-software/cbecc
- **CEC Website:** https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/2025-energy-code-compliance-software
- **ECO Tools Docs:** `/Users/DavidM/Documents/ECO_Alpha_v7/docs/`
- **CLI Research:** `CBECC_CLI_FINDINGS.md`
- **Format Specs:** `EMJSON_V6_SCHEMA.md`
- **Modular Export:** `MODULAR_CIBD_COMPLETE.md`

---

**Document Version:** 1.0
**Last Updated:** November 13, 2025
**Status:** Production Ready
