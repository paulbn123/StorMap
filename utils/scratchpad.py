import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd

from utils.search_map_utils import create_search_map
from utils.clear_current_locations_utils import clear_current_locations_reset_app
from utils.process_locations import process_search_locations
from utils.spatial_processing_utils import is_valid_lat_lon
from utils.other_utils import add_savills_logo


from config.constants import (DEBUG_PRINT, 
                              DEFAULT_STORE_NAME, 
                              SEARCH_MAP_DISPLAY_HEIGHT_PX,
                              MAX_SSDB_MARKERS_TO_SHOW)





def bounds_to_key(bounds):
    """Convert bounds to a string key for caching."""
    if not bounds:
        return "no_bounds"
    try:
        south = bounds["_southWest"]["lat"]
        west = bounds["_southWest"]["lng"]
        north = bounds["_northEast"]["lat"]
        east = bounds["_northEast"]["lng"]
        return f"{south:.4f}_{west:.4f}_{north:.4f}_{east:.4f}"
    except (KeyError, TypeError):
        return "invalid_bounds"


def create_ssdb_feature_group(bounds):
    """Create SSDB feature group with caching."""
    if "data" not in st.session_state or "ssdb" not in st.session_state.data:
        if DEBUG_PRINT:
            print("****INFO create_ssdb_feature_group No SSDB data available")
        return None

    bounds_key = bounds_to_key(bounds)
    
    # Check if we have cached markers for these bounds
    if bounds_key in st.session_state.cached_ssdb_markers:
        if DEBUG_PRINT:
            print(f"****INFO create_ssdb_feature_group Using cached SSDB markers for bounds: {bounds_key}")
        return st.session_state.cached_ssdb_markers[bounds_key]

    gdf = st.session_state.data["ssdb"]

    if not bounds:
        if DEBUG_PRINT:
            print("****INFO create_ssdb_feature_group No bounds available")
        return None

    # Extract bounds and validate they exist
    try:
        south = bounds["_southWest"]["lat"]
        west = bounds["_southWest"]["lng"]
        north = bounds["_northEast"]["lat"]
        east = bounds["_northEast"]["lng"]
        
        # Check if any bounds are None
        if any(val is None for val in [south, west, north, east]):
            if DEBUG_PRINT:
                print("****INFO create_ssdb_feature_group Bounds contain None values")
            return None
            
    except (KeyError, TypeError) as e:
        if DEBUG_PRINT:
            print(f"****INFO create_ssdb_feature_group Error extracting bounds: {e}")
        return None

    if DEBUG_PRINT:
        print(f"****INFO Creating SSDB markers for bounds: S={south:.4f}, W={west:.4f}, N={north:.4f}, E={east:.4f}")
        print(f"\tTotal SSDB records: {len(gdf)}")

    try:
        # Filter GeoDataFrame to viewport
        if hasattr(gdf, 'cx'):
            gdf_view = gdf.cx[west:east, south:north]
        else:
            mask = (
                (gdf.geometry.x >= west) & (gdf.geometry.x <= east) &
                (gdf.geometry.y >= south) & (gdf.geometry.y <= north)
            )
            gdf_view = gdf[mask]
        
        gdf_view = gdf_view.reset_index(drop=True)
        
        # Limit to maximum markers
        if len(gdf_view) > MAX_SSDB_MARKERS_TO_SHOW:
            gdf_view = gdf_view.head(MAX_SSDB_MARKERS_TO_SHOW)
            if DEBUG_PRINT:
                print(f"****INFO create_ssdb_feature_group Limited SSDB results to {MAX_SSDB_MARKERS_TO_SHOW} records")

        if DEBUG_PRINT:
            print(f"****INFO create_ssdb_feature_group Filtered SSDB records in view: {len(gdf_view)}")

        if gdf_view.empty:
            if DEBUG_PRINT:
                print("*****INFO create_ssdb_feature_group No SSDB markers in current view")
            # Cache empty result
            st.session_state.cached_ssdb_markers[bounds_key] = None
            return None

        # Create the FeatureGroup for SSDB markers
        fg_ssdb = folium.FeatureGroup(name="SSDB Locations", show=True)
        
        markers_added = 0
        for idx, row in gdf_view.iterrows():
            try:
                lat = float(row.geometry.y)
                lng = float(row.geometry.x)
                store_name = row.get("storename", f"Store {idx}")
                
                if not is_valid_lat_lon(latitude=lat, longitude=lng):
                    if DEBUG_PRINT:
                        print(f"!!!!!WARNING create_ssdb_feature_group Invalid coordinates for {store_name}: lat={lat}, lng={lng}")
                    continue
                
                marker = folium.CircleMarker(
                    location=[lat, lng],
                    radius=5,
                    tooltip=store_name,
                    color="blue",
                    fillColor="lightblue",
                    fillOpacity=0.7,
                    weight=2,
                )
                fg_ssdb.add_child(marker)
                markers_added += 1
                
                if DEBUG_PRINT and idx < 5:
                    print(f"\tAdded marker: {store_name} at [{lat:.4f}, {lng:.4f}]")
                    
            except Exception as e:
                if DEBUG_PRINT:
                    store_name = row.get("storename", f"Store {idx}")
                    print(f'!!!!WARNING create_ssdb_feature_group Could not add marker for {store_name}: {str(e)}')

        if markers_added > 0:
            # Cache the feature group
            st.session_state.cached_ssdb_markers[bounds_key] = fg_ssdb
            if DEBUG_PRINT:
                print(f"****INFO create_ssdb_feature_group Successfully created and cached {markers_added} SSDB markers")
            return fg_ssdb
        else:
            if DEBUG_PRINT:
                print("****INFO create_ssdb_feature_group No SSDB markers were successfully added")
            # Cache empty result
            st.session_state.cached_ssdb_markers[bounds_key] = None
            return None

    except Exception as e:
        if DEBUG_PRINT:
            print(f"!!!!WARNING create_ssdb_feature_group Error filtering SSDB data: {str(e)}")
        return None


def create_pending_location_feature_group():
    """Create feature group for pending location."""
    if st.session_state.clicked_location is None:
        return None
    
    fg_pending = folium.FeatureGroup(name="Pending Location", show=True)
    lat, lng = st.session_state.clicked_location
    fg_pending.add_child(
        folium.Marker(
            [lat, lng],
            popup="Click 'Confirm Location' to add",
            tooltip="Pending Location",
            icon=folium.Icon(color="red")
        )
    )
    return fg_pending


def create_confirmed_locations_feature_group():
    """Create feature group for confirmed locations."""
    if st.session_state.search_locations_df.empty:
        return None
    
    fg_confirmed = folium.FeatureGroup(name="Confirmed Locations", show=True)
    for _, row in st.session_state.search_locations_df.iterrows():
        fg_confirmed.add_child(
            folium.Marker(
                [row.lat, row.lng],
                popup=f"{row['name']}",
                tooltip=row['name'],
                icon=folium.Icon(color="green")
            )
        )
    return fg_confirmed


def get_all_feature_groups():
    """Get all feature groups that should be displayed on the map."""
    feature_groups = []
    
    if DEBUG_PRINT:
        print("=== Creating Feature Groups ===")
    
    # Get current bounds
    bounds = st.session_state.get("map_bounds")
    
    # Add SSDB markers if available
    if "data" in st.session_state and "ssdb" in st.session_state.data and bounds:
        if DEBUG_PRINT:
            print(f"****INFO SSDB data available with {len(st.session_state.data['ssdb'])} records")
        fg_ssdb = create_ssdb_feature_group(bounds)
        if fg_ssdb:
            feature_groups.append(fg_ssdb)
            if DEBUG_PRINT:
                print(f"\tAdded SSDB feature group with name: {fg_ssdb.layer_name}")
        else:
            if DEBUG_PRINT:
                print("\tSSDB feature group was None")
    else:
        if DEBUG_PRINT:
            print(f"****INFO get_all_feature_groups SSDB not available - data exists: {'data' in st.session_state}, ssdb exists: {'ssdb' in st.session_state.get('data', {})}, bounds: {bounds is not None}")
    
    # Add pending location
    fg_pending = create_pending_location_feature_group()
    if fg_pending:
        feature_groups.append(fg_pending)
        if DEBUG_PRINT:
            print(f"****INFO get_all_feature_groups Added pending location feature group")
    
    # Add confirmed locations
    fg_confirmed = create_confirmed_locations_feature_group()
    if fg_confirmed:
        feature_groups.append(fg_confirmed)
        if DEBUG_PRINT:
            print(f"****INFO get_all_feature_groups Added confirmed locations feature group with {len(st.session_state.search_locations_df)} locations")
    
    if DEBUG_PRINT:
        print(f"****INFO Total feature groups: {len(feature_groups)}")
        for i, fg in enumerate(feature_groups):
            print(f"\tFeature group {i}: {fg.layer_name}")
    
    return feature_groups


############################################################################
############################################################################
############################################################################

class SearchUI:
    def __init__(self):

        #####################################
        # force sidebar to be hidden on init 
        #####################################

        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        if DEBUG_PRINT:
            print("****INFO Initializing SearchUI")

    def _confirm_location_callback(self):
        """Callback for confirming a location - designed to minimize reruns."""
        # Get the current value from the widget
        location_name = st.session_state.get("location_name_input", "").strip()
        
        if not location_name:
            return
            
        if st.session_state.get('clicked_location') is None:
            return
            
        lat, lng = st.session_state.clicked_location
        
        # Create new row
        new_row = pd.DataFrame([{
            "lat": lat,
            "lng": lng,
            "name": location_name
        }])
        
        # Append to existing DataFrame
        st.session_state.search_locations_df = pd.concat([
            st.session_state.search_locations_df,
            new_row
        ], ignore_index=True)
        
        # Clear state variables - but don't touch the widget key
        st.session_state.clicked_location = None
        st.session_state.tooltip_text = None
        if '_default_location_name' in st.session_state:
            del st.session_state._default_location_name
        
        if DEBUG_PRINT:
            print(f"****INFO Location confirmed: {location_name} at [{lat:.4f}, {lng:.4f}]")

    def _handle_map_click(self, map_data):
        """Handle map clicks without triggering immediate reruns."""
        if not map_data:
            return False
        
        # Store previous click data to compare
        prev_map_click = getattr(st.session_state, '_prev_map_click', None)
        prev_obj_click = getattr(st.session_state, '_prev_obj_click', None)
        
        current_map_click = map_data.get("last_clicked")
        current_obj_click = map_data.get("last_object_clicked")
        
        # Check if clicks are actually new
        map_click_changed = current_map_click != prev_map_click
        obj_click_changed = current_obj_click != prev_obj_click
        
        if not (map_click_changed or obj_click_changed):
            return False
        
        # Update stored click data
        st.session_state._prev_map_click = current_map_click
        st.session_state._prev_obj_click = current_obj_click
        
        new_location = None
        tooltip_text = None
        
        # Process the new click
        if current_obj_click and obj_click_changed:
            if "lat" in current_obj_click and "lng" in current_obj_click:
                new_location = (current_obj_click["lat"], current_obj_click["lng"])
                if map_data.get("last_object_clicked_tooltip"):
                    tooltip_text = map_data["last_object_clicked_tooltip"]
                if DEBUG_PRINT:
                    print(f'Object click detected: {new_location} with tooltip: {tooltip_text}')

        elif current_map_click and map_click_changed:
            if "lat" in current_map_click and "lng" in current_map_click:
                new_location = (current_map_click["lat"], current_map_click["lng"])
                if DEBUG_PRINT:
                    print(f'Map click detected: {new_location}')

        # Only update if we have a genuinely new location
        if new_location and st.session_state.get('clicked_location') != new_location:
            st.session_state.clicked_location = new_location
            st.session_state.tooltip_text = tooltip_text
            
            # Store the default name separately - don't set the widget key directly
            if tooltip_text:
                st.session_state._default_location_name = tooltip_text
            else:
                st.session_state._default_location_name = DEFAULT_STORE_NAME
            
            if DEBUG_PRINT:
                print(f'Setting new clicked location: {new_location}')
            return True
        
        return False

    def render_search_map(self):
        col_1, col_2 = st.columns([1, 5])

        with col_1:

            add_savills_logo()
            
            # Show SSDB data status
            if "data" in st.session_state and "ssdb" in st.session_state.data:
                ssdb_count = len(st.session_state.data["ssdb"])
                st.success(f"SSDB loaded: {ssdb_count} locations")
            else:
                st.warning("SSDB data not loaded")

        with col_2:

        
            if DEBUG_PRINT:
                debug_print_current_map_settings()


            # Create base map
            m = create_search_map()
            
            # Get all feature groups - this will include debug info
            feature_groups = get_all_feature_groups()
            
            if DEBUG_PRINT:
                print(f"****INFO About to render map with {len(feature_groups)} feature groups")

            # Use a stable map key - only change when we need to force a complete reset
            # Don't change the key just because locations change - let st_folium handle updates
            map_key = "search_map_stable"
            
            map_data = st_folium(
                m,
                feature_group_to_add=feature_groups,
                key=map_key,
                use_container_width=True,
                returned_objects=["last_clicked", 
                                  "bounds", 
                                  "last_object_clicked", 
                                  "last_object_clicked_tooltip"],
                height=SEARCH_MAP_DISPLAY_HEIGHT_PX
            )

            # Update bounds if changed - but don't trigger rerun
            if map_data and map_data.get("bounds"):
                current_bounds_key = bounds_to_key(map_data["bounds"])
                if st.session_state.get('last_bounds_key') != current_bounds_key:
                    st.session_state.map_bounds = map_data["bounds"]
                    st.session_state.last_bounds_key = current_bounds_key
                    
                    # Clear SSDB cache when bounds change significantly
                    if st.session_state.get('cached_ssdb_markers'):
                        st.session_state.cached_ssdb_markers = {}
                    
                    if DEBUG_PRINT:
                        print(f"Bounds updated: {current_bounds_key}")
                        # Force rerun to get new SSDB markers for new bounds
                        st.rerun()

            # Handle map clicks - avoid immediate rerun, use button callback instead
            click_detected = self._handle_map_click(map_data)
            
            # If we detected a new click, rerun to show the pending marker
            if click_detected:
                st.rerun()

        with col_1:
            # Display bounds info for debugging
            if DEBUG_PRINT and st.session_state.get("map_bounds"):
                bounds = st.session_state.map_bounds
                try:
                    sw_lat = bounds['_southWest']['lat']
                    sw_lng = bounds['_southWest']['lng']
                    ne_lat = bounds['_northEast']['lat']
                    ne_lng = bounds['_northEast']['lng']
                    st.text(f"Bounds Debug:\nSW: {sw_lat:.4f}, {sw_lng:.4f}\nNE: {ne_lat:.4f}, {ne_lng:.4f}")
                except:
                    st.text("Bounds: Invalid format")

            # Location naming input
            if st.session_state.get('clicked_location') is not None:
                lat, lng = st.session_state.clicked_location
                
                # Get default value from our separate storage, not widget key
                default_name = st.session_state.get('_default_location_name', DEFAULT_STORE_NAME)
                
                location_name = st.text_input(
                    "Name this location:",
                    value=default_name,
                    placeholder="Enter location name...",
                    key="location_name_input"
                )

                # Button will trigger callback and rerun
                if st.button("Confirm Location", on_click=self._confirm_location_callback):
                    # Clear any pending update flag
                    if 'pending_location_update' in st.session_state:
                        del st.session_state.pending_location_update
            else:
                st.info("Click on the map to select a location")

            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            # Show confirmed locations
            if not st.session_state.search_locations_df.empty:
                if st.button("Process Locations", type="primary"):
                    process_search_locations()

                header_text = f"Confirmed Locations ({len(st.session_state.search_locations_df)})"
                st.dataframe(
                    st.session_state.search_locations_df[['name']].rename(columns={'name': header_text}),
                    use_container_width=True,
                    height=150,
                    hide_index=True
                )

                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

                # Selectbox for deletion
                selected_to_delete = st.selectbox(
                    "Delete location:",
                    options=["Select..."] + st.session_state.search_locations_df["name"].tolist(),
                    key="location_selector"
                )

                if selected_to_delete != "Select..." and st.button("Remove Selected Location"):
                    st.session_state.search_locations_df = st.session_state.search_locations_df[
                        st.session_state.search_locations_df["name"] != selected_to_delete
                    ]
                    st.rerun()

                if st.button('Delete all locations', type="primary"):
                    # Clear all location data
                    st.session_state.clicked_location = None
                    st.session_state.search_locations_df = pd.DataFrame(columns=["lat", "lng", "name"])
                    if 'location_name_input' in st.session_state:
                        st.session_state.location_name_input = ""
                    if 'tooltip_text' in st.session_state:
                        st.session_state.tooltip_text = None
                    # Update app state
                    st.session_state.setdefault('app_data', {})['src_locations_selected'] = False
                    st.rerun()
            else:
                st.write("No confirmed locations yet")



##################################################################################
###################### DEBUG PRNTING FUNCTION ####################################
##################################################################################


def debug_print_current_map_settings():
    """Print comprehensive debug information about current map state."""
    print("\n" + "="*80)
    print("DEBUG MAP SETTINGS - Current Session State")
    print("="*80)
    
    # 1. Basic Session State Info
    print(f"Session State Keys: {list(st.session_state.keys())}")
    print(f"Session State Length: {len(st.session_state)}")
    
    # 2. Map Bounds Information
    print(f"\n--- MAP BOUNDS ---")
    bounds = st.session_state.get("map_bounds")
    if bounds:
        try:
            south = bounds["_southWest"]["lat"]
            west = bounds["_southWest"]["lng"]
            north = bounds["_northEast"]["lat"]
            east = bounds["_northEast"]["lng"]
            bounds_key = bounds_to_key(bounds)
            print(f"Bounds Key: {bounds_key}")
            print(f"SW Corner: lat={south:.6f}, lng={west:.6f}")
            print(f"NE Corner: lat={north:.6f}, lng={east:.6f}")
            print(f"Bounds Width: {abs(east - west):.6f}°")
            print(f"Bounds Height: {abs(north - south):.6f}°")
        except Exception as e:
            print(f"Error parsing bounds: {e}")
            print(f"Raw bounds: {bounds}")
    else:
        print("No bounds available")
    
    print(f"Last Bounds Key: {st.session_state.get('last_bounds_key', 'None')}")
    
    # 3. SSDB Data Status
    print(f"\n--- SSDB DATA ---")
    if "data" in st.session_state:
        if "ssdb" in st.session_state.data:
            ssdb_gdf = st.session_state.data["ssdb"]
            print(f"SSDB GeoDataFrame loaded: YES")
            print(f"SSDB Total records: {len(ssdb_gdf)}")
            print(f"SSDB Columns: {list(ssdb_gdf.columns)}")
            print(f"SSDB Geometry type: {type(ssdb_gdf.geometry.iloc[0]) if len(ssdb_gdf) > 0 else 'No data'}")
            
            # Check coordinate ranges
            if len(ssdb_gdf) > 0:
                try:
                    min_lat = ssdb_gdf.geometry.y.min()
                    max_lat = ssdb_gdf.geometry.y.max()
                    min_lng = ssdb_gdf.geometry.x.min()
                    max_lng = ssdb_gdf.geometry.x.max()
                    print(f"SSDB Lat range: {min_lat:.6f} to {max_lat:.6f}")
                    print(f"SSDB Lng range: {min_lng:.6f} to {max_lng:.6f}")
                    
                    # Check if any SSDB points are within current bounds
                    if bounds:
                        try:
                            south = bounds["_southWest"]["lat"]
                            west = bounds["_southWest"]["lng"]
                            north = bounds["_northEast"]["lat"]
                            east = bounds["_northEast"]["lng"]
                            
                            if hasattr(ssdb_gdf, 'cx'):
                                gdf_in_bounds = ssdb_gdf.cx[west:east, south:north]
                            else:
                                mask = (
                                    (ssdb_gdf.geometry.x >= west) & (ssdb_gdf.geometry.x <= east) &
                                    (ssdb_gdf.geometry.y >= south) & (ssdb_gdf.geometry.y <= north)
                                )
                                gdf_in_bounds = ssdb_gdf[mask]
                            
                            print(f"SSDB Records in current bounds: {len(gdf_in_bounds)}")
                            
                        except Exception as e:
                            print(f"Error checking SSDB bounds intersection: {e}")
                    
                except Exception as e:
                    print(f"Error analyzing SSDB coordinates: {e}")
        else:
            print("SSDB data not found in session_state.data")
    else:
        print("No data key in session_state")
    
    # 4. Cached SSDB Markers
    print(f"\n--- CACHED SSDB MARKERS ---")
    if hasattr(st.session_state, 'cached_ssdb_markers'):
        cache = st.session_state.cached_ssdb_markers
        print(f"Cache exists: YES")
        print(f"Cached bounds keys: {list(cache.keys())}")
        for key, value in cache.items():
            if value is None:
                print(f"  {key}: None (empty result)")
            else:
                # Try to count markers in the feature group
                marker_count = len(value._children) if hasattr(value, '_children') else 'Unknown'
                print(f"  {key}: FeatureGroup with {marker_count} children")
    else:
        print("No cached_ssdb_markers in session_state")
        print("Initializing cached_ssdb_markers...")
        st.session_state.cached_ssdb_markers = {}
    
    # 5. Location Data
    print(f"\n--- LOCATION DATA ---")
    print(f"Clicked location: {st.session_state.get('clicked_location', 'None')}")
    print(f"Tooltip text: {st.session_state.get('tooltip_text', 'None')}")
    print(f"Default location name: {st.session_state.get('_default_location_name', 'None')}")
    
    # Search locations DataFrame
    search_df = st.session_state.get('search_locations_df', pd.DataFrame())
    print(f"Search locations DataFrame:")
    print(f"  Shape: {search_df.shape}")
    print(f"  Columns: {list(search_df.columns) if not search_df.empty else 'Empty'}")
    if not search_df.empty:
        print(f"  Locations: {search_df['name'].tolist()}")
        for idx, row in search_df.iterrows():
            print(f"    {row['name']}: [{row['lat']:.6f}, {row['lng']:.6f}]")
    
    # 6. Map Click Data
    print(f"\n--- MAP CLICK DATA ---")
    print(f"Previous map click: {getattr(st.session_state, '_prev_map_click', 'None')}")
    print(f"Previous obj click: {getattr(st.session_state, '_prev_obj_click', 'None')}")
    
    # 7. App State
    print(f"\n--- APP STATE ---")
    app_data = st.session_state.get('app_data', {})
    print(f"App data keys: {list(app_data.keys())}")
    print(f"Source locations selected: {app_data.get('src_locations_selected', 'Not set')}")
    
    # 8. Widget States
    print(f"\n--- WIDGET STATES ---")
    print(f"Location name input: '{st.session_state.get('location_name_input', 'Not set')}'")
    print(f"Location selector: '{st.session_state.get('location_selector', 'Not set')}'")
    
    # 9. Feature Groups Analysis
    print(f"\n--- FEATURE GROUPS ANALYSIS ---")
    try:
        feature_groups = get_all_feature_groups()
        print(f"Total feature groups created: {len(feature_groups)}")
        for i, fg in enumerate(feature_groups):
            fg_name = getattr(fg, 'layer_name', 'Unknown')
            children_count = len(getattr(fg, '_children', []))
            print(f"  Group {i}: '{fg_name}' with {children_count} children")
            
            # Try to identify the type of feature group
            if 'SSDB' in fg_name:
                print(f"    -> SSDB feature group")
            elif 'Pending' in fg_name:
                print(f"    -> Pending location feature group")
            elif 'Confirmed' in fg_name:
                print(f"    -> Confirmed locations feature group")
                
    except Exception as e:
        print(f"Error analyzing feature groups: {e}")
    
    # 10. Constants and Configuration
    print(f"\n--- CONFIGURATION ---")
    try:
        print(f"DEBUG_PRINT: {DEBUG_PRINT}")
        print(f"MAX_SSDB_MARKERS_TO_SHOW: {MAX_SSDB_MARKERS_TO_SHOW}")
        print(f"SEARCH_MAP_DISPLAY_HEIGHT_PX: {SEARCH_MAP_DISPLAY_HEIGHT_PX}")
        print(f"DEFAULT_STORE_NAME: {DEFAULT_STORE_NAME}")
    except NameError as e:
        print(f"Some constants not accessible: {e}")
    
    print("="*80)
    print("END DEBUG MAP SETTINGS")
    print("="*80 + "\n")