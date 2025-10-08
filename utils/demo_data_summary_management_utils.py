import streamlit as st
import pandas as pd
import numpy as np
import itertools

from config.constants import ISO_TIME_MINS, DEBUG_PRINT

""""This module deals with all the code to manage the data frame that summarises the demo outputs
All of the outputs for each storename and each iso_time_mins will be in a dataframe df_demo_summ
This will by managed in a session state st.session_state.df_demo_summ
"""

def initialize_df_demo_summ():
    st.session_state.setdefault('df_demo_summ', pd.DataFrame())

def reset_df_demo_summ():
    st.session_state.setdefault('df_demo_summ', pd.DataFrame())

def create_base_df_demo_summ(storenames_list, iso_time_mins_list=ISO_TIME_MINS):

    """"This funciton creates the base df for which we will store summary data for the store in 
    Keeps all the different demographic processing in a single location
    """
    # Cartesian product
    pairs = list(itertools.product(storenames_list, iso_time_mins_list))

    # Create DataFrame
    df = pd.DataFrame(pairs, columns=["storename", "iso_time_mins"])
    st.session_state.df_demo_summ = df
    print(df)


def add_data_to_df_demo_summ(df_update):

    """"Adds data to the df_demo_summ
    param df_update - df_update which requires columns 'storename' 'iso_time_mins' + [data_cols]"""

    df_demo_summ = st.session_state.df_demo_summ
    
    _required_cols = ['storename', 'iso_time_mins']
    missing_cols = []
    for col in _required_cols:
        if col not in df_update.columns:
            missing_cols.append(col)
    if missing_cols:
        print(f'!!!!WARNING tried to update df_demo_summ but missing these columns: {missing_cols}')
        return
    # Check if we are duplicating any columns in df_demo_summ 
    _update_data_cols = [col for col in df_update.columns if col not in _required_cols]
    _duplicated_cols = []
    if _update_data_cols:
        for col in _update_data_cols:
            if col in df_demo_summ:
                _duplicated_cols.append(col)
    if _duplicated_cols:
        print(f'!!!!!WARNING trying to add these columns to df_summ that already exist: {_duplicated_cols} - dropping them')
        clean_cols = [col for col in df_update.columns if col not in _duplicated_cols]
        df_update = df_update[clean_cols]
        if len(df_update.columns) == len(_required_cols):
            print(f'!!!!!WARNING no cols to update after cleaning')
            return 
    
    df_joined = df_demo_summ.merge(df_update, how='left', on=_required_cols)
    # Then update the session_state with the additional data
    st.session_state.df_demo_summ = df_joined

    # Save file so it can  be examined
    if DEBUG_PRINT:
        try:
            fpath_df_summ = r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_df_demo_summ.csv"
            df_joined.to_csv(fpath_df_summ, index=False)
            print(f'****INFO save df_demo_summ to {fpath_df_summ}')
        except:
            print(f'****INFO save df_demo_summ to {fpath_df_summ}')



def get_column_names_from_df_demo_summ():

    """function returns the columns names from df_demosumm excluding the two idx cols"""
    df_demo_summ = st.session_state.df_demo_summ
    _idx_cols = ['storename', 'iso_time_mins']
    data_cols = [col for col in df_demo_summ.columns if col not in _idx_cols]

    return data_cols


def get_filtered_df_demo_summ(storename_list, iso_time_mins_list):
    """Function returns filtered version of df_demo_summ"""

    print(f'**************************************')
    print(f'******** DEBUG get_filtered_df_demo_summ ***************')
    print(f'**************************************')
    df_demo_summ = st.session_state.df_demo_summ
    if DEBUG_PRINT:
        print(df_demo_summ)
        print(f'*************************************')
        print(f'************* DEBUG get_filtered_df_demo_summ *****')
        print(f'*************************************')
        print(f'****INFO df_demo_summ {df_demo_summ.shape}')
        print(f'****INFO df_demo_summ {df_demo_summ.columns}')
        print(f'****INFO storename_list {storename_list}')
        print(f'****INFO iso_time_mins_list {iso_time_mins_list}')


    df_filtered_demo_summ = df_demo_summ[(df_demo_summ.storename.isin(storename_list)) & (df_demo_summ.iso_time_mins.isin(iso_time_mins_list))]
    # By settingthe index to the storename - this effectively becomes the header on the transposed df
    df_filtered_demo_summ.set_index('storename' , inplace=True)
    
    return df_filtered_demo_summ

def get_data_value_from_df_demo_summ(storename, iso_time_mins, data_col_name):
    """Returns a value from df_demo_summ based on storename, time, and column name"""
    df = st.session_state.df_demo_summ
    
    # Validate inputs exist in DataFrame
    if not ((df['storename'] == storename) & (df['iso_time_mins'] == iso_time_mins)).any():
        print(f'!!!!WARNING: Combination ({storename}, {iso_time_mins}) not found in df_demo_summ')
        return None
    
    # and data_colName in col
    _idx_cols = ['storename', 'iso_time_mins']
    _data_cols = [col for col in df.columns if col not in _idx_cols]

    if data_col_name not in _data_cols:
        print(f'!!!!WARNING: Column {data_col_name} not found in df_demo_summ')
        return None
    
    # Extract the value efficiently
    try:
        return df.loc[(df['storename'] == storename) & 
                     (df['iso_time_mins'] == iso_time_mins), data_col_name].values[0]
    except IndexError:
        return None