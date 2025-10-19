import streamlit as st
import folium
from streamlit_folium import st_folium

from config.constants import DEBUG_PRINT, ISO_TIME_MINS
from managers.session_state_manager import SessionStateManager, clear_current_locations_reset_app
from utils.competition_utils import (render_competition_map, 
                                     render_competition_header, 
                                     update_competition_data, 
                                     render_competition_data_header,
                                     render_competition_data_summary_with_editor
                                     )
from utils.demo_processing_utils import (return_demo_chloropleth_map)
from utils.demo_data_summary_management_utils import (get_filtered_df_demo_summ, 
                                                      get_column_names_from_df_demo_summ,
                                                      get_data_value_from_df_demo_summ)
from utils.other_utils import add_savills_logo
from utils.asset_score_utils import render_score_table


"""Module renders output when the SSDB has been loaded and store(s) have been selected and """


class DisplayUI:

    def __init__(self):
        if DEBUG_PRINT:
            print(f'****INFO initialising DisplayUI')
        
        # Initialize session state on first load
        SessionStateManager.initialize(iso_time_mins=ISO_TIME_MINS)

    def update_competition_on_change():
        "Update competition when changed"
        update_competition_data()

    def render_display_sidebar(self):

        with st.sidebar:

            add_savills_logo()
            
            st.markdown('<div style="width: 250px">', unsafe_allow_html=True)
            
            with st.container():
    
                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ################### SELECTED STORE OPTIONS ####################
            ###############################################################

                selected_storenames = st.session_state.get('selected_storenames')
                print(f'****INFO display_ui selected_storenames {selected_storenames}')
                if selected_storenames is None:
                    st.write('No storenames found - please clear data and select a store')
                
                else:
                    current_selection = st.session_state.get("selected_storename")
                    try:
                        default_storename_idx = selected_storenames.index(current_selection) if current_selection else 0
                    except (ValueError, TypeError):
                        default_storename_idx = 0

                    selected_storename = st.radio(
                        label='Selected store',
                        options=selected_storenames,
                        index=default_storename_idx,
                        key="selected_storename_radio",
                        on_change=update_competition_data
                    )
                    
                    # Update session state if changed
                    if selected_storename != st.session_state.get("selected_storename"):
                        st.session_state.selected_storename = selected_storename

                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)
                
            ###############################################################
            ################### DRIVE TIME OPTIONS #######################
            ###############################################################

                current_drive_time = st.session_state.get("selected_drive_time")
                
                selected_drive_time = st.radio(
                    label='Drive Time (mins)',
                    options=ISO_TIME_MINS,
                    index=ISO_TIME_MINS.index(current_drive_time) if current_drive_time in ISO_TIME_MINS else 2,
                    key="selected_drive_time_radio",
                    on_change=update_competition_data
                )
                
                # Update session state if changed
                if selected_drive_time != current_drive_time:
                    st.session_state.selected_drive_time=  selected_drive_time

            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ####################### SS_Type OPTIONS #######################
            ###############################################################

            self._render_storage_type_selector()
            
            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ################### DEMO TYPE OPTIONS #########################
            ###############################################################

            self._render_demo_type_selector()
    
            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ##################### DELETE / RESET  #########################
            ###############################################################

            if st.button('Delete all locations', type="primary"):
                clear_current_locations_reset_app()
                st.rerun()

    def _render_storage_type_selector(self):
        """Render storage type selector with checkboxes"""
        gdf_competition = st.session_state.get('gdf_competition')
        
        print(f'****INFO - rendering checkbox multiselect')

        if gdf_competition is not None:
            unique_storage_types = gdf_competition['ss_type'].unique().tolist()
            
            # Initialize session state if not exists
            if 'selected_storage_types' not in st.session_state:
                st.session_state.selected_storage_types = unique_storage_types.copy()
            
            st.write("Storage Types")
            
            # Create checkboxes for each storage type
            for storage_type in unique_storage_types:
                is_checked = st.checkbox(
                    storage_type, 
                    value=storage_type in st.session_state.selected_storage_types,
                    key=f"checkbox_{storage_type}"
                )
                
                # Update the session state list
                if is_checked and storage_type not in st.session_state.selected_storage_types:
                    st.session_state.selected_storage_types.append(storage_type)
                elif not is_checked and storage_type in st.session_state.selected_storage_types:
                    st.session_state.selected_storage_types.remove(storage_type)

    def _render_demo_type_selector(self):
        """Render demographic type selector with proper state management"""
        # Show the data cols in df_demo_summ which will be the index for gdfs
        _gdf_cols = get_column_names_from_df_demo_summ()

        if _gdf_cols:
            current_selection = SessionStateManager.get_selected_demo_gdf()
            
            # Initialize with first column if no current selection or invalid selection
            if not current_selection or current_selection not in _gdf_cols:
                current_selection = _gdf_cols[0]
                SessionStateManager.set_selected_demo_gdf(current_selection)
            
            # Create radio buttons
            selected_demo_gdf = st.radio(
                "Select Demographic Output:",
                options=_gdf_cols,
                index=_gdf_cols.index(current_selection),
                key='demo_gdf_radio'
            )
            
            # Update session state if changed
            if selected_demo_gdf != current_selection:
                SessionStateManager.set_selected_demo_gdf(selected_demo_gdf)
                
        else:
            st.warning("No df_demo_summ data columns could be found")
            if DEBUG_PRINT:
                print('No df_demo_summ data cols could be found')


    ##################################################
    ###########  COMPETITION TAB    ##################
    ##################################################

    def render_competition_tab(self):
        """Render Title and Map in tab"""
        # Update competition data first
        update_competition_data()
        
        with st.container():
            col_1, col_2 = st.columns([5, 2])
            with col_1:
                render_competition_header()
            with col_2:
                self._render_competition_download_button()
            
            render_competition_map()

    def _render_competition_download_button(self):
        """Render competition data download button"""
        output_competition = st.session_state.get('output_competition')
        
        if output_competition is not None:
            _output_competition = output_competition.copy()
            if 'geometry' in _output_competition.columns:
                _output_competition.drop(columns='geometry', inplace=True)
            
            comp_output_csv = _output_competition.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="Download competition",
                data=comp_output_csv,
                file_name="output_competition.csv",
                mime="text/csv",
                help='Download competition summary for the current iso'
            )

    def render_score_tab(self):
        """Render the score analysis tab"""
        render_score_table()

    def render_demographic_tab(self):
        """Render the demographic analysis tab"""
        # Get current state values
        storename = st.session_state.get("selected_storename")
        iso_time_mins = st.session_state.get("selected_drive_time")
        demo_type_selected = SessionStateManager.get_selected_demo_gdf()
        
        if DEBUG_PRINT:
            print(f"****INFO {storename} {iso_time_mins} {demo_type_selected}")

        if not storename or not demo_type_selected:
            st.warning("Please ensure a store and demographic type are selected")
            return

        gdf_demo = SessionStateManager.get_gdf_demo()
        gdf_selected_demo = gdf_demo.get(demo_type_selected)
        
        if gdf_selected_demo is None:
            st.error(f'Could not get {demo_type_selected} from demographic data')
            if DEBUG_PRINT:
                print(f'!!!!WARNING render_demographic_tab could not get {demo_type_selected} from gdf_demo')
            return
        
        # Render header
        header_string = f'Subject Store: {demo_type_selected} for {iso_time_mins} min catchment'
        st.write(header_string)

        # Render demo map
        return_demo_chloropleth_map(
            gdf_name=demo_type_selected,  
            storename=storename, 
            iso_time_mins=iso_time_mins
        )

    def render_data_summary_tab(self):
        """Render the data summary tab with competition and demographic data"""
        
        # Competition summary
        render_competition_data_header()
        render_competition_data_summary_with_editor()

        # Demographic summary
        self._render_demographic_summary()

    def _render_demographic_summary(self):
        """Render filtered demographic summary data"""
        storename = st.session_state.get("selected_storename")
        drive_time = st.session_state.get("selected_drive_time")
        
        if not storename:
            st.warning("Please select a store to view demographic summary")
            return
        
        try:
            storename_list = [storename]
            iso_time_mins_list = [drive_time]
            
            if DEBUG_PRINT:
                print(f'storename_list {storename_list} iso_time_mins_list {iso_time_mins_list}')
            
            df_data_summ_filtered = get_filtered_df_demo_summ(
                storename_list=storename_list, 
                iso_time_mins_list=iso_time_mins_list
            )
            
            if df_data_summ_filtered is not None:
                st.write(f'Summary demographic data for {storename}')
                st.dataframe(
                    df_data_summ_filtered.T, 
                    hide_index=False,  
                    height=(35 * len(df_data_summ_filtered.T) + 35)
                ) 
            else:
                st.info("No demographic summary data available for the selected criteria")
             
        except Exception as e:
            if DEBUG_PRINT:
                print(f'!!!!WARNING could not get a filtered df_summ for store and isotime: {e}')
            st.error("Error loading demographic summary data")


