import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, shape
import openrouteservice as ors
from openrouteservice import client


from utils.spatial_calculations_utils import haversine_distance_m
from utils.load_save_data_files_utils import save_isochrone_gdf_to_file
from utils.spatial_processing_utils import is_valid_lat_lon

from config.constants import (
    ISO_TIME_MINS, 
    DEBUG_PRINT,
    ORS_API_KEY,
    DISTANCE_NEAREST_ISO_M,
    ISO_TIME_MINS_COL
)


class ORSClientManager:
    """Manages OpenRouteService client initialization and validation."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ORS client with error handling."""
        try:
            if not self.api_key:
                raise ValueError("ORS_API_KEY is not configured")
            
            self._client = ors.Client(key=self.api_key)
            print("****INFO ORS client initialized successfully")
            
        except Exception as e:
            print(f"!!!!ERROR Failed to initialize ORS client: {e}")
            self._client = None
    
    @property
    def client(self):
        """Get the ORS client instance."""
        return self._client
    
    @property
    def is_available(self):
        """Check if ORS client is available."""
        return self._client is not None


# Initialize ORS client manager
ors_manager = ORSClientManager(ORS_API_KEY)


def get_isos_from_confirmed_locations_df(df):
    """Process multiple locations to get isochrones.
    
    Args:
        df: DataFrame with columns ['name', 'lat', 'lng']
        
    Returns:
        GeoDataFrame with isochrones or None if failed
    """
    if df is None or df.empty:
        print("!!!!ERROR Invalid or empty DataFrame provided")
        return None
    
    required_cols = ['name', 'lat', 'lng']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        print(f"!!!!ERROR Missing required columns: {missing_cols}")
        print(f'df.columns: {df.columns}')
        return None
    
    results = []
    failed_stores = []
    
    for idx, row in df.iterrows():
        print(f'##################################################')
        print(f'*********   Processing store: {idx+1}        ************')
        print(f'##################################################')
        try:
            store_name = row['name']
            lat, lon = row['lat'], row['lng']
            
            gdf_temp = get_isos_from_lat_lon(lat, lon)
            
            if gdf_temp is not None and not gdf_temp.empty:
                gdf_temp['storename'] = store_name
                results.append(gdf_temp)
                
                if DEBUG_PRINT:
                    print(f"****INFO Successfully got isos for {store_name}")
            else:
                failed_stores.append(store_name)
                print(f"!!!WARNING Could not get isos for {store_name}")
                
        except Exception as e:
            failed_stores.append(row.get('name', f'row_{idx}'))
            print(f"!!!!ERROR Error processing row {idx}: {e}")
    
    if not results:
        print("!!!WARNING No isochrones were successfully processed")
        return None
    
    if failed_stores:
        print(f"!!!WARNING Failed to process stores: {failed_stores}")
    
    # Concatenate all results at once for better performance
    final_gdf = pd.concat(results, ignore_index=True)

    print(f'###############################################')
    print(f'*********   ISO Processing Complete      ************')
    print(f'###############################################')


    print(f"****INFO Successfully processed {len(results)} stores")
    
    return final_gdf


def get_isos_from_lat_lon(lat, lon):
    """Get isochrones for given coordinates.
    
    First tries to find existing isochrones within threshold distance,
    then fetches new ones from ORS if needed.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        GeoDataFrame with isochrones or None if failed
    """
    print(f"****INFO Processing isochrones for lat/lon: {lat}, {lon}")
    
    # Validate configuration
    if not _validate_configuration():
        st.error("Invalid isochrone configuration")
        return None
    
    # Validate coordinates
    if not is_valid_lat_lon(latitude=lat, longitude=lon):
        st.error(f"Invalid coordinates: lat={lat}, lon={lon}")
        return None
    
    try:
        # Try to get existing isochrones first
        existing_iso = _get_iso_from_existing_gdf(lat, lon)
        
        if existing_iso is not None and not existing_iso.empty:
            print("****INFO Found existing isochrones")
            return existing_iso
        
        # Fetch new isochrones from ORS
        print("****INFO Fetching new isochrones from ORS...")
        return _fetch_new_isochrones(lat, lon)
        
    except Exception as e:
        print(f"!!!!ERROR Failed to get isochrones for {lat}, {lon}: {e}")
        return None


def _validate_configuration():
    """Validate that all required configuration is present and valid."""
    try:
        # Check ISO_TIME_MINS
        if not ISO_TIME_MINS:
            print("!!!!ERROR ISO_TIME_MINS is not configured")
            return False
            
        if not isinstance(ISO_TIME_MINS, (list, tuple)):
            print("!!!!ERROR ISO_TIME_MINS must be a list or tuple")
            return False
            
        if not all(isinstance(t, (int, float)) and t > 0 for t in ISO_TIME_MINS):
            print("!!!!ERROR All values in ISO_TIME_MINS must be positive numbers")
            return False
        
        # Check ORS client
        if not ors_manager.is_available:
            print("!!!!ERROR ORS client is not available")
            return False
            
        return True
        
    except Exception as e:
        print(f"!!!!ERROR Configuration validation failed: {e}")
        return False


def _get_iso_from_existing_gdf(src_lat, src_lon, threshold_distance_m=None):
    """Search for existing isochrones within threshold distance.
    
    Args:
        src_lat: Source latitude
        src_lon: Source longitude  
        threshold_distance_m: Search radius in meters
        
    Returns:
        GeoDataFrame with closest isochrones or None if not found
    """
    if threshold_distance_m is None:
        threshold_distance_m = DISTANCE_NEAREST_ISO_M
        
    if threshold_distance_m <= 0:
        print("!!!!ERROR threshold_distance_m must be positive")
        return None
    
    try:
        # Safely access session state
        iso_data = st.session_state.get('data', {}).get('iso')
        if iso_data is None or iso_data.empty:
            print("****INFO No existing isochrone data found in session state")
            return None
        
        gdf_iso = iso_data.copy()
        
        # Validate GeoDataFrame
        if not _validate_geodataframe_structure(gdf_iso):
            return None
        
        # Add lat/lon columns if missing
        if 'latitude' not in gdf_iso.columns or 'longitude' not in gdf_iso.columns:
            gdf_iso['longitude'] = gdf_iso.geometry.x
            gdf_iso['latitude'] = gdf_iso.geometry.y
        
        # Calculate distances vectorized
        try:
            distances = haversine_distance_m(
                src_lat, src_lon,
                gdf_iso['latitude'].values,
                gdf_iso['longitude'].values
            )
            gdf_iso['distance_m'] = distances
            
        except Exception as e:
            print(f"!!!!ERROR Failed to calculate distances: {e}")
            return None
        
        # Filter and find closest isochrones
        filtered_gdf = gdf_iso[gdf_iso['distance_m'] <= threshold_distance_m].copy()

        if filtered_gdf.empty:
            print("****INFO No existing isochrones found within threshold distance")
            return None

        # Use groupby for better performance
        try:
            closest_iso = (filtered_gdf
                        .groupby(ISO_TIME_MINS_COL)
                        .apply(lambda x: x.loc[x['distance_m'].idxmin()])
                        .reset_index(drop=True))
            
            # Verify we have all required drive times
            found_times = set(closest_iso[ISO_TIME_MINS_COL].unique())
            required_times = set(ISO_TIME_MINS)
            
            if not required_times.issubset(found_times):
                missing = required_times - found_times
                print(f"****INFO Missing drive times in existing data: {missing}")
                return None
            
            # Clean up and return
            if 'distance_m' in closest_iso.columns:
                closest_iso = closest_iso.drop(columns=['distance_m'])
            
            # ENHANCED CRS HANDLING - SET CRS IF MISSING
            if not isinstance(closest_iso, gpd.GeoDataFrame):
                # Create GeoDataFrame and set CRS to 4326 if not defined
                closest_iso = gpd.GeoDataFrame(
                    closest_iso, 
                    geometry='geometry'
                )
            
            # If no CRS is defined, set it to EPSG:4326 (your known standard)
            if closest_iso.crs is None:
                print("****INFO Setting missing CRS to EPSG:4326")
                closest_iso.set_crs('EPSG:4326', inplace=True)
            
            # Only transform if not already in target CRS
            if not closest_iso.crs.equals('EPSG:4326'):
                closest_iso = closest_iso.to_crs('EPSG:4326')
            
            print(f"****INFO Found {len(closest_iso)} existing isochrones")
            return closest_iso
            
        except Exception as e:
            print(f"!!!!ERROR Failed to process closest isochrones: {e}")
            return None
            
    except Exception as e:
        print(f"!!!!ERROR _get_iso_from_existing_gdf failed: {e}")
        return None


def _validate_geodataframe_structure(gdf):
    """Validate GeoDataFrame has required structure."""
    try:
        if not isinstance(gdf, gpd.GeoDataFrame):
            print("!!!!ERROR Data is not a GeoDataFrame")
            return False
            
        if gdf.crs is None or str(gdf.crs).upper() != 'EPSG:4326':
            print("!!!WARNING GeoDataFrame does not have CRS of EPSG:4326")
            return False
            
        if 'geometry' not in gdf.columns:
            print("!!!!ERROR GeoDataFrame missing geometry column")
            return False
            
        if ISO_TIME_MINS_COL not in gdf.columns:
            print(f"!!!!ERROR GeoDataFrame missing {ISO_TIME_MINS_COL} column")
            return False
            
        return True
        
    except Exception as e:
        print(f"!!!!ERROR GeoDataFrame validation failed: {e}")
        return False


def _fetch_new_isochrones(lat, lon):
    """Fetch new isochrones from ORS and update storage."""
    try:
        # Get isochrone from ORS
        ors_response = _get_isochrone_from_ors(lat, lon)
        if ors_response is None:
            print("!!!!ERROR Failed to get isochrone from ORS")
            return None
        
        # Convert to GeoDataFrame
        gdf_new_iso = _ors_response_to_geodataframe(ors_response, lat, lon)
        if gdf_new_iso is None or gdf_new_iso.empty:
            print("!!!!ERROR Failed to convert ORS response to GeoDataFrame")
            return None
        
        # Update storage
        updated_gdf = _append_and_save_isochrones(gdf_new_iso)
        if updated_gdf is None:
            print("!!!WARNING Failed to update storage, but returning new isochrones")
        
        return gdf_new_iso
        
    except Exception as e:
        print(f"!!!!ERROR Failed to fetch new isochrones: {e}")
        return None


def _get_isochrone_from_ors(lat, lon):
    """Fetch isochrone data from OpenRouteService API."""
    try:
        if not ors_manager.is_available:
            print("!!!!ERROR ORS client is not available")
            return None
        
        # Prepare request parameters
        time_range_seconds = [int(time_minutes * 60) for time_minutes in ISO_TIME_MINS]
        search_location = [[lon, lat]]  # ORS expects [lon, lat]
        
        print(f"****INFO Requesting isochrones for location: {search_location}")
        if DEBUG_PRINT:
            print(f"****INFO Time ranges (seconds): {time_range_seconds}")
        
        # Make API request
        ors_response = client.isochrones(
            locations=search_location,
            profile='driving-car',
            range=time_range_seconds,
            validate=False,
            attributes=['total_pop'],
            client=ors_manager.client
        )
        
        # Validate response
        if not _validate_ors_response(ors_response):
            return None
        
        print("****INFO Successfully received ORS response")
        return ors_response
        
    except ors.exceptions.ApiError as e:
        print(f"!!!!ERROR ORS API Error: {e}")
        return None
    except Exception as e:
        print(f"!!!!ERROR Failed to get isochrone from ORS: {e}")
        return None


def _validate_ors_response(response):
    """Validate ORS API response structure."""
    if response is None:
        print("!!!!ERROR ORS returned None response")
        return False
        
    if not isinstance(response, dict):
        print("!!!!ERROR ORS response is not a dictionary")
        return False
        
    if 'features' not in response:
        print("!!!!ERROR ORS response missing features")
        return False
        
    if not response['features']:
        print("!!!!ERROR ORS response has empty features")
        return False
    
    return True


def _ors_response_to_geodataframe(ors_response, lat, lon):
    """Convert ORS response to GeoDataFrame with error handling."""
    try:
        features = ors_response.get('features', [])
        
        geometries = []
        properties_list = []
        
        # Process each feature
        for i, feature in enumerate(features):
            try:
                if 'geometry' not in feature or 'properties' not in feature:
                    print(f"!!!WARNING Feature {i} missing geometry or properties, skipping")
                    continue
                
                # Convert geometry
                geom = shape(feature['geometry'])
                if geom is None or geom.is_empty:
                    print(f"!!!WARNING Feature {i} has invalid geometry, skipping")
                    continue
                
                geometries.append(geom)
                properties_list.append(feature['properties'])
                
            except Exception as e:
                print(f"!!!WARNING Failed to process feature {i}: {e}")
                continue
        
        if not geometries or not properties_list:
            print("!!!!ERROR No valid features processed from ORS response")
            return None
        
        # Create GeoDataFrame
        properties_df = pd.DataFrame(properties_list)
        gdf = gpd.GeoDataFrame(properties_df, geometry=geometries, crs='EPSG:4326')
        
        # Clean up columns
        cols_to_drop = ['group_index', 'total_pop', 'center']
        existing_cols_to_drop = [col for col in cols_to_drop if col in gdf.columns]
        if existing_cols_to_drop:
            gdf = gdf.drop(columns=existing_cols_to_drop)
        
        # Add metadata
        gdf['latitude'] = lat
        gdf['longitude'] = lon
        
        # Convert value column to minutes
        if 'value' in gdf.columns:
            gdf = gdf.rename(columns={'value': ISO_TIME_MINS_COL})
            gdf[ISO_TIME_MINS_COL] = gdf[ISO_TIME_MINS_COL] / 60.0
        else:
            print("!!!!ERROR Missing 'value' column in ORS response")
            return None
        
        print(f"****INFO Successfully converted ORS response to GeoDataFrame with {len(gdf)} features")
        return gdf
        
    except Exception as e:
        print(f"!!!!ERROR Failed to convert ORS response to GeoDataFrame: {e}")
        return None


def _append_and_save_isochrones(new_iso):
    """Append new isochrones to existing data and save."""
    try:
        # Get existing data safely
        existing_data = st.session_state.get('data', {}).get('iso')
        
        if existing_data is not None and not existing_data.empty:
            # Ensure both GeoDataFrames have same CRS
            existing_data = existing_data.to_crs('EPSG:4326')
            new_iso = new_iso.to_crs('EPSG:4326')
            
            # Concatenate
            complete_iso = pd.concat([existing_data, new_iso], ignore_index=True)
            print(f"****INFO Appended {len(new_iso)} new isochrones to {len(existing_data)} existing")
        else:
            complete_iso = new_iso.copy()
            print("****INFO No existing isochrones, using new data only")
        
        # Clean up any temporary columns
        if 'distance_m' in complete_iso.columns:
            complete_iso = complete_iso.drop(columns=['distance_m'])
        
        # Save to file and update session state
        try:
            save_isochrone_gdf_to_file(complete_iso)
            
            # Ensure session state structure exists
            if 'data' not in st.session_state:
                st.session_state.data = {}
            
            st.session_state.data['iso'] = complete_iso
            print("****INFO Successfully updated isochrone storage")
            
        except Exception as e:
            print(f"!!!WARNING Failed to save isochrones to file: {e}")
            # Continue anyway - the data is still valid
        
        return complete_iso
        
    except Exception as e:
        print(f"!!!!ERROR Failed to append and save isochrones: {e}")
        return None


def get_iso_bounds(gdf_iso):
    """Get bounds for each isochrone time for map fitting.
    
    Args:
        gdf_iso: GeoDataFrame with isochrones
        
    Returns:
        Dictionary mapping drive times to bounds [[SW], [NE]] or None
    """
    try:
        if not _validate_geodataframe_structure(gdf_iso):
            return None
        
        bounds_dict = {}
        
        for _, row in gdf_iso.iterrows():
            iso_time = row[ISO_TIME_MINS_COL]
            
            if iso_time not in ISO_TIME_MINS:
                print(f"!!!WARNING Unexpected iso_time_mins value: {iso_time}")
                continue
            
            try:
                minx, miny, maxx, maxy = row.geometry.bounds
                # Format for folium: [[SW], [NE]]
                folium_bounds = [[miny, minx], [maxy, maxx]]
                bounds_dict[iso_time] = folium_bounds
                
            except Exception as e:
                print(f"!!!!ERROR Failed to get bounds for iso_time {iso_time}: {e}")
                continue
        
        if bounds_dict:
            print(f"****INFO Successfully created bounds for {len(bounds_dict)} isochrones")
            return bounds_dict
        else:
            print("!!!WARNING No valid bounds created")
            return None
            
    except Exception as e:
        print(f"!!!!ERROR Failed to create bounds dictionary: {e}")
        return None


def validate_iso_has_all_drive_times(gdf_iso):
    """Validate that isochrone GeoDataFrame contains all required drive times."""
    try:
        if ISO_TIME_MINS_COL not in gdf_iso.columns:
            print(f"!!!!ERROR Missing '{ISO_TIME_MINS_COL}' column")
            return False
            
        unique_times = set(gdf_iso[ISO_TIME_MINS_COL].unique())
        required_times = set(ISO_TIME_MINS)
        
        missing_times = required_times - unique_times
        if missing_times:
            print(f"!!!!ERROR Missing required drive times: {missing_times}")
            return False
            
        print("****INFO All required drive times present")
        return True
        
    except Exception as e:
        print(f"!!!!ERROR Failed to validate drive times: {e}")
        return False