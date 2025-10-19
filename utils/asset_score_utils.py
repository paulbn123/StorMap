import streamlit as st

import pandas as pd
import numpy as np

from managers.session_state_manager import SessionStateManager

from utils.demo_data_summary_management_utils import get_data_value_from_df_demo_summ
from utils.competition_utils import summarise_competition, get_output_competition
from utils.other_utils import validate_storename_and_iso_time_mins_in_df

from config.constants import DEBUG_PRINT



"""This module covers the creation of the SSST output table on the ssst tab
Reads in data summary and applies weights
"""

SCORE_ROUNDING_MULTIPLE = 0.25

def get_score_from_value(df, value):
    """This requires that the bounds are in ascending order
    This is part of the load process """

    _required_cols = ['Lower Bound', 'Upper Bound', 'Score']
    _missing_cols = []
    for col in _required_cols:
        if col not in df.columns:
            _missing_cols.append(col)
    if _missing_cols:
        print(f'!!!!WARNING get_score_from_value df passed with missing cols {_missing_cols}')
        return None
    if value < df['Lower Bound'].min():
        print(f"WARNING: Value {value} below minimum bound, using lowest score")
        return df['Score'].iloc[0]
    elif value > df['Upper Bound'].max():
        print(f"WARNING: Value {value} above maximum bound, using highest score")
        return df['Score'].iloc[-1]
    
    mask = (df['Lower Bound'] <= value) & (df['Upper Bound'] >= value)
    return df[mask]['Score'].iloc[0]



def render_score_table():

    # to get the scoring create a data frame with the score and weighted values
    # the order is determined by df_weightings 

    print(f'*****************************')
    print(f'**Processing Savills Score***')
    print(f'****************************')


    try: 
       
        _iso_time_mins = st.session_state.get("selected_drive_time")
        _storename = st.session_state.get("selected_storename")
        selected_storage_types = st.session_state.get("selected_storage_types")

        # Validation checks
        if not _iso_time_mins:
            return st.error("Please select a drive time")
        if not _storename:
            return st.error("Please select a store name")
        if not selected_storage_types:
            return st.error("Please select at least one storage type")

        print(f'storename: {_storename } iso_time_mins: {_iso_time_mins}')

    except:
        print(f'!!!!!WARNING render_score_table could not get storename or iso_time ')


    _score_weightings = st.session_state.get("savills_score_weightings") 
    if _score_weightings is None:
        print(f'!!!!WARNING render_score_table could not get savills_score_weightings from session_state')
        return
    
    output_factor_name = []
    internal_factor_name = []
    raw_value = []
    weight = []
    score_unweighted = []
    score_weighted = []


    for idx, row in _score_weightings.iterrows():
       
        # only process if this is a demand factor - supply handled later
        if row.Supply_Demand == 'Supply':
            continue

        print(f'\tProcessing: {row.Display_Name}')
        print(f'\tInternal name: {row.Internal_Name}')
        print(f'\tWeight: {row.Weight}')

        
        _internal_name = row.Internal_Name
        _weight = row.Weight
        
        weightings_dict = st.session_state.get('weightings_dict')
        if weightings_dict is None:
            print(f'!!!!WARNING could not get weightings_dict')
            continue
        else:
            # only append values if we have managed to get data in
            _df_scoring = weightings_dict.get(_internal_name)
            if _df_scoring is not None:
                _raw_value = get_data_value_from_df_demo_summ(storename=_storename,
                                                              iso_time_mins=_iso_time_mins,
                                                              data_col_name= _internal_name)
                if _raw_value is None:
                    print(f'!!!!WARNING render_score_table could not get a value for {_internal_name}')
                try:
                    _unweighted_score = get_score_from_value(_df_scoring, _raw_value)
                    print(f'****INFO _unweighted_score: {_unweighted_score}')
                except:
                    print(f'!!!!WARNING could not get _unweighted_score')
                    continue
                
                raw_value.append(_raw_value)
                score_unweighted.append(_unweighted_score)
                output_factor_name.append(row.Display_Name)
                internal_factor_name.append(_internal_name)
                _display_weight = round(_weight * 100,2)
                weight.append(f'{_display_weight}%')
                _weighted_score = round((_weight * _unweighted_score) / SCORE_ROUNDING_MULTIPLE,0) * SCORE_ROUNDING_MULTIPLE
                score_weighted.append(_weighted_score) 

    # now need to add the two supply side factors
    _total_popn_in_iso =  get_data_value_from_df_demo_summ(storename=_storename, 
                                     iso_time_mins=_iso_time_mins, 
                                     data_col_name='Total_Popn')
    print(f'****INFO render_score_table total_popn: {_total_popn_in_iso} ')
    
    _gdf_competition = get_output_competition(drive_time=_iso_time_mins,
                                            storename=_storename,
                                            selected_storage_types=selected_storage_types)
    if _gdf_competition is not None:
        print(f'****INFO render_score_table _gdf_competition {_gdf_competition.columns}')
        _competition_summary = summarise_competition(_gdf_competition)

        print(f"****INFO _competition_summary")
        print(f"{_competition_summary}")
        
        # Check dataframe is not None - as this is the error value from _competiton summary
        if _competition_summary is None:
            print("!!!!WARNING No competition data available")
            total_cla = 0
            total_stores = 0
            stores_per_person = None
            cla_per_person = None
        else:
            # Use .iloc[0] for first row regardless of index
            total_cla = _competition_summary.iloc[0]['store_cla']
            total_stores = _competition_summary.iloc[0]['competition_count']
            
            ##############################
            ## STORES PER PERSON
            ##############################
            # Check for division by zero - stores per person
            if total_stores > 0 and _total_popn_in_iso > 0:
                
                stores_per_person = round(_total_popn_in_iso / total_stores,0)

                weight_values = _score_weightings.loc[_score_weightings['Internal_Name'] == 'People_per_store', 'Weight'].values
                if len(weight_values) > 0:
                    _weight = weight_values[0]
                    raw_value.append(stores_per_person)
                    output_factor_name.append('People per store')
                    internal_factor_name.append('People_per_store')
                    _df_scoring = weightings_dict.get('People_per_store')
                    _unweighted_score = get_score_from_value(_df_scoring, stores_per_person)
                    score_unweighted.append(_unweighted_score)
                    print(f'****INFO _unweighted_score: {_unweighted_score}')
                    _display_weight = round(_weight * 100,2)
                    weight.append(f'{_display_weight}%')
                    _weighted_score = round((_weight * _unweighted_score) / SCORE_ROUNDING_MULTIPLE,0) * SCORE_ROUNDING_MULTIPLE
                    score_weighted.append(_weighted_score) 
                else:
                    print(f"!!!!WARNING: No weight found for People_per_store")

            else:
                stores_per_person = None
                print("!!!!Warning: No stores to calculate stores per person ratio")
            
            ##############################
            #### CLA Per person
            #############################

            # Check for division by zero - CLA per person
            if pd.notna(_total_popn_in_iso) and _total_popn_in_iso > 0:

                cla_per_person = round(total_cla / _total_popn_in_iso,2)

                weight_values = _score_weightings.loc[_score_weightings['Internal_Name'] == 'CLA_per_person', 'Weight'].values
                if len(weight_values) > 0:
                    _weight = weight_values[0]
                    raw_value.append(cla_per_person)
                    output_factor_name.append('CLA per person')
                    internal_factor_name.append('CLA_per_person')
                    _df_scoring = weightings_dict.get('CLA_per_person')
                    _unweighted_score = get_score_from_value(_df_scoring, cla_per_person)
                    score_unweighted.append(_unweighted_score)
                    print(f'****INFO _unweighted_score: {_unweighted_score}')
                    _display_weight = round(_weight * 100,2)
                    weight.append(f'{_display_weight}%')
                    _weighted_score = round((_weight * _unweighted_score) / SCORE_ROUNDING_MULTIPLE,0) * SCORE_ROUNDING_MULTIPLE
                    score_weighted.append(_weighted_score) 
                else:
                    print(f"!!!!WARNING: No weight found for CLA_per_person")
            else:
                cla_per_person = None
                print("!!!!Warning: Invalid population to calculate CLA per person")

    print(f'*****INFO checking length of outputs lists for _output_df')
    _output_lists = [output_factor_name, raw_value, score_unweighted, weight, score_weighted]
    for _output_list in _output_lists:
        print(f'\t{len(_output_list)}')

    _output_df = pd.DataFrame({
        'Factor':output_factor_name,
        'Factor Value': raw_value,
        'Score (unweighted)': score_unweighted,
        'Weight': weight,
        'Weighted Score': score_weighted,
    })

    _overall_score = _output_df['Weighted Score'].sum()
    _overall_score_rounded = round(_overall_score / SCORE_ROUNDING_MULTIPLE,0) * SCORE_ROUNDING_MULTIPLE

    # Streamlit will render these at this point
    _rendered_df = st.dataframe(_output_df, 
                                hide_index= True, 
                                #height=600
                                )

    _output_text = st.write(f'Savills Self Storage Score: {_overall_score_rounded} / 10')




