# Quick Start Guide for Testers

## 1. Launch the Application

```bash
cd "/Users/DavidM/Documents/Documents - MacBook Air (4)/ECO_Alpha_v7"
streamlit run gui/main.py
```

Open browser to: **http://localhost:8501**

## 2. Priority Test Order

Test these features first (P0):

1. **Zone Analysis** - Navigate to "Zone Analysis" page
2. **ESG Report** - Navigate to "ESG Report" page
3. **Site Loads** - Navigate to "Site Loads" page
4. **CUAC Import** - Go to Import, upload a CSV file
5. **Tariff Management** - LCCA Dashboard > Tariffs tab

## 3. Key Things to Check

### Each New Page Should:
- Load without errors
- Display all tabs
- Accept user input
- Calculate results
- Export data (CSV/JSON)

### Navigation Should:
- Show emoji icons on all pages
- Display "No model loaded" indicator
- Show module status in expander

## 4. Reporting Issues

If something fails:
1. Note which page/tab
2. What step failed
3. Any error message
4. Screenshot if possible

## 5. Test Data Locations

- Sample CUAC: `docs/test_pack/sample_data/sample_cuac.csv`
- Sample zones: `docs/test_pack/sample_data/sample_zones.json`

## 6. Stop Testing If:

- Application won't start
- Multiple pages crash
- Data is being corrupted

Contact development team immediately for critical issues.
