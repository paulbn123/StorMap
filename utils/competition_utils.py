import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from html import escape
import folium
from streamlit_folium import st_folium

from utils.load_save_data_files_utils import get_ssdb_from_ss, get_store_isos_from_ss

from utils.spatial_processing_utils import check_crs_match, get_bounds_from_gdf
from utils.dataframe_handling_utils import all_required_cols_in_df
from utils.spatial_calculations_utils import haversine_distance_km

from config.constants import (DEBUG_PRINT, 
                              DEFAULT_TILE_LAYER, 
                              COMPETITION_MAP_DISPLAY_HEIGHT_PX,
                              POP_UP_MAX_WIDTH_PX,
                              HTML_BODY_FONT_SIZE,
                              HTML_H4_FONT_SIZE,
                                HTML_LINE_HEIGHT )

def process_competition_with_isochrones():
    """Function captures the competion by clipping the ssdb by the isochrones"""
    
    if DEBUG_PRINT:
        print(f'#################################################')
        print(f'****INFO running process_competition_with_isochrones')
        print(f'#################################################')

    # check the session state has ssdb in data - hnadled in data load function
    gdf_ssdb_4326 = get_ssdb_from_ss()
    required_ssdb_cols = ['storename', 'address', 'city', 'area_unit', 'store_mla', 'store_cla' ,'ss_type',  'geometry'] 
    if not all_required_cols_in_df(gdf_ssdb_4326, required_ssdb_cols):
        if DEBUG_PRINT:
            print(f'!!!!WARNING process_competition_with_isochrones found missing cols from gdf_ssdb_4326')
        return None
    # Filter and rename 
    gdf_ssdb_4326 = gdf_ssdb_4326[required_ssdb_cols]
    gdf_ssdb_4326.rename(columns={'storename':'Competitor'}, inplace=True) # OTherwise this will match storename from isos

    # get the isochrones from session_state
    gdf_store_isos_4236 = get_store_isos_from_ss()
    required_iso_cols = ['storename', 'iso_time_mins', 'latitude', 'longitude', 'geometry']
    if not all_required_cols_in_df(gdf_store_isos_4236, required_iso_cols):
        if DEBUG_PRINT:
            print(f'!!!!WARNING process_competition_with_isochrones found missing cols from gdf_store_isos_4236')
        return None
    # Filter and rename
    gdf_store_isos_4236 = gdf_store_isos_4236[required_iso_cols]
    gdf_store_isos_4236.rename(columns={'latitude': 'src_latitude', 'longitude':'src_longitude'}, inplace=True)

    # Check that the crs match - expected that these will both be 4236
    check_crs_match(gdf_store_isos_4236, gdf_ssdb_4326, raise_error=True)

    gdf_comp_in_iso_4326 = gpd.sjoin(gdf_ssdb_4326, 
                                gdf_store_isos_4236, 
                                how='inner', 
                                predicate='intersects')
    
    # Apply vectorized haversine distance
    gdf_comp_in_iso_4326["distance_km"] = haversine_distance_km(
                                        gdf_comp_in_iso_4326["src_latitude"].values,
                                        gdf_comp_in_iso_4326["src_longitude"].values,
                                        gdf_comp_in_iso_4326.geometry.y.values,
                                        gdf_comp_in_iso_4326.geometry.x.values,
                                    )
    _cols_to_drop = ['index_right']  # => Keep these for plotting of source store, 'src_latitude', 'src_longitude']
    for col in _cols_to_drop:
        if col in gdf_comp_in_iso_4326.columns:
             gdf_comp_in_iso_4326.drop(columns=[col], inplace=True)

    # as there are strings in the area columns need to coerce to errors before creating hmtml from them
    _integer_cols = ['store_cla', 'store_mla']
    for col in _integer_cols:
        gdf_comp_in_iso_4326[col] = pd.to_numeric(gdf_comp_in_iso_4326[col], errors='coerce')

    # Create html for popup
    gdf_comp_in_iso_4326['popup_text'] = gdf_comp_in_iso_4326.apply(create_popup_text_html, axis=1)

    gdf_comp_in_iso_4326 = gdf_comp_in_iso_4326.sort_values(by=['storename', 'iso_time_mins', 'distance_km'], 
                                                            ascending=[True, True, True])
    
    if DEBUG_PRINT:
        print(f'****INFO process_competition_with_isochrones joined gdf_store_isos_4236, gdf_ssdb_4326')
        print(f'****INFO process_competition_with_isochrones {gdf_comp_in_iso_4326.columns}')

        try:
            fpath_test = r'D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_competition.gpkg'
            gdf_comp_in_iso_4326.to_file(fpath_test, 
                                 driver='GPKG')
            print(f'****INFO Successfully save gdf_comp_in_iso_4326 to {fpath_test}')
        except:
            print(f'!!!!WARNING failed to save test version of gdf_comp_in_iso_4326')

    return gdf_comp_in_iso_4326

def get_output_iso(drive_time, storename):
    """This function gets the iso for the specified drive time 
    Returns one row gdf or None"""
    _gdf_isos = st.session_state.get("gdf_isos")
    if (_gdf_isos is None or drive_time is None or storename is None): 
        print(f'!!!!WARNING get_output_iso could not get gdf_isos from session_state or storename or drivetime was None')
        return None
    _gdf_isos_filtered = _gdf_isos[(_gdf_isos.iso_time_mins == drive_time) & (_gdf_isos.storename == storename)].copy()
    if _gdf_isos_filtered.empty:
        print(f'!!!!WARNING get_output_iso could not find matches for {storename} {drive_time}')
        print(f'****INFO _gdf_isos {_gdf_isos.shape}')
        print(f'****INFO _gdf_isos {_gdf_isos}')
        return None
    else:
        return _gdf_isos_filtered.iloc[0:1] 


def get_output_competition(drive_time, storename):
    """Function returns gdf for all compeition within speicifed drive_time for specified store
    Returns gdf or None"""
    _gdf_comp = st.session_state.get("gdf_competition")
    if (_gdf_comp is None or drive_time is None or storename is None): 
        print(f'!!!!WARNING get_output_competition could not get gdf_iso from session_state')
        return None
    _gdf_comp_filtered = _gdf_comp[(_gdf_comp.iso_time_mins == drive_time) & (_gdf_comp.storename == storename)].copy()
    if _gdf_comp_filtered.empty:
        print(f'!!!!WARNING get_output_iso could not find matches for {storename} {drive_time}')
        return None
    else:
        return _gdf_comp_filtered


def update_competition_data():

    """
     Filter and update competition data in session state based on current radio button selections.
     Filtering is done on storename / iso_time_mins / the list of storage types
    This should be called whenever radio button values change.
    """
    # Get selected values from radio buttons
    selected_storename = st.session_state.get("selected_storename")
    selected_drive_time = st.session_state.get("selected_drive_time")
    
    # # Get geodataframes from session state
    # gdf_isos = st.session_state.get("gdf_isos")
    # gdf_competition = st.session_state.get("gdf_competition")
    
    print(f'******************************')
    print(f'Checking gdf comp outputs - iso and competition')
    print(f'******************************')
    
    # # Initialize output data as None
    st.session_state["output_iso"] = get_output_iso(storename=selected_storename,
                                                    drive_time=selected_drive_time)
    st.session_state["output_competition"]  = get_output_competition(storename=selected_storename,
                                                            drive_time=selected_drive_time)
    
    # # Check if required data exists and filter
    # if (gdf_isos is not None and gdf_competition is not None and 
    #     selected_storename is not None and selected_drive_time is not None):
        
    #     try:
    #         # Additional safety checks before filtering
    #         if (isinstance(gdf_isos, gpd.GeoDataFrame) and isinstance(gdf_competition, gpd.GeoDataFrame) and
    #             not gdf_isos.empty and not gdf_competition.empty and
    #             hasattr(gdf_isos, 'iso_time_mins') and hasattr(gdf_isos, 'storename') and 
    #             hasattr(gdf_competition, 'iso_time_mins') and hasattr(gdf_competition, 'storename') and
    #             'iso_time_mins' in gdf_isos.columns and 'storename' in gdf_isos.columns and
    #             'iso_time_mins' in gdf_competition.columns and 'storename' in gdf_competition.columns):
                
    #             # Check if selected values exist in the data
    #             if (selected_storename in gdf_isos['storename'].values and 
    #                 selected_drive_time in gdf_isos['iso_time_mins'].values and
    #                 selected_storename in gdf_competition['storename'].values):
                    
    #                 # Filter gdf_isos
    #                 filtered_iso = gdf_isos[
    #                     (gdf_isos.iso_time_mins == selected_drive_time) & 
    #                     (gdf_isos.storename == selected_storename)
    #                 ]
                    
    #                 # Only store if we have exactly one result
    #                 if len(filtered_iso) == 1:
    #                     output_iso = filtered_iso
                        
    #                     # Filter gdf_competition
    #                     output_competition = gdf_competition[
    #                         (gdf_competition.storename == selected_storename) & 
    #                         (gdf_competition.iso_time_mins == selected_drive_time) &
    #                         (gdf_competition['ss_type'].isin(st.session_state.get('selected_storage_types', [])))
    #                     ]
        
    #     except Exception as e:
    #         if DEBUG_PRINT:
    #             print(f"Error filtering competition data: {str(e)}")
    #         # Ensure outputs remain None on any error
    #         output_iso = None
    #         output_competition = None
    
    # # Store filtered data in session state


def render_competition_map():
    """
    Renders a Folium map based on filtered data from session state.
    Returns st.write('Could not find data') if data is missing or invalid.
    """
    if DEBUG_PRINT:
        print(f'****INFO Rendering competition map')

    selected_drive_time = st.session_state.get("selected_drive_time")
    selected_store = st.session_state.get("selected_storename")

    print(f'****INFO render_competition_map selected_store: {selected_store} selected drive time: {selected_drive_time}')

    # Get filtered data from function
    gdf_output_competition = get_output_competition(storename=selected_store,
                                                  drive_time=selected_drive_time)
    
    gdf_output_iso = get_output_iso(storename=selected_store,
                                                  drive_time=selected_drive_time)

    if gdf_output_competition is  None or gdf_output_iso is None:
        print(f'!!!!!WARNING render_competition_map either output_iso or output_competition is None')
        return st.write(f'Was not able to render map - please try different parameters')
    
    try:
        #########################################
        # Create base map
        #########################################
        m = folium.Map(tiles=DEFAULT_TILE_LAYER)
        

        ################################################################
        # Add ISO boundary to map with styling (no fill, just lines) 
        #  Ensures that only one row is ever returned
        #################################################################
        
        iso_style = {
            'fillColor': 'transparent',
            'color': 'black',
            'weight': 1.5,
            'fillOpacity': 0,
            'opacity': 0.8
        }
        if gdf_output_iso is not None:
            folium.GeoJson(
                gdf_output_iso.iloc[0].geometry.__geo_interface__,
                style_function=lambda x: iso_style
            ).add_to(m)
        
        ###################################################################
        # Add competition - competition is any store where distance is greater than 0
        ###################################################################

        if DEBUG_PRINT:
            print(f'*****INFO output_competition: {gdf_output_competition.columns}')

        subject_store_marker_plotted_has_been_rendered = False
        # Add competition points as circle markers
        for idx, row in gdf_output_competition.iterrows():
            if row.distance_km > 0:  # ie not subject store 
                if hasattr(row.geometry, 'coords'):
                    # Point geometry
                    coords = list(row.geometry.coords)[0]
                    lat, lon = coords[1], coords[0]  # Note: folium expects (lat, lon)
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=8,
                        popup=folium.Popup(
                            str(row.get('popup_text', 'No competitor info')),
                            max_width=POP_UP_MAX_WIDTH_PX),
                        tooltip=str(row.get('Competitor', 'No popup text')),
                        color='blue',
                        fill=True,
                        fillColor='blue',
                        fillOpacity=0.6
                    ).add_to(m)
            else:
                subject_store_marker_plotted_has_been_rendered = True
                if hasattr(row.geometry, 'coords'):
                        # Point geometry
                        coords = list(row.geometry.coords)[0]
                        lat, lon = coords[1], coords[0]  # Note: folium expects (lat, lon)
                        
                        if DEBUG_PRINT:
                            print(f"****INFO adding marker for subject store at lat/lon: {lat} {lon}")

                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            popup=folium.Popup(
                                str(row.get('popup_text', 'Subject location')),
                                max_width=POP_UP_MAX_WIDTH_PX),
                            tooltip=str(row.get('Competitor', 'Subject location')),
                            color='green',
                            fill=True,
                            fillColor='green',
                            fillOpacity=0.6
                        ).add_to(m)

        ############################################################################
        # plot the subject store if not plotted already
        ############################################################################
        if not subject_store_marker_plotted_has_been_rendered:
            if DEBUG_PRINT:
                print(f"****INFO no marker for subject store was been found in df")  
    
            # If the subject store has not been printed then we are looking at a point on map - which will be src_latitude and src_longitude
            first_row = gdf_output_competition.iloc[[0]]
            lat = row.src_latitude
            lon = row.src_longitude

            if DEBUG_PRINT:
                print(f"****INFO adding marker for subject store at lat/lon: {lat} {lon} based on src_")

            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                popup=folium.Popup(
                    'Subject location',
                    max_width=POP_UP_MAX_WIDTH_PX),
                tooltip='Subject location',
                color='green',
                fill=True,
                fillColor='green',
                fillOpacity=0.6
            ).add_to(m)
                        
        #############################################################################
        # Fit bounds to ISO extent
        #############################################################################
        if gdf_output_iso is not None:

            bounds = get_bounds_from_gdf(gdf_output_iso)
            if bounds is not None:
                m.fit_bounds(bounds)
        
        # Render the map
        return st_folium(
            m,
            width="100%",
            height=COMPETITION_MAP_DISPLAY_HEIGHT_PX,
            returned_objects=[]
        )
        
    except Exception as e:
        print(f'!!!!WARNING error on render_competion_map')
        st.error(f"Error rendering map: {str(e)}")
        return st.write('Could not find data')

def render_competition_header():
    """Function sets out summary of selected gdf in terms of number of stores in catchment area"""
    selected_storename = st.session_state.get("selected_storename")
    selected_drive_time = st.session_state.get("selected_drive_time")
    
    # Get filtered data from session state
    gdf_output_competition = get_output_competition(storename=selected_storename,
                                                  drive_time=selected_drive_time)
    
    if gdf_output_competition is not None:
        competition_count = len(gdf_output_competition.index)
        output_text = f'{selected_storename}: {competition_count} competing stores ({selected_drive_time:d} min drive time)'
    else:
        output_text = f'{selected_storename}: No data available ({selected_drive_time:d} min drive time)'
    
    return st.write(output_text)


def render_competition_data_header():
    
    """Function creates header for data summary tab / competition"""
    selected_storename = st.session_state.get("selected_storename")
    selected_drive_time = st.session_state.get("selected_drive_time")
    
    if (selected_storename is not None and selected_drive_time is not None):
        output_text = f'{selected_storename} - {selected_drive_time:d} min drive time'
    else:
        output_text = f'Competition summary'
    
    return st.write(output_text)

# Alternative approach: Using st.data_editor for more interactive experience
def render_competition_data_summary_with_editor():
    """Shows competion in a rendered df with  delete functionality"""

    _selected_storename = st.session_state.get("selected_storename")
    _selected_drive_time = st.session_state.get("selected_drive_time")
    _ss_types = st.session_state.get("selected_storage_types")

    gdf_competition = get_output_competition(storename= _selected_storename, drive_time=_selected_drive_time)

    if gdf_competition is None:
        print(f'!!!!WARNING render_competition_data_summary_with_editor did not get any competion to render')
        return None
    

    print(f'***INFO render_competition_data_summary_with_editor ss_types: {_ss_types}')

    _df_competition_filtered = gdf_competition[(gdf_competition.ss_type.isin(_ss_types))].copy()

    _df_competition_columns = ['Competitor', 'address', 'ss_type', 'store_cla', 'store_mla', 'distance_km']
    df_output = _df_competition_filtered[_df_competition_columns].copy()
    
    # Add a delete checkbox column
    df_output.insert(0, 'Delete', False)
    
    _integer_cols = ['store_cla', 'store_mla']
    for col in _integer_cols:
        if col in df_output.columns:
            # Convert to numeric first, coercing errors to NaN
            df_output[col] = pd.to_numeric(df_output[col], errors='coerce')
            df_output[col] = df_output[col].round(0)
            df_output[col] = df_output[col].fillna(0).replace([np.inf, -np.inf], 0).astype(int)

    # Use data_editor for interactive editing
    edited_df = st.data_editor(
        df_output,
        hide_index=True,
        column_config={
            "Delete": st.column_config.CheckboxColumn(
                "Delete",
                help="Check to mark for deletion",
                default=False,
            )
        }
    )
    
    # Process deletions
    # Note the app renders gdf_outputs but the is drawn from gdf_competition - if we delete from output_competition 
    # when the app re-creates output_competition it will still have the store in it
    if st.button("Delete Competitor"):
        rows_to_delete = edited_df[edited_df['Delete'] == True]
        if len(rows_to_delete) > 0:
            competititors_to_delete = rows_to_delete['Competitor'].tolist()

            if DEBUG_PRINT:
                print(f'*****INFO render_competition_data_summary_with_editor competititors_to_delete: {competititors_to_delete}')
                print(f'\tcurrent length of output_competion: {len(st.session_state.get("output_competition").index)}')
             
            # Remove rows from session state
            mask = ~st.session_state.output_competition['Competitor'].isin(competititors_to_delete)
            st.session_state.gdf_competition = gdf_competition[mask]
            
            if DEBUG_PRINT:
                print(f'\tLength of  st.session_state.gdf_competition after deletion: {len(st.session_state.gdf_competition.index)}')

            st.success(f"Deleted {len(competititors_to_delete)} rows")
            st.rerun()
        else:
            st.warning("No rows marked for deletion")
    
    return edited_df

def summarise_competition(df_competition):
    """Summarises competition and updates st.session_state.competition_summary"""
    print(f'****INFO summarise_competition called')
    
    _required_cols = ['storename', 'iso_time_mins', 'store_cla', 'store_mla']
    missing_cols = [col for col in _required_cols if col not in df_competition.columns]
    
    if missing_cols:
        print(f'!!!!WARNING summarise_competition missing columns: {missing_cols}')
        return None
    
    try:
        # Work on copy
        df = df_competition.copy()
        
        # Convert to numeric
        df['store_cla'] = pd.to_numeric(df['store_cla'], errors='coerce')
        df['store_mla'] = pd.to_numeric(df['store_mla'], errors='coerce')
        
        # Group and aggregate
        _df_grouped = df.groupby(['storename', 'iso_time_mins']).agg({
            'store_cla': 'sum',
            'store_mla': 'sum'
        }).reset_index()
        
        # Add count
        _df_grouped['competition_count'] = df.groupby(['storename', 'iso_time_mins']).size().values
        
        st.session_state.competition_summary = _df_grouped
        print('*' * 20)
        print(_df_grouped)
        print('*' * 20)

        return _df_grouped
        
    except Exception as e:
        print(f'!!!!WARNING summarise_competition error: {e}')
        return None

def get_competition_summary_outputs(storename, iso_time_mins):
    """Function gets key values from competition summary
    returns Number of competing stores in catchment, total cla, total mla
    or None"""

    _competition_summary = st.session_state.get('competition_summary')
    
    # Check if competition_summary exists and is a DataFrame
    if _competition_summary is None:
        print(f'!!!!WARNING get_competition_summary_outputs: competition_summary not found in session_state')
        return None
        
    try:
        # Create a copy to avoid modifying the original
        df = _competition_summary.copy()
        
        # Apply the filter mask
        mask = (df['storename'] == storename) & (df['iso_time_mins'] == iso_time_mins)
        filtered_df = df[mask]
        
        # Check if any rows match the filter criteria
        if filtered_df.empty:
            print(f'!!!!WARNING get_competition_summary_outputs: No matching records found for {storename}, {iso_time_mins}')
            return None
        
        # Get the first matching row as a Series
        result_row = filtered_df.iloc[0]
        
        # Extract values directly from the Series
        competition_count = result_row['competition_count']
        store_mla = result_row['store_mla']
        store_cla = result_row['store_cla']
        
        return competition_count, store_mla, store_cla
        
    except IndexError as e:
        print(f'!!!!WARNING get_competition_summary_outputs: Index error - {e}')
        return None
    except KeyError as e:
        print(f'!!!!WARNING get_competition_summary_outputs: Column not found - {e}')
        return None
    except Exception as e:
        print(f'!!!!WARNING get_competition_summary_outputs: Unexpected error - {e}')
        return None

def create_popup_text_html(row):
    """Create HTML for Direct Costs popup with proper NaN handling"""
    # Safely get values with defaults
    storename = row.get('Competitor', 'Unknown Store') if pd.notna(row.get('Competitor')) else 'Unknown Store'
    address = row.get('address', 'Unknown address') if pd.notna(row.get('address')) else 'Unknown address'
    ss_type = row.get('ss_type', 'Unknown ss type') if pd.notna(row.get('ss_type')) else 'Unknown ss type'
    area_type = row.get('area_unit', 'unknown area type') if pd.notna(row.get('area_unit')) else 'unknown area type'
    
    # Format numeric values safely - howeever as we have mixed col values coerce to numeric
    total_area = f"{row.get('store_cla'):,.0f}" if pd.notna(row.get('store_cla')) else 'N/A'
    total_rentable_area = f"{row.get('store_mla'):,.0f}" if pd.notna(row.get('store_mla')) else 'N/A'
    distance_km = f"{row.get('distance_km'):,.2f}" if pd.notna(row.get('distance_km')) else 'N/A'

    # Use triple quotes with f-string for cleaner HTML
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 10px; line-height: {HTML_LINE_HEIGHT}; font-size: {HTML_BODY_FONT_SIZE}px">
        <h4 style="margin-bottom: 10px; font-size: {HTML_H4_FONT_SIZE}px"><strong>{escape(storename)}</strong></h4>
        <p><strong>Address:</strong> {escape(address)}</p>
        <p><strong>Distance:</strong> {distance_km}km</p>
        <p><strong>Storage Type:</strong> {escape(ss_type)}</p>
        <p><strong>Total area:</strong> {escape(total_area)} {escape(area_type)}</p>
        <p><strong>Total rentable area:</strong> {escape(total_rentable_area)} {escape(area_type)}</p>
    </div>
    """
    return html

def render_competition_ss_type_selector():
    """Renders list for the select box for the SS Type in the sidebar
    This ensures that if a competitor with the type is deleted the select box will not raise an error
    """
    gdf_competition = st.session_state.gdf_competition
    
    if gdf_competition is None:
        if 'selected_storage_types' in st.session_state:
            st.session_state['selected_storage_types'] = []
        st.warning("!!!!WARNING render_competition_ss_type_selector gdf_competition is None")
        return []
    
    try:
        unique_storage_types = gdf_competition['ss_type'].unique().tolist()
        
        # Initialize with all selected on first run
        if 'selected_storage_types' not in st.session_state:
            st.session_state['selected_storage_types'] = unique_storage_types
        
        # Get current selected values
        current_selected = st.session_state.get('selected_storage_types', [])
        
        # Validate and clean the selection
        valid_selected_types = [storage_type for storage_type in current_selected 
                               if storage_type in unique_storage_types]
        
        selected_competitors = st.multiselect(
            'Storage Types',
            options=unique_storage_types,
            default=valid_selected_types,
            key='selected_storage_types'
        )
        
        return selected_competitors
        
    except Exception as e:
        st.error(f"Error loading storage types: {str(e)}")
        # Reset selection on error
        if 'selected_storage_types' in st.session_state:
            st.session_state['selected_storage_types'] = []
        return []