import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium


from utils.spatial_processing_utils import check_crs_match
from utils.demo_data_summary_management_utils import add_data_to_df_demo_summ
from utils.spatial_processing_utils import get_bounds_from_gdf
from utils.competition_utils import get_output_iso

from config.constants import (DEBUG_PRINT, 
                              CRS, 
                              SQM_IN_SQKM,
                              DEFAULT_TILE_LAYER,
                              DEMO_MAP_DISPLAY_HEIGHT_PX,
                              DEFAULT_MAP_CENTER_LATLON, 
                              DEFAULT_MAP_ZOOM_START)

def process_LA_rents():

    """Function overlay isoschrones with LA rents
    Creates gdf of polygons showing average rent per overlaid area
    PLus df of weighted rent per iso area / per store"""

    gdf_isos = st.session_state.gdf_isos.copy()
    _iso_cols_to_keep = ['storename','iso_time_mins', 'geometry']
    missing_cols = []
    for col in _iso_cols_to_keep:
        if col not in gdf_isos.columns:
            missing_cols.append(col)
    if len(missing_cols) > 0:
        raise KeyError(f'!!!!WARNING missing columns from gdf_isos in process_LA_rents: {missing_cols}')
    

    gdf_la_rents = st.session_state.data['la_rents'].copy()
    _la_rents_cols_to_keep = ['Area name', 'Rents_Oct_2024', 'geometry']
    missing_cols = []
    for col in _la_rents_cols_to_keep:
        if col not in gdf_la_rents.columns:
            missing_cols.append(col)
    if len(missing_cols) > 0:
        raise KeyError(f'!!!!WARNING missing columns from gdf_la_rents in process_LA_rents: {missing_cols}')


    check_crs_match(gdf_isos, gdf_la_rents, raise_error=True)

    gdf_overlaid_rents = gpd.overlay(gdf_isos[_iso_cols_to_keep], 
                                        gdf_la_rents[_la_rents_cols_to_keep], 
                                        how='intersection',
                                        keep_geom_type=False,
                                        make_valid=True
                                    )
    if not gdf_overlaid_rents.empty:
        st.session_state.app_data['gdf_rents'] = gdf_overlaid_rents

    # Now add areas and weight outputs
    gdf_overlaid_rents_3035 = gdf_overlaid_rents.to_crs(CRS.EUROPEAN_PLANAR).copy()
    gdf_overlaid_rents_3035['area_sqkm'] = gdf_overlaid_rents_3035.geometry.area / SQM_IN_SQKM
    gdf_overlaid_rents_3035['weighted_rent'] = gdf_overlaid_rents_3035['area_sqkm'].mul(gdf_overlaid_rents_3035['Rents_Oct_2024'])
    _groupby_cols = ['storename', 'iso_time_mins' ]
    _sum_cols = ['area_sqkm', 'weighted_rent']
    gdf_overlaid_rents_groupby = gdf_overlaid_rents_3035.groupby(_groupby_cols)[_sum_cols].sum()
    gdf_overlaid_rents_groupby = gdf_overlaid_rents_groupby.reset_index()
    gdf_overlaid_rents_groupby['Rents_Oct_2024'] = (gdf_overlaid_rents_groupby['weighted_rent']
                                                    .div(gdf_overlaid_rents_groupby['area_sqkm'])
                                                    .fillna(0)
                                                    .round(0).
                                                    astype(int))
    gdf_overlaid_rents_groupby.drop(columns=['weighted_rent', 'area_sqkm'], inplace=True)
    
    # The grouped data can now be added to df_demo_summ and save a version to session_state 
    add_data_to_df_demo_summ(gdf_overlaid_rents_groupby)
    
    # if DEBUG_PRINT:
    #     print(f'gdf_overlaid_rents_3035: {gdf_overlaid_rents_3035.columns}')

    _gdf_rent_cols = ['storename', 'iso_time_mins',  'Rents_Oct_2024', 'geometry'  ] 
    add_demo_gdf_to_session_state(gdf_overlaid_rents_3035[_gdf_rent_cols].to_crs(4326)) 

    if DEBUG_PRINT:
        try:    
            gdf_overlaid_rents_3035[_gdf_rent_cols].to_file(r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_la_overlay.gpkg", driver='GPKG')
            gdf_overlaid_rents_groupby.to_csv(r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_df_rent.csv", index=False)
            print(f'****INFO save test version of gdf_rents and df_rents')

        except:
            print(f'!!!!WARNING was not able to save test version of gdf_overlaid_rents')
    

def process_household_inc():
    """Function overlay isoschrones with Household income data 
    this is not part of the other msoa data set as it is based on 2011 msoa codes
    Creates gdf of polygons showing hh ince per overlaid area
    PLus df of weighted hh inc per iso area / per store"""

    gdf_isos = st.session_state.gdf_isos.copy()
    _iso_cols_to_keep = ['storename','iso_time_mins', 'geometry']
    missing_cols = []
    for col in _iso_cols_to_keep:
        if col not in gdf_isos.columns:
            missing_cols.append(col)
    if len(missing_cols) > 0:
        raise KeyError(f'!!!!WARNING missing columns from gdf_isos in process_LA_rents: {missing_cols}')
    

    gdf_hh_inc = st.session_state.data['msoa_20'].copy()
    _hh_inc_cols_to_keep = ['MSOA11NM', 'HouseholdIncMar2020', 'geometry']
    missing_cols = []
    for col in _hh_inc_cols_to_keep:
        if col not in gdf_hh_inc.columns:
            missing_cols.append(col)
    if len(missing_cols) > 0:
        raise KeyError(f'!!!!WARNING missing columns from gdf_hh_inc in process_household_inc: {missing_cols}')


    check_crs_match(gdf_isos, gdf_hh_inc, raise_error=True)

    gdf_overlaid_inc = gpd.overlay(gdf_isos[_iso_cols_to_keep], 
                                        gdf_hh_inc[_hh_inc_cols_to_keep], 
                                        how='intersection',
                                        keep_geom_type=False,
                                        make_valid=True
                                    )
    if not gdf_overlaid_inc.empty:
        st.session_state.app_data['gdf_inc'] = gdf_overlaid_inc

    # Now add areas and weight outputs
    gdf_overlaid_inc_3035 = gdf_overlaid_inc.to_crs(CRS.EUROPEAN_PLANAR).copy()
    gdf_overlaid_inc_3035['area_sqkm'] = gdf_overlaid_inc_3035.geometry.area / SQM_IN_SQKM
    gdf_overlaid_inc_3035['weighted_inc'] = gdf_overlaid_inc_3035['area_sqkm'].mul(gdf_overlaid_inc_3035['HouseholdIncMar2020'])
    _groupby_cols = ['storename', 'iso_time_mins' ]
    _sum_cols = ['area_sqkm', 'weighted_inc']
    gdf_overlaid_inc_groupby = gdf_overlaid_inc_3035.groupby(_groupby_cols)[_sum_cols].sum()
    gdf_overlaid_inc_groupby = gdf_overlaid_inc_groupby.reset_index()
    gdf_overlaid_inc_groupby['HouseholdIncMar2020'] = (gdf_overlaid_inc_groupby['weighted_inc']
                                                    .div(gdf_overlaid_inc_groupby['area_sqkm'])
                                                    .fillna(0)
                                                    .round(0).
                                                    astype(int))
    gdf_overlaid_inc_groupby.drop(columns=['weighted_inc', 'area_sqkm'], inplace=True)

    # Add the grouped data to df_demo_summ
    add_data_to_df_demo_summ(gdf_overlaid_inc_groupby)

    # if DEBUG_PRINT:
    #     print(f'****INFO gdf_overlaid_inc_3035 {gdf_overlaid_inc_3035.columns}')

    _gdf_inc_cols = ['storename', 'iso_time_mins', 'HouseholdIncMar2020', 'geometry']
    add_demo_gdf_to_session_state(gdf_overlaid_inc_3035[_gdf_inc_cols].to_crs(4326))
    

    if DEBUG_PRINT:
        try:    
            gdf_overlaid_inc_3035[_gdf_inc_cols].to_file(r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_inc_overlay.gpkg", driver='GPKG')
            gdf_overlaid_inc_groupby.to_csv(r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_df_inc.csv", index=False)
            # print(f'****INFO save test version of gdf_inc and df_inc')

        except:
            print(f'!!!!WARNING was not able to save test version of gdf_overlaid_inc')


def process_popn_data():
    """Function overlay isoschrones with LA rents
    Creates gdf of polygons showing average rent per overlaid area
    PLus df of weighted rent per iso area / per store"""

    # Load and process isos from selected stores
    gdf_isos = st.session_state.gdf_isos
    _iso_cols_to_keep = ['storename','iso_time_mins', 'geometry']
    missing_cols = []
    for col in _iso_cols_to_keep:
        if col not in gdf_isos.columns:
            missing_cols.append(col)
    if len(missing_cols) > 0:
        raise KeyError(f'!!!!WARNING missing columns from gdf_isos in process_LA_rents: {missing_cols}')
    
    # load and process the popn data from msoa_22
    gdf_popn = st.session_state.data['msoa_22'].copy()
    _popn_cols_to_keep = ['MSOA21NM', 'total_owners', 'total_renters',  '1 person in household',
                        'Total Households', 'Total_Popn', 'Med_House_Price_YE_Mar2024',
                        'Resi_Sales_YE_Mar2024', 'area_sqkm_orig', 'geometry',
                        'Single_Person_HH_Perc', 'Popn_Density', 'Owner_Occ_Perc',
                        'Avg_HH_Size','LTE_3rooms',	'LTE_3Rooms_perc']
    missing_cols = []
    for col in _popn_cols_to_keep:
        if col not in gdf_popn.columns:
            missing_cols.append(col)
    if len(missing_cols) > 0:
        raise KeyError(f'!!!!WARNING missing columns from gdf_popn in process_household_inc: {missing_cols}')

    # Just check check that each crs matchs 
    check_crs_match(gdf_isos, gdf_popn, raise_error=True)

    # add in transactions per household (perc figure) as this is a relative measure so does not need to be weighted for area
    gdf_popn['trans_per_hh_perc'] = gdf_popn['Resi_Sales_YE_Mar2024'].div(gdf_popn['Total Households']).fillna(0).mul(100).round(2)
    # Then add this back to the popn list to keep
    _popn_cols_to_keep.append('trans_per_hh_perc')

    gdf_overlaid_popn = gpd.overlay(gdf_isos[_iso_cols_to_keep], 
                                        gdf_popn[_popn_cols_to_keep], 
                                        how='intersection', 
                                        keep_geom_type=False,
                                        make_valid=True
                                    )
    if not gdf_overlaid_popn.empty:
        st.session_state.app_data['gdf_inc'] = gdf_overlaid_popn

    # Now add areas and weight outputs and adjustments where not whole area captured
    gdf_overlaid_popn_3035 = gdf_overlaid_popn.to_crs(CRS.EUROPEAN_PLANAR).copy()
    gdf_overlaid_popn_3035['area_sqkm'] = gdf_overlaid_popn_3035.geometry.area / SQM_IN_SQKM
    gdf_overlaid_popn_3035['area_perc'] = gdf_overlaid_popn_3035['area_sqkm'].div(gdf_overlaid_popn_3035['area_sqkm_orig']).fillna(0)  

    _cols_to_adjust = [ 'total_owners', 'total_renters', 
                        '1 person in household',
                        'Total Households', 'Total_Popn', 
                        'Resi_Sales_YE_Mar2024','LTE_3rooms']
    for col in _cols_to_adjust:
        gdf_overlaid_popn_3035[col] = gdf_overlaid_popn_3035[col].mul(gdf_overlaid_popn_3035['area_perc']).round(0).astype(int)
    
    # House prices need to be weighted by area  - but first divide through by 1_000 to show as ,000s
    gdf_overlaid_popn_3035['Med_House_Price_YE_Mar2024'] = gdf_overlaid_popn_3035['Med_House_Price_YE_Mar2024'].div(1_000)
    gdf_overlaid_popn_3035['Weighted_Med_House_Price_YE_Mar2024'] = gdf_overlaid_popn_3035['Med_House_Price_YE_Mar2024'].mul(gdf_overlaid_popn_3035['area_sqkm'])

    _groupby_cols = ['storename', 'iso_time_mins' ]
    _sum_cols = [ 'total_owners', 'total_renters',  '1 person in household',
                        'Total Households', 'Total_Popn', 
                        'Weighted_Med_House_Price_YE_Mar2024',
                        'Resi_Sales_YE_Mar2024', 'LTE_3rooms', 'area_sqkm']
    
    gdf_overlaid_popn_groupby = gdf_overlaid_popn_3035.groupby(_groupby_cols)[_sum_cols].sum(_sum_cols)
    gdf_overlaid_popn_groupby = gdf_overlaid_popn_groupby.reset_index()

    # Recalculcate some of the columsn
    gdf_overlaid_popn_groupby['Single_Person_HH_Perc'] = (gdf_overlaid_popn_groupby['1 person in household']
                                                    .div(gdf_overlaid_popn_groupby['Total Households'])
                                                    .fillna(0)
                                                    .mul(100).
                                                    round(2))
    gdf_overlaid_popn_groupby['Popn_Density'] = (gdf_overlaid_popn_groupby['Total_Popn']
                                                    .div(gdf_overlaid_popn_groupby['area_sqkm'])
                                                    .fillna(0)
                                                    .round(0).
                                                    astype(int))
    gdf_overlaid_popn_groupby['Owner_Occ_Perc'] = (gdf_overlaid_popn_groupby['total_owners']
                                                    .div(gdf_overlaid_popn_groupby['Total Households'])
                                                    .fillna(0)
                                                    .mul(100).
                                                    round(2))
    gdf_overlaid_popn_groupby['Avg_HH_Size'] = (gdf_overlaid_popn_groupby['Total_Popn']
                                                    .div(gdf_overlaid_popn_groupby['Total Households'])
                                                    .fillna(0)
                                                    .round(2)
                                                    )
    
    gdf_overlaid_popn_groupby['trans_per_hh_perc'] = (gdf_overlaid_popn_groupby['Resi_Sales_YE_Mar2024']
                                                    .div(gdf_overlaid_popn_groupby['Total Households'])
                                                    .fillna(0)
                                                    .mul(100)
                                                    .round(2)
                                                    )
    gdf_overlaid_popn_groupby['LTE3_rooms_perc'] = (gdf_overlaid_popn_groupby['LTE_3rooms']
                                                    .div(gdf_overlaid_popn_groupby['Total Households'])
                                                    .fillna(0)
                                                    .mul(100)
                                                    .round(2)
                                                    )

    # "De-weight" the cols adjusted by area -just house prices in this instance - and drop the weighted column as it has effectively been rename in the groupby
    gdf_overlaid_popn_groupby['Med_House_Price_YE_Mar2024'] = gdf_overlaid_popn_groupby['Weighted_Med_House_Price_YE_Mar2024'].div(gdf_overlaid_popn_groupby['area_sqkm']).fillna(0).round(0).astype(int)
    gdf_overlaid_popn_groupby.drop(columns=['Weighted_Med_House_Price_YE_Mar2024'], inplace=True)

    # if DEBUG_PRINT:
    #     print(f'****INFO gdf_overlaid_popn_groupby {gdf_overlaid_popn_groupby.columns}')
    
    _cols_to_drop = ['total_owners', 'total_renters',
                        '1 person in household','area_sqkm', 
                        'Resi_Sales_YE_Mar2024','LTE_3rooms'
                        ]

    gdf_overlaid_popn_groupby.drop(columns=_cols_to_drop, inplace=True)
    
    # Add the grouped data to df_demo_summ 
    add_data_to_df_demo_summ(gdf_overlaid_popn_groupby)

    # if DEBUG_PRINT:
    #     print(f'****INFO gdf_overlaid_popn_3035 cols: {gdf_overlaid_popn_3035.columns}')

    _gdf_popn_cols = ['storename', 'iso_time_mins','Total Households',
       'Total_Popn', 'Med_House_Price_YE_Mar2024', 'trans_per_hh_perc',
       'Single_Person_HH_Perc', 'Popn_Density',
       'Owner_Occ_Perc', 'Avg_HH_Size', 'LTE_3Rooms_perc' ,'geometry']
    add_demo_gdf_to_session_state(gdf_overlaid_popn_3035[_gdf_popn_cols].to_crs(4326))

    if DEBUG_PRINT:
        try:    
            gdf_overlaid_popn_3035[_gdf_popn_cols].to_file(r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_popn_overlay.gpkg", driver='GPKG')
            gdf_overlaid_popn_groupby.to_csv(r"D:\D_documents\OldCo\Savills\Scripts\SSST_V2\assets\data\test_df_popn.csv", index=False)
            print(f'****INFO save test version of gdf_popn and df_popn')

        except:
            print(f'!!!!WARNING was not able to save test version of gdf_overlaid_popn')



def return_demo_chloropleth_map(gdf_name, storename, iso_time_mins):

    """Function returns st_folium map object based on input gdf"""

    try:
        required_cols = ['geometry', 'storename' , 'iso_time_mins' ]
        gdf_to_map =  st.session_state.gdf_demo.get(gdf_name)
        if gdf_to_map is None:
            print(f'!!!WARNING return_demo_chloropleth_map did not get any values from st.session_state gdf_demo {gdf_name}')
            return None
        gdf_filtered = gdf_to_map[(gdf_to_map.storename==storename) & (gdf_to_map.iso_time_mins==iso_time_mins)]
        if gdf_filtered.empty:
            print(f'!!!!WARNING could not find values in {gdf_name} that matched the storename: {storename} with an iso_time_mins of: {iso_time_mins}')
            return None
        # Capture the data col - the data column is the only column that is not in the required columns
        data_col = [col for col in gdf_to_map.columns if col not in required_cols]
        if len(data_col) > 1:
            print(f'!!!!WARNING  return_demo_chloropleth_map excess amount of columns for {gdf_name}')
            return None
        if len(data_col) == 0:
            print(f'!!!!WARNING  return_demo_chloropleth_map missing data cols for {gdf_name}')
            return None
        values_col  = data_col[0]
        print(f'****INFO return_demo_chloropleth_map creating chloro map for {values_col}')
        m = folium.Map(location=DEFAULT_MAP_CENTER_LATLON,
                       zoom_start=DEFAULT_MAP_ZOOM_START,
                       tiles=DEFAULT_TILE_LAYER, 
                       width="100%")
        gdf_filtered.explore(m=m,
                        column=values_col,
                        tooltip=values_col,
                        popup=True)
        # iso not required but use for bounds
        _output_iso = get_output_iso(storename=storename , drive_time=iso_time_mins)
        if _output_iso is not None:
            bounds = get_bounds_from_gdf(_output_iso)
            m.fit_bounds(bounds)
        else:
            print(f'!!!!WARNING return_demo_chloropleth_map was not able to set bounds from _output_iso')

        # Render the map
        return st_folium(
            m,
            width="100%",
            height=DEMO_MAP_DISPLAY_HEIGHT_PX,
            returned_objects=[]
        )
    
    except:
        print(f'!!!!WARNING error on return_demo_chloropleth_map')
        return None


def add_demo_gdf_to_session_state(gdf):

    """Function adds input gdf to st.session_state.gdf_demo{}
    The key is the name of the data column header
    The gdf should ONLY contain ['storename', 'iso_time_mins'] [<<data_cols>>] ['geometry']"""

    # For streamlit folium to render needs to be in either 3587 of 4326 - here I will enforce 4326
    if gdf.crs != 4326:
        if DEBUG_PRINT:
            print(f'!!!!WARNING add_demo_gdf_to_session_state received a gdf with crs of {gdf.crs}')
            return


    # this should have been intiialised on loading - but just in case
    if 'gdf_demo' not in st.session_state:
        print(f'!!!!WARNING add_demo_gdf_to_session_state - gdf_demo was not in session_state')
        st.session_state.gdf_demo = {}

    _required_cols = ['storename', 'iso_time_mins','geometry']
    missing_cols = [] 
    for col in _required_cols:
        if col not in gdf.columns:
            missing_cols.append(col)
    if missing_cols:
        print(f'!!!!WARNING add_demo_gdf_to_session_state missing some required cols: {missing_cols} not added gdf to sesion_state')
        return

    data_cols = [col for col in gdf.columns if col not in _required_cols]
    for col in data_cols:
        output_cols = _required_cols + [col]
        gdf_to_save = gdf[output_cols].copy()
        st.session_state.gdf_demo[col] = gdf_to_save
        # if DEBUG_PRINT:
        #     print(f'*****INFO add_demo_gdf_to_session_state saved {col} to gdf_demo session_state dict')
        #     # print out current dictionaries 
        #     try:
        #         print(f'********  add_demo_gdf_to_session_state GDF  ****************')
        #         _gdf_dict = st.session_state.gdf_demo
        #         for k,v in _gdf_dict.items():
        #             print(f'\t {k}')
        #     except:
        #         print(f'****INFO add_demo_gdf_to_session_state could not get hold of gdf_demo info from session_state')




