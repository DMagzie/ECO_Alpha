import streamlit as st

def show_diagnostics():
    st.subheader("Diagnostics Information")
    diagnostics = [
        {"level": "info", "code": "MODEL-ZONES", "message": "Zones: 5"},
        {"level": "warning", "code": "MODEL-WALLS", "message": "Walls count mismatch."},
        {"level": "error", "code": "MODEL-DHW", "message": "DHW systems count mismatch."},
    ]
    st.json(diagnostics, expanded=False)
