import streamlit as st
import os 
import pandas as pd
import geopandas as gpd

from utils.parquet_io_utils import load_gdf_from_parquet, save_gdf_to_parquet
from config.constants import DEBUG_PRINT


""""This module loads the data files required for the application
These are:
    - ssdb 
    - isos
    - LA Rents Ovt 24
    - msoa_data_2020
    - msoa_data_2021
All contained in the assets/data folder

+ also loads app_data - although this mihgt dissapper from here TODO

"""

"""This module contains the functionality to load data into the app
It is called from session_state_utils _initialize_app_data()"""




FNAME_MSOA_20 = "gdf_2020_msoa_inc_data.parquet"
FNAME_ISO = "gdf_iso_light_4326.parquet"
FNAME_LA_Rents = "gdf_LA_Rents_Oct24_EW.parquet"
FNAME_MSOA_22 = "gdf_msoa_data_light.parquet"
# FNAME_SSDB = "gdf_light_ssdb_4326.parquet"
FNAME_COUNTRIES = "gdf_countries_4326.parquet"

FNAME_WEIGHTINGS = "Savills_Score_weightings.xlsx"

def validate_gdf(gdf) -> bool:
    """
    Validate that the input is a GeoDataFrame with a valid geometry column.

    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        return False

    if gdf.geometry.name not in gdf.columns:
        return False

    if gdf.geometry.is_empty.all():
        return False

    return True



@st.cache_data(show_spinner=True)
def load_data_files():
    """
    Load all required GeoDataFrames from parquet files with validation.
    Returns a dictionary of GeoDataFrames.
    """
    data_files = {
        "msoa_20": FNAME_MSOA_20,
        "msoa_22": FNAME_MSOA_22,
        "iso": FNAME_ISO,
        "la_rents": FNAME_LA_Rents,
        # "ssdb": FNAME_SSDB,
        "countries": FNAME_COUNTRIES,
    }

    gdfs = {}

    for key, fname in data_files.items():
        fpath = os.path.join('assets','data', fname)
        gdf = load_gdf_from_parquet(fpath, epsg=4326)

        if not validate_gdf(gdf):
            raise ValueError(f"!!!!WARNING {fname} did not load as a valid GeoDataFrame with a geometry column.")

        gdfs[key] = gdf

    return gdfs


# Callable function to save isochrone to update
# Don't need load function as we simply update the value in the session_date.data['iso']
def save_isochrone_gdf_to_file(gdf_iso):
    fpath_iso = os.path.join(DATA_FOLDER, FNAME_ISO)
    try:
        save_gdf_to_parquet(gdf_iso, fpath_iso)
        print(f'****INFO Successfully save gdf_iso to {fpath_iso}')
    except:
        print(f'!!!!WARNING Was not able to save gdf_iso to {fpath_iso}')


def get_ssdb_from_ss():
    """Get the ssdb gdf from session state.
    Easier to Ask Forgiveness than Permission EAFP
    Returns:
        A copy of the ssdb gdf if it exists and is not empty,
        otherwise returns None.
    """
    try:
        ssdb = st.session_state.data['ssdb']
        ssdb_copy = ssdb.copy()
        if not ssdb_copy.empty:
            return ssdb_copy
    except (KeyError, AttributeError, TypeError):
        # KeyError: 'data' or 'ssdb' doesn't exist
        # AttributeError: missing .copy() or .empty methods
        # TypeError: object is None or doesn't support operations
        pass
    
    return None


def get_store_isos_from_ss():
    """Get the iso gdf from session state.
    These are the selected locations isos not the wider iso file 
    Easier to Ask Forgiveness than Permission EAFP
    Returns:
        A copy of the iso gdf if it exists and is not empty,
        otherwise returns None.
    """
    try:
        gdf_store_isos = st.session_state.gdf_isos
        gdf_store_isos_copy = gdf_store_isos.copy()
        if not gdf_store_isos_copy.empty:
            return gdf_store_isos_copy
    except (KeyError, AttributeError, TypeError):
        # KeyError: 'app_data' or 'gdf_isos' doesn't exist
        # AttributeError: missing .copy() or .empty methods
        # TypeError: object is None or doesn't support operations
        pass

    return None
    
def validate_scoring_dataframe(df):
    # Check ascending order
    _required_cols = ['Lower Bound', 'Upper Bound', 'Score']
    _missing_cols = []
    for _col in _required_cols:
        if _col not in _required_cols:
            _missing_cols.append(_col)
    if _missing_cols:
        print(f'!!!!WARNING validate_scoring_dataframe missing cols: {_missing_cols} ')
        raise KeyError(f'Missing columns')

    if not df['Lower Bound'].is_monotonic_increasing:
        print("ERROR: Lower Bound not in ascending order")
        return False
    if not df['Upper Bound'].is_monotonic_increasing:
        print("ERROR: Upper Bound not in ascending order")
        return False
    
    # Check for overlaps
    for i in range(len(df)-1):
        if df['Upper Bound'].iloc[i] > df['Lower Bound'].iloc[i+1]:
            print(f"!!!!WARNING: Overlap in bounds between row {i} and {i+1}")
            return False
    
    return True

def get_savills_score_weightings():
    """Function loads the score weigghtings 
        - This is both the percent that each score contributes to the overall total
        and the bounds and score for each asset
        returns either  or if error None df_weightings and weightings_dict 
    """
    fpath_weightings = os.path.join(DATA_FOLDER, FNAME_WEIGHTINGS)
    # First load the front sheet where the column Internal name will provide keys to the other sheets
    try:
        if DEBUG_PRINT:
            print(f'****INFO - load_savills_score_weightings trying to load score weights from {fpath_weightings}')
            
            df_overall_weightings = pd.read_excel(fpath_weightings,
                                                sheet_name='Weighting')
            if df_overall_weightings.empty:
                print(f'!!!!WARNING df_overall_weightings could not be loaded correctly')
                return None, None
            print(f'*********************')
            print(f'{df_overall_weightings}')
            
            weightings_dict = {}

            # Capture the data for each individual score weight from each sheet in first col
            for idx, row in df_overall_weightings.iterrows():
                sheet_name = row.Internal_Name
                display_name = row.Display_Name
                
                if sheet_name.lower() == 'total':
                    print(f'****INFO skipping Total row')
                    continue

                print(f'****INFO Getting weightings for: {sheet_name}')
                try:
                    df_ind_scoring = pd.read_excel(fpath_weightings,
                                                    sheet_name=sheet_name)
                    if not df_ind_scoring.empty:
                        # Check if the weightings df is correctly formatted
                        if validate_scoring_dataframe(df_ind_scoring):
                            weightings_dict[sheet_name] = df_ind_scoring
                        else:
                            print(f'!!!!WARNING {sheet_name} {display_name} is not validly formatted')
                            continue
                except:
                    print(f'!!!!WARNING - could not get df for {display_name} {sheet_name}')
            
            return df_overall_weightings, weightings_dict
            
    except Exception as e:
        print(f'!!!!WARNING - failed to load weights: {e}')
        return None, None

def get_validated_df_ssdb(df_ssdb):
    """This function validates the loaded SSDB and returns validated DataFrame or None"""
    _required_cols = ['storename','address', 'city', 
                       'latitude', 'longitude', 
                      'ss_type',  'area_unit',
                      'store_cla','store_mla']
    
    # Check required columns
    missing_cols = [col for col in _required_cols if col not in df_ssdb.columns]
    if missing_cols:
        print(f'!!!!WARNING is_ssdb_df_valid missing cols: {missing_cols}')
        return None
    
    # Create a copy to avoid modifying original
    df_validated = df_ssdb.copy()
    
    # Convert latitude/longitude to numeric, coercing errors to NaN
    df_validated['latitude'] = pd.to_numeric(df_validated['latitude'], errors='coerce')
    df_validated['longitude'] = pd.to_numeric(df_validated['longitude'], errors='coerce')
    
    # Filter out rows with invalid coordinates
    original_count = len(df_validated)
    
    # Check for valid latitude (-90 to 90) and longitude (-180 to 180)
    valid_lat_mask = (df_validated['latitude'] >= -90) & (df_validated['latitude'] <= 90)
    valid_lon_mask = (df_validated['longitude'] >= -180) & (df_validated['longitude'] <= 180)
    valid_coords_mask = valid_lat_mask & valid_lon_mask
    
    # Remove rows with NaN coordinates or out-of-range values
    df_validated = df_validated[valid_coords_mask].copy()
    
    filtered_count = original_count - len(df_validated)
    if filtered_count > 0:
        print(f'!!!!WARNING is_ssdb_df_valid filtered out {filtered_count} rows with invalid coordinates')
    
    # Check if we have any valid rows left
    if len(df_validated) == 0:
        print('!!!!WARNING is_ssdb_df_valid no valid rows remaining after coordinate validation')
        return None
    
    return df_validated

@st.cache_data
def get_gdf_ssdb_from_df(df_ssdb):
    """Turns import df_ssdb into gdf"""
    try:
        ssdb_geom = gpd.points_from_xy(df_ssdb.longitude, df_ssdb.latitude)
        return gpd.GeoDataFrame(df_ssdb, geometry=ssdb_geom, crs=4326)
    except:
        print(f'!!!WARNING get_gdf_ssdb_from_df was not able to convert input df into gdf')
        return None


def load_ssdb_gdf_from_excel():

    """This function loads the ssdb from an Excel file
    Used as a pre-cursor to uploading the file directly
    returns gdf_ssdb or None"""
    FNAME_SSDB = 'SSDB.xlsx'
    try:
        df_ssdb = pd.read_excel(os.path.join(DATA_FOLDER,FNAME_SSDB))
        validated_df = get_validated_df_ssdb(df_ssdb)
        return get_gdf_ssdb_from_df(validated_df)
       

    except:
        print(f'!!!WARNING load_ssdb_gdf_from_excel was not able to load SSDB gdf into data session_state')

        return None
