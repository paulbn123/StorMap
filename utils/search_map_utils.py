import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import folium
from folium.plugins import Geocoder
from config.constants import (DEFAULT_MAP_CENTER_LATLON, DEFAULT_MAP_ZOOM_START,
                              MIN_SEARCH_MAP_ZOOM, MAX_SEARCH_MAP_ZOOM,
                              DEFAULT_TILE_LAYER)


def initialize_search_map_session_state():
    """Initialize all necessary session state variables"""
    if 'app_data' not in st.session_state:
        st.session_state.app_data  = {}
    if 'map_center' not in st.session_state:
        st.session_state.map_center = DEFAULT_MAP_CENTER_LATLON
    if "map_bounds" not in st.session_state:
        st.session_state.map_bounds = None
    if 'map_zoom' not in st.session_state:
        st.session_state.map_zoom = DEFAULT_MAP_ZOOM_START
    if "location_name_input" not in st.session_state:
        st.session_state.location_name_input = ""
    if 'clicked_location' not in st.session_state:
        st.session_state.clicked_location = None
    if 'markers' not in st.session_state:
        st.session_state.markers = folium.FeatureGroup(name="Selected Locations")
    if 'search_locations_df' not in st.session_state:
        st.session_state.search_locations_df = pd.DataFrame(columns=["lat", "lng", "name"])
    if 'tooltip_text' not in st.session_state:
        st.session_state.tooltip_text = ''
    if "feature_groups" not in st.session_state:
        st.session_state.feature_groups = []
    if "cached_ssdb_markers" not in st.session_state:
        st.session_state.cached_ssdb_markers = {}
    if "last_bounds_key" not in st.session_state:
        st.session_state.last_bounds_key = None
    if "gdf_demo" not in st.session_state:
        st.session_state.gdf_demo = {}
    

def create_search_map():
    """Creates the search map with marker at clicked location using FeatureGroup"""

    # Use stored map center/zoom if available, else defaults
    center = st.session_state.get('map_center', DEFAULT_MAP_CENTER_LATLON)
    zoom = st.session_state.get('map_zoom', DEFAULT_MAP_ZOOM_START)

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        min_zoom=MIN_SEARCH_MAP_ZOOM,
        max_zoom=MAX_SEARCH_MAP_ZOOM,
        tiles=DEFAULT_TILE_LAYER
    )
    # Add layer control so they show in the UI
    folium.plugins.Geocoder().add_to(m)

    return m
