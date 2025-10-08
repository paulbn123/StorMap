import streamlit as st
import pandas as pd

from utils.load_save_data_files_utils import get_gdf_ssdb_from_df
from config.constants import DEBUG_PRINT

class SSDBUploaderUI:
    def __init__(self):
        self.title = "Please add the SSDB"
        self.allowed_types = ["xlsx", "xls"]

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

        
    def render_uploader(self):
        """Render the file uploader interface"""
        st.title(self.title)
        
        uploaded_file = st.file_uploader(
            "Choose an Excel file", 
            type=self.allowed_types
        )
        
        if uploaded_file is not None:
            self._process_uploaded_file(uploaded_file)
    
    def _process_uploaded_file(self, uploaded_file):
        """Process the uploaded Excel file"""
        try:
            # Read the Excel file into a DataFrame
            df_ssdb = pd.read_excel(uploaded_file)
            
            # Process the DataFrame using your existing function
            gdf_ssdb = get_gdf_ssdb_from_df(df_ssdb)
            if gdf_ssdb is not None:
                st.session_state.data['ssdb'] = gdf_ssdb
                st.session_state.ssdb_uploaded = True
            
                st.success("SSDB file successfully loaded!")
                st.rerun()
            else:
                st.error('Unable to process uploaded file - please try again')
                st.rerun()

        except Exception as e:
            error_msg = f"Error loading SSDB: {str(e)}"
            st.error(error_msg)
            print(f'!!!!WARNING ssdb_uploader was not able to load the ssdb: {str(e)}')
            st.session_state.ssdb_uploaded = False