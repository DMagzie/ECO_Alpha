# Debugging Greyed-Out Buttons

**Issue**: Navigation buttons and file upload button are greyed out
**Status**: Investigating

---

## Possible Causes

### 1. Streamlit App Error
When Streamlit encounters an error during page rendering, widgets become unresponsive (greyed out).

**Check the terminal** where you ran `streamlit run gui/main.py` for error messages.

### 2. Session State Not Initialized
Some pages might require session state variables that aren't set yet.

### 3. Import Errors
If a module fails to import, Streamlit may partially render the page with disabled widgets.

---

## Quick Diagnosis

### Step 1: Check Terminal Output

Look for error messages in the terminal where Streamlit is running:
- Red error text
- Traceback messages
- Import errors
- AttributeError or NameError

**Common errors to look for**:
```
ModuleNotFoundError: No module named 'xxx'
AttributeError: module 'xxx' has no attribute 'yyy'
KeyError: 'some_key'
```

### Step 2: Check Browser Console

Open browser console (F12 or Cmd+Option+I on Mac):
- Look for JavaScript errors
- Check Network tab for failed requests
- Look for WebSocket connection issues

### Step 3: Check Streamlit Status

In the browser, top right corner:
- Should say "Running" with green dot
- If it says "Connecting..." or "Error", that's the issue

---

## Quick Fixes to Try

### Fix 1: Force Refresh

1. In browser: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+F5** (Windows)
2. This clears Streamlit cache and reloads

### Fix 2: Clear Session State

1. In terminal, stop Streamlit (Ctrl+C)
2. Delete cache:
   ```bash
   rm -rf ~/.streamlit/cache
   ```
3. Restart:
   ```bash
   streamlit run gui/main.py
   ```

### Fix 3: Check for Specific Errors

Run this to test imports:
```bash
cd /Users/DavidM/Documents/ECO_Alpha_v7
python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, './gui')
from gui.pages.import_page import handle_import
print('Import page OK')
"
```

If this shows an error, that's the problem.

---

## Most Likely Cause

Based on testing, the import chain has issues when run outside Streamlit context. **But within Streamlit, it should work** because `main.py` sets up the paths correctly.

**The greyed-out buttons suggest**:
1. An error occurred during page initialization
2. Check terminal for the actual error message
3. The error is preventing proper page rendering

---

## What to Do Now

**Please check the terminal where Streamlit is running and tell me:**

1. Are there any RED error messages?
2. Any tracebacks (lines starting with "Traceback")?
3. Any messages saying "ModuleNotFoundError" or "AttributeError"?

**Copy the full error output here** and I'll fix it immediately.

---

## If No Errors Visible

If terminal shows no errors but buttons are still greyed:

### Check Streamlit Status Bar

Top right of browser, next to the "Deploy" button:
- **Green "Running"** = App is working, might be a different issue
- **Red "Error"** = Click it to see error details
- **Yellow "Connecting"** = Network/WebSocket issue

### Try This

Add some debug output. Edit `/Users/DavidM/Documents/ECO_Alpha_v7/gui/pages/import_page.py`:

At the very start of `handle_import()` function (around line 27), add:
```python
def handle_import():
    st.write("DEBUG: Import page loading...")  # ADD THIS LINE
    st.title("Import Model File")
    # ... rest of code
```

This will confirm the page is actually loading.

---

## Common Streamlit Widget Issues

### Widgets Disabled When:
1. **Page is still loading** - Wait a few seconds
2. **Error occurred** - Check terminal
3. **WebSocket disconnected** - Check browser console
4. **Form submission in progress** - Wait for completion
5. **Session rerun triggered** - Wait for page to stabilize

### Quick Test

Open browser console (F12), go to Console tab, and type:
```javascript
console.log("Buttons:", document.querySelectorAll('button[disabled]').length);
```

If this returns a number > 0, buttons are actually disabled in HTML.

---

## Next Steps

1. **Check terminal for errors** - Most likely cause
2. **Copy any error messages here**
3. **I'll fix immediately**

The buttons being greyed means something failed during initialization. We need to see the actual error to fix it.
