import streamlit as st
import os
from PIL import Image

LOGO_PATH = os.path.join('assets', 'images', 'savills_logo.jpg')

IMG_WIDTH_PX = 200


def add_savills_logo():
    """Safe logo loading with error handling and fallback"""
    try:
        if not os.path.exists(LOGO_PATH):
            # If no logo found, show text fallback
            st.sidebar.markdown("**SAVILLS**")
            return
            
        # Load and display image
        with Image.open(LOGO_PATH) as img:
            st.sidebar.image(
                img, 
                width=IMG_WIDTH_PX,
                # use_container_width=True
            )
            
    except (FileNotFoundError, OSError) as e:
        # Handle file-related errors specifically
        st.sidebar.warning(f"Logo file error: {str(e)}")
        st.sidebar.markdown("**SAVILLS**")
        
    except Exception as e:
        # Handle any other unexpected errors
        st.sidebar.error(f"Unexpected error loading logo: {str(e)}")
        st.sidebar.markdown("**SAVILLS**")


