import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd

from config.constants import DEBUG_PRINT
from utils.isochrone_utils import get_isos_from_confirmed_locations_df
from utils.competition_utils import process_competition_with_isochrones, summarise_competition
from utils.demo_processing_utils import (process_LA_rents, 
                                         process_household_inc, 
                                         process_popn_data)
from utils.demo_data_summary_management_utils import create_base_df_demo_summ

def validate_confirmed_locations(df):
    """
    Validate the confirmed locations DataFrame.
    Returns True if the data is valid, False otherwise.
    """
    if df is None or df.empty:
        st.warning("No confirmed locations to process. Please select locations on the map.")
        return False

    required_columns = ['name', 'lat', 'lng']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"DataFrame is missing required columns: {missing_columns}")
        print(f'df.columns {df.columns}')
        return False

    if not pd.api.types.is_numeric_dtype(df['lat']) or not pd.api.types.is_numeric_dtype(df['lng']):
        st.error("Latitude and longitude must be numeric.")
        return False

    if not ((df['lat'].between(-90, 90)).all() and (df['lng'].between(-180, 180)).all()):
        st.error("Some latitude or longitude values are out of valid range.")
        return False

    if df['name'].duplicated().any():
        st.warning("Some location names are duplicated. Processing will continue.")

    return True

def set_storenames_from_search_locations(valid_storenames):

    """Set the list of selected store names"""
    print(f'****INFO Process_location set_storenames_from_search_locations saving valid_storename to st.session_state.selected_storenames')
    print(f'****INFO {valid_storenames}')
    st.session_state.selected_storenames = valid_storenames
    
    # Auto-select first store if none selected
    if valid_storenames and not st.session_state.get('selected_storename'):
            st.session_state.selected_storename = valid_storenames[0]
            print(f'****INFO valid_storename {valid_storenames[0]}')


def process_search_locations():
    """
    Process the confirmed locations after validation.
    """
    df = st.session_state.get('search_locations_df')
    
    if not validate_confirmed_locations(df):
        return  # Stop processing if validation fails

    # Get valid storenames from the dataframe
    valid_storenames = df['name'].values.tolist()

    # add these to the session_state  + default value
    set_storenames_from_search_locations(valid_storenames)

    # Create the main headings of the df_demo_summ
    create_base_df_demo_summ(storenames_list=valid_storenames)

    if DEBUG_PRINT:
        print(f'****INFO Valid storenames: {valid_storenames} length: {len(valid_storenames)}')

    gdf_isos = get_isos_from_confirmed_locations_df(df)
    
    if not gdf_isos.empty:
        print(f'****INFO saving gdf_isos to session_state {gdf_isos.shape}')
        st.session_state.gdf_isos = gdf_isos
        if DEBUG_PRINT:
            try:
                fpath_test = r'D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_isos.gpkg'
                gdf_isos.to_file(fpath_test, driver='GPKG')
                print(f'****INFO Successfully saved gdf_isos to {fpath_test}')
            except:
                print(f'!!!!WARNING failed to save test version of gdf_isos')

    gdf_competition = process_competition_with_isochrones()

    if DEBUG_PRINT:
        try:
            print(f'****INFO process_search_locations gdf_competion: {gdf_competition.shape}')
            print(f'****INFO process_search_locations gdf_competion: {gdf_competition.columns}')
        except:
            print(f'!!!!WARNING process_search_locations could not print info on gdf_competition')


    # Process demographic data
    process_LA_rents()
    process_household_inc()
    process_popn_data()

    # Check if we have valid competition data and update session state
    if gdf_competition is not None and not gdf_competition.empty:
        
        st.session_state.gdf_competition = gdf_competition

        # Update the flag to trigger UI output
        st.session_state.src_locations_selected = True
        st.rerun()