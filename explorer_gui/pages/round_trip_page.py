import streamlit as st
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from explorer_gui.import_export import emjson6_to_cibd22x

# ... rest of your existing code ...
def handle_round_trip():
    st.subheader("Round-Trip Check (EM → XML → EM)")
    em_file = st.file_uploader("Upload EM v6 JSON", type=["json"])
    if em_file:
        em_data = json.load(em_file)  # Load the EMJSON v6 file
        xml_data = emjson6_to_cibd22x(em_data)  # Convert to CIBD22x XML
        em_back = translate_cibd22x_to_v6(xml_data)  # Convert back to EMJSON v6

        st.write("**Original EM JSON:**")
        st.json(em_data)  # Display original EM JSON
        st.write("**Back-converted EM JSON:**")
        st.json(em_back)  # Display back-converted EM JSON

        # Compare the two
        # You can add logic here to compare the original and back-converted models
