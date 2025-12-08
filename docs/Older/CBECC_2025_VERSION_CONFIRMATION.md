# CBECC 2025 Version Confirmation

**Date:** November 13, 2025
**CBECC Software:** Version 2.0 (just released)

## Version Information

### Software Bundle Version
- **App Name:** CBECC 2025.app
- **Bundle Version:** 2.0-RC
- **Release Date:** November 12, 2025 (approved yesterday)

### Internal SoftwareVersion String
The `SoftwareVersion` property that goes inside CIBD25 files:
```
SoftwareVersion = "CBECC 2025.2.0 (1390)"
```

This is **NOT** the same as the bundle version. The bundle version is "2.0", but files must contain "2025.2.0 (1390)".

## Verification

**Updated to build 1390 per user confirmation.**

Old sample files (from earlier beta) had build 1381:
```bash
SoftwareVersion = "CBECC 2025.1.0 (1381)"  # Earlier beta version
```

CBECC 2025 Version 2.0 (released Nov 12, 2025) uses build 1390:
```bash
SoftwareVersion = "CBECC 2025.2.0 (1390)"  # Official release
```

## ECO Tools Exporter Status

Our CIBD25 exporter is **already correct** and uses the right version string:

**File:** `eco_tools/translators/cibd25/exporter.py`

**Metadata Injection (Updated to build 1390):**
```python
internal.proj_metadata['SoftwareVersion'] = 'CBECC 2025.2.0 (1390)'
internal.proj_metadata['BldgEngyModelVersion'] = '17'
internal.proj_metadata['RulesetFilename'] = 'T24_2025.bin'
```

## Test Results

```
✅ TEST PASSED: Minimal export is valid CIBD25

Metadata Found:
  RulesetFilename: T24_2025.bin
  SoftwareVersion: CBECC 2025.2.0 (1390)
  BldgEngyModelVersion: 17
```

## Summary

✅ **Updated to build 1390** - ECO Tools CIBD25 exporter now uses correct version
✅ Exports with `SoftwareVersion = "CBECC 2025.2.0 (1390)"`
✅ All validation tests passing
✅ Ready for production use with CBECC 2025 Version 2.0

## Note on Version Numbering

**Software Bundle Version (App):** 2.0
- This is what you see in `/Applications/CBECC 2025.app`
- This is the "product version" number

**SoftwareVersion (File Property):** CBECC 2025.2.0 (1390)
- This is what goes INSIDE .cibd25 files
- This is the "internal version" number
- Build number: 1390 (official release)
- Previous beta: build 1381

Both refer to the same software, just different version identifiers for different purposes.
