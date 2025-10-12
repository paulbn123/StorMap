import streamlit as st
import pandas as pd
import geopandas as gpd

from config.constants import DEBUG_PRINT, ISO_TIME_MINS


class AppState:
    """Class to define the structure of application state"""
    
    def __init__(self):
        # Store selection
        self.selected_storenames = []
        self.selected_storename = None
        
        # Drive time and filters
        self.selected_drive_time = None
        self.selected_storage_types = []
        self.selected_demo_gdf = None
        
        # Data objects
        self.gdf_competition = None
        self.gdf_demo = {}
        self.output_competition = None
        self.df_demo_summ = None


class SessionStateManager:
    """Centralized session state management for the Streamlit app"""
    
    # Define default values
    DEFAULTS = {
        'selected_storenames': [],
        'selected_storename': None,
        'selected_drive_time': 15,  # Default from ISO_TIME_MINS[2]
        'selected_storage_types': [],
        'selected_demo_gdf': None,
        'gdf_competition': None,
        'gdf_demo': {},
        'output_competition': None,
        'df_demo_summ': None,
    }
    
    @classmethod
    def initialize(cls, iso_time_mins=ISO_TIME_MINS):
        """Initialize session state with defaults if not already present"""

        # Set default drive time to middle value
        if 'selected_drive_time' not in st.session_state:
            cls.DEFAULTS['selected_drive_time'] = iso_time_mins[len(iso_time_mins)//2]
        
        for key, default_value in cls.DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    @classmethod
    def get_app_state(cls):
        """Get the current application state as a structured object"""
        app_state = AppState()
        app_state.selected_storenames = cls.get('selected_storenames', [])
        app_state.selected_storename = cls.get('selected_storename')
        app_state.selected_drive_time = cls.get('selected_drive_time')
        app_state.selected_storage_types = cls.get('selected_storage_types', [])
        app_state.selected_demo_gdf = cls.get('selected_demo_gdf')
        app_state.gdf_competition = cls.get('gdf_competition')
        app_state.gdf_demo = cls.get('gdf_demo', {})
        app_state.output_competition = cls.get('output_competition')
        app_state.df_demo_summ = cls.get('df_demo_summ')
        return app_state
    
    @classmethod
    def get(cls, key, default=None):
        """Safely get a value from session state"""
        return st.session_state.get(key, default)
    
    @classmethod
    def set(cls, key, value):
        """Set a value in session state"""
        st.session_state[key] = value
    
    @classmethod
    def update(cls, updates):
        """Update multiple session state values at once"""
        for key, value in updates.items():
            st.session_state[key] = value
    
    @classmethod
    def delete(cls, key):
        """Delete a key from session state if it exists"""
        if key in st.session_state:
            del st.session_state[key]
    
    @classmethod
    def clear_all(cls):
        """Clear all session state and reinitialize with defaults"""
        st.session_state.clear()
        cls.initialize()
    
    # Specific getters for commonly used values
    @classmethod
    def get_selected_storenames(cls):
        """Get the list of selected store names"""
        return cls.get('selected_storenames', [])
    
    @classmethod
    def get_selected_storename(cls):
        """Get the currently selected store name"""
        return cls.get('selected_storename')
    
    @classmethod
    def get_selected_drive_time(cls):
        """Get the selected drive time"""
        return cls.get('selected_drive_time', 15)
    

    
    @classmethod
    def get_selected_demo_gdf(cls):
        """Get the selected demographic GDF type"""
        return cls.get('selected_demo_gdf')
    

    
    @classmethod
    def get_gdf_demo(cls):
        """Get the demographic GeoDataFrames dictionary"""
        return cls.get('gdf_demo', {})
    

    
    @classmethod
    def get_df_demo_summ(cls):
        """Get the demographic summary DataFrame"""
        return cls.get('df_demo_summ')
    

    
    @classmethod
    def set_selected_drive_time(cls, drive_time):
        """Set the selected drive time"""
        cls.set('selected_drive_time', drive_time)
    

    
    @classmethod
    def set_selected_demo_gdf(cls, demo_gdf):
        """Set the selected demographic GDF type"""
        cls.set('selected_demo_gdf', demo_gdf)
    
    @classmethod
    def set_gdf_competition(cls, gdf):
        """Set the competition GeoDataFrame"""
        cls.set('gdf_competition', gdf)
    
    @classmethod
    def set_gdf_demo(cls, gdf_dict):
        """Set the demographic GeoDataFrames dictionary"""
        cls.set('gdf_demo', gdf_dict)
    
    @classmethod
    def set_output_competition(cls, df):
        """Set the competition output DataFrame"""
        cls.set('output_competition', df)
    
    @classmethod
    def set_df_demo_summ(cls, df):
        """Set the demographic summary DataFrame"""
        cls.set('df_demo_summ', df)
    
    # Validation methods
    @classmethod
    def validate_state(cls):
        """Validate current session state and return validation results"""
        validation = {}
        
        # Check if we have stores selected
        validation['has_stores'] = len(cls.get_selected_storenames()) > 0
        validation['has_selected_store'] = cls.get_selected_storename() is not None
        validation['has_competition_data'] = cls.get_gdf_competition() is not None
        validation['has_demo_data'] = len(cls.get_gdf_demo()) > 0
        validation['has_demo_summary'] = cls.get_df_demo_summ() is not None
        
        return validation
    




# Utility functions for backward compatibility and easy migration
def get_validated_gdf_from_app_data(gdf_name):
    """
    Backward compatibility function to replace the old utility function
    """
    if gdf_name == "gdf_competition":
        return SessionStateManager.get_gdf_competition()
    elif gdf_name in SessionStateManager.get_gdf_demo():
        return SessionStateManager.get_gdf_demo()[gdf_name]
    else:
        return None


def clear_current_locations_reset_app():
    """
    Clears session_state to return user to map 
    """
    initialize_search_map_session_state()
    session_state_defaults = {
        'selected_demo_gdf': None,
        'gdf_competition': None,
        'gdf_demo': {},
        'output_competition': None,
        'df_demo_summ': None,
        'search_locations_df': pd.DataFrame(columns=["lat", "lng", "name"]),
        'src_locations_selected' : False # this is the key rigger to show searhc UI
    }
    
    for k, v in session_state_defaults.items():
        st.session_state[k] = v

    # Making sure the key search UI from the map is cleared
    if 'location_name_input' in st.session_state:
        st.session_state.location_name_input = ""
    if 'tooltip_text' in st.session_state:
        st.session_state.tooltip_text = None
    st.session_state.clicked_location = None

    st.rerun()
