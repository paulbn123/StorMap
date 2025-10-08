import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.wkb import dumps as wkb_dumps
from shapely.wkb import loads as wkb_loads

WKB_EXTENSION = '_wkb' # added to geom cols converted to WKB

def load_gdf_from_parquet(fpath_load, epsg=4326, geometry_col=None):
    """
    Load Parquet file and convert WKB columns back to geometry.
    Return as a GeoDataFrame.
    """
    try:
        # Load the DataFrame from Parquet
        df = pd.read_parquet(fpath_load)
    except FileNotFoundError:
        raise FileNotFoundError(f"Parquet file not found: {fpath_load}")
    except Exception as e:
        raise Exception(f"Error reading parquet file: {e}")
    
    # Find all WKB columns
    wkb_columns = [col for col in df.columns if col.endswith(WKB_EXTENSION)]
    if not wkb_columns:
        raise ValueError(f"No columns ending with '{WKB_EXTENSION}' found in the parquet file")
    
    # Convert WKB columns back to geometry
    geometry_columns = []
    failed_conversions = []
    
    for col in wkb_columns:
        new_col_name = col.removesuffix(WKB_EXTENSION)  # More explicit than replace
        
        try:
            # Handle potential None/NaN values in WKB data
            df[new_col_name] = df[col].apply(
                lambda x: wkb_loads(x) if pd.notna(x) and x is not None else None
            )
            geometry_columns.append(new_col_name)
        except Exception as e:
            print(f"!!!!WARNING Failed to convert WKB column '{col}': {e}")
            continue
        
        # Drop the original WKB column
        df = df.drop(columns=[col])
    
    if not geometry_columns:
        raise ValueError("No WKB columns could be successfully converted to geometry")
    
    # Determine which geometry column to use
    if geometry_col:
        if geometry_col not in geometry_columns:
            raise ValueError(f"Specified geometry column '{geometry_col}' not found. "
                           f"Available geometry columns: {geometry_columns}")
        primary_geom_col = geometry_col
    else:
        primary_geom_col = geometry_columns[0]
        if len(geometry_columns) > 1:
            print(f"!!!!WARNING Multiple geometry columns found: {geometry_columns}. "
                         f"Using '{primary_geom_col}' as primary geometry.")
    
    # Create GeoDataFrame
    try:
        gdf = gpd.GeoDataFrame(df, geometry=primary_geom_col, crs=f"EPSG:{epsg}")
    except Exception as e:
        raise Exception(f"Error creating GeoDataFrame: {e}")
    
    return gdf

def save_gdf_to_parquet(gdf_to_save, fpath_save, geometry_cols_list=['geometry']):
    """
    Save iso_gdf to a Parquet file after converting geometry columns to WKB
    """
    
    # Make a copy of the GeoDataFrame to be absolutely sure to avoid modifying the original
    gdf_to_save = gdf_to_save.copy()

    for col in geometry_cols_list:
        new_col_name = col + WKB_EXTENSION
        # Convert geometry columns to WKB
        gdf_to_save[new_col_name] = gdf_to_save[col].apply(wkb_dumps)
        # drop the original geom column
        gdf_to_save = gdf_to_save.drop(columns=[col])
        
    # Save the DataFrame to Parquet
    gdf_to_save.to_parquet(fpath_save, engine='pyarrow')
    print(f'****INFO Saved GeoDataFrame to {fpath_save}')