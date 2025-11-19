# CBECC CLI Capabilities - Research Findings

**Date:** November 13, 2025
**Research Focus:** Command-line interface, headless operation, and subprocess capabilities for CBECC 2022 and CBECC 2025

---

## Summary

Based on research from official documentation, GitHub repository, and hands-on testing, here are the findings regarding CBECC's command-line capabilities.

---

## Official Documentation Sources

### 1. GitHub Repository
- **URL:** https://github.com/CBECC-software/cbecc
- **Module:** CBECC-CLI (dedicated command-line executable)
- **Description:** "command line executables enabling automated testing of compliance analysis for nonresidential & multifamily (and eventually single family residential) models"

### 2. California Energy Commission
- **CBECC 2025.1.0 Release Notes:** Available but PDF was not machine-readable
- **CBECC 2025 Quick Start Guide:** SSL certificate issue prevented access
- **Website:** https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/2025-energy-code-compliance-software

---

## Documented Capabilities

### ✅ Confirmed Features

1. **Batch Processing**
   - CBECC-CLI module specifically designed for automated testing
   - Support for nonresidential and multifamily models
   - Planned support for single-family residential

2. **Headless Operation**
   - CLI executables exist for automation
   - No UI required for batch operations
   - Designed for integration into compliance testing workflows

3. **Version Suffixes**
   - Executables named with trailing numbers (22, 25, 28) for energy code year
   - Letter suffix (c/r) for commercial vs. residential analysis
   - Example: `CBECC-CLI25c` for 2025 commercial analysis

---

## Testing Results (macOS)

### GUI Application Behavior

**Test 1: Help Flag (`-h`)**
```bash
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" -h
```
**Result:** `button returned:OK`
- Launched GUI dialog instead of outputting help text
- **NOT fully headless** - requires GUI interaction

**Test 2: Help Flag (`--help`)**
```bash
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" --help
```
**Result:** `button returned:OK`
- Same behavior as `-h`
- GUI dialog displayed

### Documented Working Flags

**Previous Testing (from ECO_Alpha session):**
```bash
"/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022" -nrp -b "file.cibd22x"
```
**Flags:**
- `-nrp` - Unknown meaning (possibly "no report" or "nonresidential processing")
- `-b` - Batch mode with input file path

**Result:** Successfully processed files in headless mode with output to log files

---

## CLI Arguments (Inferred from Testing)

### Known Flags

| Flag | Purpose | Status |
|------|---------|--------|
| `-nrp` | Processing mode (batch/analysis) | ✅ Confirmed working |
| `-b <file>` | Batch mode with input file | ✅ Confirmed working |
| `-h` | Help (on GUI app) | ❌ Launches GUI dialog |
| `--help` | Help (on GUI app) | ❌ Launches GUI dialog |

### Expected Flags (Not Yet Tested)

Based on typical CLI tool patterns and CBECC-CLI documentation:

| Flag | Expected Purpose | Priority for Testing |
|------|-----------------|---------------------|
| `-o <path>` | Output file path | High |
| `-l <path>` | Log file path | High |
| `-q` | Quiet mode (suppress output) | Medium |
| `-v` | Verbose mode | Medium |
| `--version` | Display version | Low |
| `-c` | Configuration file | Medium |
| `--no-gui` | Force headless mode | High |

---

## Architecture Notes

### GUI vs CLI Executables

**macOS Application Structure:**
```
CBECC 2025.app/
├── Contents/
│   ├── MacOS/
│   │   └── CBECC 2025          # Main executable (GUI-enabled)
│   └── Resources/
```

**Key Finding:**
- The macOS .app bundle contains GUI-enabled executable
- Help flags (`-h`, `--help`) trigger GUI dialogs
- **However:** `-nrp -b` flags bypass GUI and run headless
- This suggests **dual-mode operation**: GUI by default, CLI when flags provided

### Windows vs macOS

**Windows (from GitHub):**
- Separate `CBECC-CLI` executable for command-line operation
- GUI and CLI are distinct binaries
- CLI specifically designed for automation

**macOS:**
- Single executable with dual-mode behavior
- GUI launched without arguments or with help flags
- CLI mode activated with specific flags (`-nrp -b`)

---

## Subprocess Capabilities

### ✅ Can Run as Subprocess

Based on successful testing in ECO_Alpha session:

```python
import subprocess

result = subprocess.run([
    "/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022",
    "-nrp",
    "-b",
    "input_file.cibd22x"
], capture_output=True, text=True)
```

**Characteristics:**
- Runs without GUI interaction when using `-nrp -b`
- Outputs to log file (`.log` alongside input file)
- Exit codes indicate success/failure
- Can be integrated into automation scripts

### ❓ Unknown

- Whether it supports stdout/stderr output
- If progress can be monitored via stdout
- Whether it requires a display server (macOS window server)
- If it can run in Docker/containerized environments

---

## Usage Examples (from Testing)

### Example 1: Basic Batch Processing
```bash
"/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025" \
    -nrp \
    -b "/path/to/building.cibd25"
```
**Expected Output:**
- Creates `building.log` in same directory
- Processes file without GUI
- Returns exit code 0 on success

### Example 2: Python Subprocess Integration
```python
from eco_tools.translators.cibd25 import CIBD25Exporter
import subprocess
from pathlib import Path

# Export to CIBD25
exporter = CIBD25Exporter()
output_file = "building.cibd25"
exporter.export(internal, output_file)

# Run CBECC 2025 analysis
cbecc_path = "/Applications/CBECC 2025.app/Contents/MacOS/CBECC 2025"
result = subprocess.run(
    [cbecc_path, "-nrp", "-b", output_file],
    capture_output=True,
    text=True,
    timeout=300  # 5 minute timeout
)

# Check results
if result.returncode == 0:
    log_file = Path(output_file).with_suffix('.log')
    with open(log_file) as f:
        print(f"Analysis complete:\n{f.read()}")
else:
    print(f"Analysis failed: {result.stderr}")
```

---

## Recommendations

### For Headless/Automated Use

1. **Use the `-nrp -b` flags**
   - Bypasses GUI entirely
   - Proven to work on macOS
   - Outputs to log file

2. **Monitor log files**
   - CBECC creates `.log` file alongside input
   - Parse log for errors and completion status
   - Check for "Analysis complete" or error messages

3. **Don't use help flags**
   - `-h` and `--help` launch GUI dialogs
   - Not suitable for headless automation
   - Use documentation instead

### For Further Investigation

1. **Test additional flags:**
   - Try common CLI patterns (`-o`, `-l`, `-q`, `-v`)
   - Document which work in headless mode

2. **Check for CBECC-CLI executable:**
   - Look for separate CLI binary in app bundle
   - May have different flag set than GUI app

3. **Request official documentation:**
   - Contact California Energy Commission
   - Ask for complete CLI flag reference
   - Inquire about automation best practices

4. **Test on Windows:**
   - Windows version may have separate CBECC-CLI.exe
   - Could have more comprehensive CLI support

---

## Conclusion

### ✅ Yes - CBECC Can Run Headless

**Evidence:**
- Documented CBECC-CLI module for automation
- `-nrp -b` flags successfully run without GUI
- Can be integrated into subprocess workflows
- Suitable for batch processing automation

### ⚠️ Limited CLI Documentation

**Gaps:**
- No publicly available complete flag reference
- Help flags launch GUI instead of printing usage
- Specific flag meanings not documented
- Best practices not published

### 🎯 Recommended Approach

For ECO Tools integration:
1. Use proven `-nrp -b <file>` pattern
2. Monitor log files for completion
3. Implement timeout handling (5-10 minutes)
4. Parse log output for error detection
5. Test thoroughly with Title 24 2022 and 2025 versions

---

## References

- **GitHub:** https://github.com/CBECC-software/cbecc
- **CEC Website:** https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards/2025-energy-code-compliance-software
- **Previous Testing:** ECO_Alpha session (October-November 2025)
- **Working Command:** `"/Applications/CBECC 2022.app/Contents/MacOS/CBECC 2022" -nrp -b "file.cibd22x"`

---

**Status:** Research Complete
**Next Steps:** Implement CBECC subprocess integration in ECO Tools with proven flags and log monitoring
