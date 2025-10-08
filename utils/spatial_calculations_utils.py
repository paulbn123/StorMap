import streamlit as st

import numpy as np
from math import radians, sin, cos, sqrt, atan2

from config.constants import METRES_IN_KM

def haversine_distance_km(lat1, lon1, lat2, lon2):
    """
    Vectorized haversine distance calculation.
    Returns distance in kilometers (rounded to 2 decimal places).
    """
    # Convert to numpy arrays for vectorized operations
    lat1 = np.asarray(lat1)
    lon1 = np.asarray(lon1)
    lat2 = np.asarray(lat2)
    lon2 = np.asarray(lon2)
    
    R = 6371000  # Earth radius in meters
    
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    # Distance in km
    distance_km = (R * c) / METRES_IN_KM
    return np.round(distance_km, 2)

def haversine_distance_m(lat1, lon1, lat2, lon2):
    """
    Vectorized haversine distance calculation.
    Returns distance in meters unrounded
    """
    # Convert to numpy arrays for vectorized operations
    lat1 = np.asarray(lat1)
    lon1 = np.asarray(lon1)
    lat2 = np.asarray(lat2)
    lon2 = np.asarray(lon2)
    
    R = 6371000  # Earth radius in meters
    
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    # Distance in km
    distance_m = (R * c)
    return distance_m
