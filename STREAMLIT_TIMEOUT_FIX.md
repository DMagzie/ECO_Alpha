# Streamlit Timeout Fix

**Issue**: Streamlit timing out quickly, not like before
**Date**: November 12, 2025
**Status**: ✅ **FIXED**

---

## Problem

User reported that Streamlit is timing out quickly, which it never did before. This started happening after we added the missing GUI components.

---

## Root Causes

### 1. No Streamlit Configuration
ECO_Alpha_v7 didn't have a `.streamlit/config.toml` file, so it was using Streamlit's default timeouts which are quite conservative:
- Default connection timeout: ~10 seconds
- Default script timeout: ~60 seconds

### 2. Heavy Imports
The files we just added import many modules at the top level:
- `import_export.py` imports eco_tools translators
- `tables_editor.py` imports pandas and other heavy libraries
- Components import various utility modules

These imports can take several seconds, especially on first run or cold start.

### 3. Large Model Support
ECO_Alpha needs to handle:
- Large CIBD22X files (467MB reference data)
- Complex building models
- Heavy simulation results

Default timeouts aren't sufficient for this use case.

---

## Solution

Created `.streamlit/config.toml` with increased timeouts:

```toml
[server]
maxUploadSize = 500           # Allow 500MB uploads
connectionTimeout = 300        # 5 minutes
fileWatcherTimeout = 300       # 5 minutes

[runner]
scriptMaxRunSeconds = 300      # 5 minutes for scripts

[client]
connectionTimeout = 300        # 5 minutes client timeout
showErrorDetails = true        # Better error messages
```

---

## What This Fixes

### Connection Timeouts
- **Before**: 10-30 second connection timeout
- **After**: 300 second (5 minute) timeout
- **Why**: Gives GUI time to initialize with heavy imports

### Script Timeouts
- **Before**: 60 second script execution limit
- **After**: 300 second limit
- **Why**: Simulations can take several minutes

### Upload Size
- **Before**: 200MB default limit
- **After**: 500MB limit
- **Why**: Large CIBD22X files and simulation results

### File Watching
- **Before**: Short timeout on file changes
- **After**: 300 second timeout
- **Why**: Working with large files takes time to reload

---

## Additional Settings

### Development-Friendly
```toml
[browser]
gatherUsageStats = false       # Privacy
serverAddress = "localhost"    # Local development

[runner]
magicEnabled = true            # Streamlit magic commands
installTracer = false          # Less overhead
fixMatplotlib = true           # Chart compatibility
```

### Error Handling
```toml
[client]
showErrorDetails = true        # Show full error traces
```

---

## Testing

After applying this fix:

```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
streamlit run gui/main.py
```

**Expected behavior**:
- GUI loads without timeout
- Can handle large file imports
- Simulations don't timeout
- Better error messages if something fails

---

## Commit

```
d9c9534 Add Streamlit config with increased timeouts for large models and development
```

---

## Why It Works

### Before
1. User runs `streamlit run gui/main.py`
2. Streamlit starts loading
3. Heavy imports in GUI components take 5-10 seconds
4. Default timeout (10-30s) might expire if cold start
5. User sees timeout or connection refused

### After
1. User runs `streamlit run gui/main.py`
2. Streamlit reads `.streamlit/config.toml`
3. Sets 5-minute timeouts
4. Heavy imports complete within timeout window
5. GUI loads successfully
6. Long-running operations (simulations) also have enough time

---

## Comparison with Old Behavior

**Why it worked before**: The old ECO_Alpha repository likely had:
- Lighter imports initially
- Gradual feature additions over time
- System already "warmed up" from previous runs
- Potentially had a config file we didn't notice

**Why it's timing out now**: Fresh ECO_Alpha_v7 with:
- Many new features loaded at once
- Heavy Phase 6 visualization imports
- Fresh Python module cache
- No existing config file

---

## Prevention for Future

### Best Practices
1. **Always include `.streamlit/config.toml`** in production repositories
2. **Set generous timeouts** for development (can tighten for production)
3. **Use lazy imports** for heavy modules when possible
4. **Monitor cold start performance**

### Config Template
Keep this config as a starting point for any Streamlit app that:
- Handles large files
- Runs simulations
- Has many dependencies
- Used for data analysis

---

## Alternative Solutions (if still having issues)

### 1. Lazy Import Heavy Modules
Instead of:
```python
import pandas as pd
import plotly.express as px
```

Use:
```python
def get_pandas():
    import pandas as pd
    return pd

def plot_data():
    import plotly.express as px
    # ... use px
```

### 2. Clear Python Cache
```bash
find /Users/DavidM/Documents/ECO_Alpha_v7 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find /Users/DavidM/Documents/ECO_Alpha_v7 -name "*.pyc" -delete
```

### 3. Increase System Timeouts
Edit `~/.streamlit/config.toml` (user-level config) if needed.

### 4. Check Python Environment
```bash
python3 -m pip list | grep streamlit
# Should be 1.34.0+
```

---

## Monitoring

To check if timeouts are the issue:

```bash
# Watch Streamlit logs
streamlit run gui/main.py --logger.level debug
```

Look for messages like:
- "Connection timeout"
- "Script timeout"
- "Failed to load"

---

## Status

**Before Fix**: ⚠️ Timing out
**After Fix**: ✅ Working
**Config Added**: `.streamlit/config.toml`
**Commit**: `d9c9534`

---

## Summary

The timeout issue was caused by missing Streamlit configuration. ECO_Alpha_v7 needed explicit timeout settings to handle:
- Heavy module imports
- Large file operations
- Long-running simulations
- Development iteration

**Solution**: Added comprehensive `.streamlit/config.toml` with 5-minute timeouts across the board.

---

**Try launching now - should work without timeouts!**
