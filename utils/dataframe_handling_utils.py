import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np



"""Module contains util functions for checking dataframe and geodataframe objects"""



def all_required_cols_in_df(df, required_cols):
    """"Checks that the required columns are in df
    Returns bool and prints missing cols outputs"""

    if required_cols == None:
        return False
    
    missing_cols = []
    for col in required_cols:
        if col not in df.columns:
            missing_cols.append(col)
    
    if missing_cols:
        print(f'!!!!WARNING check_required_cols_in_df found missing colulms: {missing_cols}')
        return False
    
    return True
    

