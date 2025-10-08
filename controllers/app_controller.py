import streamlit as st


from config.constants import (DEBUG_PRINT, 
                              DISPLAY_TAB_NAMES)
from ui.display_ui import DisplayUI
from ui.search_ui import SearchUI
from ui.ssdb_uploader_ui import SSDBUploaderUI

"""This module is the main controller handling initial loading of data 
and setting up of session states
it also handles the instantiation and rendering of the uis for data display
"""


class StorageAppController():
    """Main application controller"""

    def __init__(self):
        # on init capture the application data from the session state
        self.app_data = st.session_state.app_data
        

    def run(self):
        # ensure that the ssdb has been uploaded
        if not self._ssdb_uploaded():
            self._render_SSDB_uploader_view()

        else:
            # Function that runs the StorageAppController
            if self._src_locations_selected():
                if DEBUG_PRINT:
                    print(f'****INFO StorageAppController: _src_location_selected has been found')

                self._render_outputs_view()

            else:
                if DEBUG_PRINT:
                    print(f'****INFO StorageAppController: No  _src_locations_selected have been found')

                self._render_search_view()

    def _src_locations_selected(self):
                
        # Ensure the key exists with a default value
        if 'src_locations_selected' not in st.session_state:
            st.session_state.src_locations_selected = False
        
        return st.session_state.src_locations_selected

    def _ssdb_uploaded(self):
        if 'ssdb_uploaded' not in st.session_state:
            st.session_state.ssdb_uploaded = False 
        
        return st.session_state.ssdb_uploaded


    def _render_outputs_view(self):

        self.display_ui = DisplayUI()

        self.display_ui.render_display_sidebar()

        tab_comp, tab_Score, tab_demo, tab_data = st.tabs(DISPLAY_TAB_NAMES)

        with tab_comp:
            self.display_ui.render_competition_tab()

        with tab_Score:
            self.display_ui.render_score_tab()

        with tab_demo:
            self.display_ui.render_demographic_tab()
        
        with tab_data:
            self.display_ui.render_data_summary_tab()


    def _render_search_view(self):

        self.search_ui = SearchUI()

        self.search_ui.render_search_map()
    
    def _render_SSDB_uploader_view(self):

        self.ssdb_uploader_ui = SSDBUploaderUI()

        self.ssdb_uploader_ui.render_uploader()
