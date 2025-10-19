import streamlit as st
import os
from PIL import Image

LOGO_PATH = os.path.join('assets', 'images', 'savills_logo.jpg')

IMG_WIDTH_PX = 200


def add_savills_logo():
    """Safe logo loading with error handling and fallback"""
    try:
        if not os.path.exists(LOGO_PATH):
            # If no logo found, show text fallback
            st.sidebar.markdown("**SAVILLS**")
            return
            
        # Load and display image
        with Image.open(LOGO_PATH) as img:
            st.sidebar.image(
                img, 
                width=IMG_WIDTH_PX,
                # use_container_width=True
            )
            
    except (FileNotFoundError, OSError) as e:
        # Handle file-related errors specifically
        st.sidebar.warning(f"Logo file error: {str(e)}")
        st.sidebar.markdown("**SAVILLS**")
        
    except Exception as e:
        # Handle any other unexpected errors
        st.sidebar.error(f"Unexpected error loading logo: {str(e)}")
        st.sidebar.markdown("**SAVILLS**")

def validate_storename_and_iso_time_mins_in_df(df, storename, iso_time_mins):
    """
    Validates if storename and iso_time_mins exist in the DataFrame columns and rows.
    
    Args:
        df: DataFrame to check
        storename: Store name to validate
        iso_time_mins: Time value to validate
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    # Check if DataFrame is valid
    if df is None:
        return False, "!!!!WARNING validate_storename_and_iso_time_mins_in_df DataFrame is None"
    
    if df.empty:
        return False, "!!!!WARNING validate_storename_and_iso_time_mins_in_df DataFrame is empty"
    
    # Check required columns exist
    required_cols = ['storename', 'iso_time_mins']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return False, f"!!!!WARNING validate_storename_and_iso_time_mins_in_df missing required columns: {missing_cols}"
    
    # Check if storename exists in the storename column
    if storename not in df['storename'].values:
        return False, f"!!!!WARNING validate_storename_and_iso_time_mins_in_df Storename '{storename}' not found in DataFrame"
    
    # Check if iso_time_mins exists in the iso_time_mins column
    if iso_time_mins not in df['iso_time_mins'].values:
        return False, f"!!!!WARNING validate_storename_and_iso_time_mins_in_df Time value '{iso_time_mins}' not found in DataFrame"
    
    # Check if the specific combination exists
    combination_exists = ((df['storename'] == storename) & 
                         (df['iso_time_mins'] == iso_time_mins)).any()
    
    if not combination_exists:
        return False, f"!!!!WARNING validate_storename_and_iso_time_mins_in_df Combination (storename: '{storename}', time: {iso_time_mins}) not found in DataFrame"
    
    return True, "***INFO validate_storename_and_iso_time_mins_in_df - Validation successful"
