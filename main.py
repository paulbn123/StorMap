import streamlit as st
import os
import time

from utils.session_state_utils import initialize_session_state
from controllers.app_controller import StorageAppController
from utils.load_save_data_files_utils import (load_data_files, 
                                              get_savills_score_weightings)

from config.constants import DEBUG_PRINT



def load_css(pathname):
    """
    Load and inject a CSS file into the Streamlit app.
    
    Args:
        file_path (str): Path to the CSS file.
    """
    with open(pathname, "r") as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def main():

    """main function is the function that runs the app
    """

    st.set_page_config(
        layout='wide',
        page_title='Savills Stormap',
        page_icon=':unlock:',
        initial_sidebar_state='expanded'
    )

    load_css("./assets/css/style.css")  # Load CSS first

    # Initialize session state on first run
    if "data" not in st.session_state:
        
        # This is loading the main spatial files - but not the ssdb
        st.session_state.data = load_data_files()

        # This loads the Savills self storage weights 
        st.session_state.savills_score_weightings, st.session_state.weightings_dict = get_savills_score_weightings()
        # Show temporary success message
        msg = st.empty()
        msg.success("Data loaded successfully")
        time.sleep(2)  # show for 2 seconds
        msg.empty()    # remove the message
        
        # check if the ssdb parquet has been loaded - if not show up loader screen 
        if not 'ssdb' in st.session_state.data:
            # If we are not loading the ssdb from local files render uploader window for the parquet file
            if DEBUG_PRINT:
                print('****INFO did not find SSDB from local files rendering ssdb uploader')
        else:
            if DEBUG_PRINT:
                print('****INFO Found SSDB in local files')

    if 'app_data' not in st.session_state:
        # This includes session state data     
        initialize_session_state() 

    app_controller = StorageAppController()
    app_controller.run()


if __name__ == "__main__":
    main()


# "D:\D_documents\LLMs\LLM_Engineering\scripts\llm_venv\Scripts\Activate.ps1"