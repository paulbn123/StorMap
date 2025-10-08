import streamlit as st
import folium
from streamlit_folium import st_folium


from config.constants import DEBUG_PRINT, ISO_TIME_MINS
from utils.clear_current_locations_utils import clear_current_locations_reset_app
from utils.competition_utils import (render_competition_map, 
                                     render_competition_header, 
                                     update_competition_data, 
                                     render_competition_data_header,
                                     render_competition_data_summary,
                                     render_competition_data_summary_with_editor,
                                     render_competition_ss_type_selector)
from utils.session_state_utils import get_validated_gdf_from_app_data
from utils.demo_processing_utils import (return_demo_chloropleth_map)
from utils.demo_data_summary_management_utils import (get_filtered_df_demo_summ, 
                                                      get_column_names_from_df_demo_summ,
                                                      get_data_value_from_df_demo_summ)
from utils.other_utils import add_savills_logo
from utils.asset_score_utils import render_score_table


"""Module renders output when a store has been selected"""


class DisplayUI:

    def __init__(self):
        if DEBUG_PRINT:
            print(f'*****INFO initialising DisplayUI')


    def render_display_sidebar(self):

        with st.sidebar:

            add_savills_logo()
            
            st.markdown('<div style="width: 250px">', unsafe_allow_html=True)
            
            with st.container():
    
                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ################### SELECTED STORE OPTIONS ####################
            ###############################################################

                selected_storenames = st.session_state.app_data['selected_storenames']
                if not len(selected_storenames)>0:
                    st.write('No storenames found - please clear data and select a store')
                
                else:
                    try:
                        default_storename_idx = selected_storenames.index(st.session_state.app_data['selected_storenames'])

                    except(ValueError, TypeError):
                        default_storename_idx = 0

                    st.radio(
                            label='Selected store',
                            options=selected_storenames,
                            key="selected_storename",
                            index=default_storename_idx
                    )  

                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)
                
            ###############################################################
            ################### DRIVE TIME OPTIONS #######################
            ###############################################################

                if "selected_drive_time" not in st.session_state:
                    st.session_state.selected_drive_time = ISO_TIME_MINS[2]

                st.radio(
                    label='Drive Time (mins)',
                    options=ISO_TIME_MINS,
                    key="selected_drive_time",
                )  

            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ####################### SS_Type OPTIONS #######################
            ###############################################################

            render_competition_ss_type_selector()

            # gdf_competition = get_validated_gdf_from_app_data("gdf_competition")
            # if gdf_competition is not None:
            #     unique_storage_types = gdf_competition['SS_Type'].unique().tolist()
                
            #     # Initialize with all selected on first run
            #     if 'selected_storage_types' not in st.session_state.app_data:
            #         st.session_state.app_data['selected_storage_types'] = unique_storage_types
                
            #     selected_competitors = st.multiselect(
            #         'Storage Types',
            #         options=unique_storage_types,
            #         default=st.session_state.app_data['selected_storage_types'],
            #         key='selected_storage_types'
            #     )

            
            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)


            ###############################################################
            ################### DEMO TYPE OPTIONS #########################
            ###############################################################



            # Show the data cols in df_demo_summ which will be the index for gdfs
            _gdf_cols = get_column_names_from_df_demo_summ()

            if _gdf_cols:
                # Initialize session state if not exists
                if 'selected_demo_gdf' not in st.session_state:
                    st.session_state.selected_demo_gdf = _gdf_cols[0]  # Default to first column
                
                # Check if stored value exists in current columns, otherwise revert to first
                if st.session_state.selected_demo_gdf not in _gdf_cols:
                    st.session_state.selected_demo_gdf = _gdf_cols[0]
                
                # Create radio buttons with callback to update session state
                selected_col = st.radio(
                    "Select Demographic Output:",
                    options=_gdf_cols,
                    index=_gdf_cols.index(st.session_state.selected_demo_gdf),
                    key='demo_gdf_radio',
                    on_change=lambda: setattr(st.session_state, 'selected_demo_gdf', st.session_state.demo_gdf_radio)
                )
                
                # Ensure session state is synchronized (in case of external changes)
                st.session_state.selected_demo_gdf = selected_col
                
            else:
                st.warning("No df_demo_summ data columns could be found")
                print('No df_demo_summ data cols could be found')

    
            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)


            # Select demo data to be displayed
            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            ###############################################################
            ##################### DELETE / RESET  #########################
            ###############################################################


            if st.button('Delete all locations', type="primary"):
                    clear_current_locations_reset_app()
                    st.rerun()


    ##################################################
    ###########  COMPETITION TAB    ##################
    ##################################################

    def render_competition_tab(self):
        """Render Title and Map in tab"""
        # Update competition data first
        update_competition_data()
        
        with st.container():
            col_1, col_2 = st.columns([5,2])
            with col_1:
                render_competition_header()
            with col_2:
                app_data = st.session_state.get("app_data", {})
                output_competition = app_data.get("output_competition")
                _output_competition = output_competition.copy()
                _cols_to_drop = ['index_right', 'storename', 'iso_time_mins', 'src_latitude', 'src_longitude', 'popup_text', 'geometry']
                for col in _cols_to_drop:
                    if col in _output_competition.columns:
                        _output_competition.drop(columns=col, inplace=True)
                comp_output_csv = _output_competition.to_csv(index=False, encoding='utf-8-sig')
                _storename = st.session_state.selected_storename
                _iso_time_mins = st.session_state.selected_drive_time
                output_file_name = f'{_storename}_{_iso_time_mins}_competition.csv'
                st.download_button(
                    label="Download competition",
                    data=comp_output_csv,
                    file_name=output_file_name,
                    mime="text/csv",
                    help='Download competition summary for the current iso'
                )
            
            render_competition_map()


    def render_score_tab(self):

        render_score_table()


    def render_demographic_tab(self):
        
        # Capture key values 
        _storename = st.session_state.selected_storename
        _iso_time_mins = st.session_state.selected_drive_time
        _demo_type_selected = st.session_state.demo_gdf_radio
        if DEBUG_PRINT:
            print(f"****INFO {_storename} {_iso_time_mins} {_demo_type_selected}")

        gdf_selected_demo = st.session_state.gdf_demo.get(_demo_type_selected)
        
        if gdf_selected_demo is None:
            print(f'!!!!WARNING render_demographic_tab could not get {_demo_type_selected} from session_state.gdf_demo')
            return
        
        # render header
        header_string = f'{_storename}: {_demo_type_selected} for {_iso_time_mins} min catchment'
        st.write(header_string)

        # Render demo map
        return_demo_chloropleth_map(gdf_name=_demo_type_selected,  
                                    storename=_storename, 
                                    iso_time_mins=_iso_time_mins)




    def render_data_summary_tab(self):

        """Adds in data for the outputs"""
        
        # Competition summary
        # Title + dataframe table 
        render_competition_data_header()
        render_competition_data_summary_with_editor()
        # render_competition_data_summary()

        # Filtered df_demo_summ is shown here
        try:
            storename_list = [st.session_state.selected_storename]
            iso_time_mins_list = [st.session_state.selected_drive_time]
            print(f'storename_list {storename_list} iso_time_mins_list {iso_time_mins_list}')
            df_data_summ_filtered = get_filtered_df_demo_summ(
                                    storename_list=storename_list, 
                                    iso_time_mins_list=iso_time_mins_list
                                )
            if df_data_summ_filtered is not None:
                st.write(f'Summary demographic data for {st.session_state.selected_storename}')
                st.dataframe(df_data_summ_filtered.T, hide_index=False,  height=(35 * len(df_data_summ_filtered.T) + 35)) 
             
        except:
            if DEBUG_PRINT:
                print(f'!!!!WARNING could not get a filtered df_summ for store and isotime')
        
        


