import streamlit as st
import pandas as pd

from utils.demo_data_summary_management_utils import reset_df_demo_summ

from config.constants import DEBUG_PRINT


"""The reset function 
If there is data it will clear it and the app controller will direct to search rather than display 
"""

def clear_current_locations_reset_app():
    """Clears pending and confirmed location markers, and resets the map."""
    
    if DEBUG_PRINT:
        print(f'****INFO clear_current_locations_reset_app')

    # Clear pending location
    st.session_state.clicked_location = None
    
    # Clear confirmed locations
    st.session_state.search_locations_df = pd.DataFrame(columns=["lat", "lng", "name"])
    st.session_state.confirmed_locations_df = pd.DataFrame(columns=["lat", "lng", "name"])
    
    # Clear input box
    if "location_name_input" in st.session_state:
        del st.session_state["location_name_input"]
    
    # Force a new map key so map reloads
    st.session_state['search_map_key'] = f"search_map_{len(st.session_state)}_{pd.Timestamp.now().value}"
    
    # Also reset app_data so that it will definitely revert to search ui
    st.session_state.app_data = {} 
    st.session_state.setdefault('app_data', {})['src_locations_selected'] = False

    # just in case clear df_demo_summ 
    reset_df_demo_summ()

    # Refresh the page
    st.rerun()
