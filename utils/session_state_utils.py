import streamlit as st
import pandas as pd 
import geopandas as gpd

from config.constants import DEBUG_PRINT, ISO_TIME_MINS

from utils.search_map_utils import initialize_search_map_session_state
from utils.demo_data_summary_management_utils import initialize_df_demo_summ


def initialize_session_state():

    if DEBUG_PRINT:
        print(f'****INFO Intialising session_states including search_map_ss & df_demo_summ ss')

    initialize_search_map_session_state()
    initialize_df_demo_summ()
    initialize_session_state_for_display_ui()


def initialize_session_state_for_display_ui():

    """Function to set values up front so that there is no conflict with widget creation"""

    if DEBUG_PRINT:
        print(f'****INFO Intialising session_states for Display in initialize_session_state_for_display_ui')

    if "selected_drive_time" not in st.session_state:
        st.session_state.selected_drive_time = ISO_TIME_MINS[2]


