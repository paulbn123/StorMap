import streamlit as st

DEBUG_PRINT = True

ISO_TIME_MINS = [5,10,15,20,25,30]

DEFAULT_MAP_CENTER_LATLON = [51.50, -0.15]
DEFAULT_MAP_ZOOM_START = 14
MIN_SEARCH_MAP_ZOOM = 9 # Controls furthest out you can see
MAX_SEARCH_MAP_ZOOM = 17 # Controls how close you can zoom in 
SSDB_MARKER_DISPLAY_ZOOM_DISPLAY_LEVEL = 10  # LEvel at which SSDB markers are shown
DEFAULT_TILE_LAYER = 'CartoDB Positron'
SEARCH_MAP_DISPLAY_HEIGHT_PX = 800
COMPETITION_MAP_DISPLAY_HEIGHT_PX = 800
DEMO_MAP_DISPLAY_HEIGHT_PX = 800
MAX_SSDB_MARKERS_TO_SHOW  = 150

POP_UP_MAX_WIDTH_PX = 300

DISPLAY_TAB_NAMES = ['Competition', 'Savills SS Score', 'Demographics', 'Data Summary']

DEFAULT_STORE_NAME = 'Store Location'
#### ORS => Needs to go to secrets
ORS_API_KEY = st.secrets("ORS_API_KEY")
DISTANCE_NEAREST_ISO_M = 250


# Popup settings for competition maps
HTML_BODY_FONT_SIZE = 12
HTML_H4_FONT_SIZE = 12
HTML_LINE_HEIGHT = 1.0 # This controls vertical space between lines smaller = tighter



ISO_TIME_MINS_COL = 'iso_time_mins'


class CRS:
    WGS84 = "EPSG:4326"
    UK_PLANAR = "EPSG:27700"
    EUROPEAN_PLANAR = "EPSG:3035"




#### ROUNDING + MAGIC NUMBERS
METRES_IN_KM = 1_000
SQM_IN_SQKM = 1_000_000
# DISTANCE_KM_COL = 'distance_km'
# DISTANCE_M_COL = 'distance_m'

# DISTANCE_KM_PRECISION_DECIMAL_PLACES = 2
# # MESSAGE_DISPLAY_SECONDS = 1
# MAX_OUTPUT_DATAFRAME_ROWS = 100