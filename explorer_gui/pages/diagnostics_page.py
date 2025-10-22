import streamlit as st
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ... rest of your existing code ...from diagnostics import show_diagnostics

def show_diagnostics():
    st.subheader("Diagnostics Information")
    diagnostics = [
        {"level": "info", "code": "MODEL-ZONES", "message": "Zones: 5"},
        {"level": "warning", "code": "MODEL-WALLS", "message": "Walls count mismatch."},
        {"level": "error", "code": "MODEL-DHW", "message": "DHW systems count mismatch."},
    ]
    st.json(diagnostics, expanded=False)
