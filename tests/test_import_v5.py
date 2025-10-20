from Superceeded.translate_cibd22x_to_v5 import parse_and_set_active_model_v5
import streamlit as st


def test_parse_and_set_active_model_v5():
    xml_text = "<CBECCProject><Project><Name>Test Project</Name></Project></CBECCProject>"

    # Set up the Streamlit session state
    st.session_state = {}

    # Call the function
    parse_and_set_active_model_v5(xml_text)

    # Check that the active model was set
    assert "active_em_v5" in st.session_state
    assert st.session_state.active_em_v5["project"]["name"] == "Test Project"


def test_stub(): pass
