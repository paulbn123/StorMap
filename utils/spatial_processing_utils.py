import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np

from config.constants import DEBUG_PRINT

def check_crs_match(gdf1, gdf2, raise_error=False):
    """Check if two GeoDataFrames have matching CRS, handling edge cases."""
    
    # Check if either has no CRS defined
    if gdf1.crs is None or gdf2.crs is None:
        if raise_error:
            raise ValueError("!!!!WARNING One or both GeoDataFrames have no CRS defined")
        return False
    
    if DEBUG_PRINT:

        print(f'****INFO checking matching crs in check_crs_match')
        print(f'\tcrs 1: {gdf1.crs}')
        print(f'\tcrs 2: {gdf2.crs}')
        print(f'\tcrs match: {gdf1.crs == gdf2.crs}')

    # Use equals method for proper CRS comparison (more robust than !=)
    if not gdf1.crs.equals(gdf2.crs):
        if raise_error:
            raise ValueError(f"CRS mismatch: {gdf1.crs} vs {gdf2.crs}")
        return False
    
    return True


def is_valid_lat_lon(latitude, longitude):
    """
    Check if the provided latitude and longitude are valid.

    Parameters
    ----------
    latitude : float or int
        Latitude value to check.
    longitude : float or int
        Longitude value to check.

    Returns
    -------
    bool
        True if latitude is between -90 and 90 and longitude is between -180 and 180.
        False otherwise.
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False

    return -90 <= lat <= 90 and -180 <= lon <= 180


def get_bounds_from_gdf(gdf):
    """Returns bounds of the gdf in form [southwest, northeast]
    or None if error"""
    try:
        bounds = gdf.bounds
        if not bounds.empty:
            southwest = [bounds.miny.iloc[0], bounds.minx.iloc[0]]
            northeast = [bounds.maxy.iloc[0], bounds.maxx.iloc[0]]
            return [southwest, northeast]
    except:
        print(f'!!!!WARNING get_bounds_from_gdf was unable to get bounds from input gdf')
        return None