"""
Intellectual property of Andreas Rehn.
Created for research purposes and should be used in association with climate mitigation research in agricultural system transitions.

Code part of the article: Building a platform for regionalized monitoring, reporting and verification (MRV) for soil organic carbon (SOC) change in agriculture – case Sweden.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os

# ============================================================
# CONFIGURATION & PATHS
# ============================================================
INPUT_SHP_PATH = r'<ENTER_INPUT_SHP_PATH_HERE>'
OUT_DIR = r'<ENTER_OUTPUT_DIRECTORY_HERE>'

# Pre-defined output paths based on OUT_DIR
CROP_COUNT_CSV = os.path.join(OUT_DIR, 'dff_cropcount.csv')
MCD_FULL_SHP = os.path.join(OUT_DIR, 'mcd_full_noshare_balj.shp')
MCD_FULL_PKL = os.path.join(OUT_DIR, 'sweden_mcd_full_noshare_balj.pkl')
MCD_FULL_XLS = os.path.join(OUT_DIR, 'correct_crop_noshare_balj.xls')
MCD_WORK_PKL = os.path.join(OUT_DIR, 'df_mcd_work.pkl')
FILTERED_IQR_CSV = os.path.join(OUT_DIR, 'df_filteredIQR.csv')

# Crop Categorization Codes
SPANN_VALUES = [1, 2, 3, 4, 5, 7, 8, 13, 12, 10]
RAPS_VALUES = [20, 21, 22, 23, 25]
VALL_VALUES = [16, 49, 50, 53, 58, 59, 80, 62]
BALJ_VALUES = [30, 31, 32, 34, 43, 35, 37, 39]
OVRIGT_VALUES = [95, 90, 89, 88, 82, 81, 68, 67, 66, 65, 52, 45, 34, 32, 31, 23, 6]
TRADA_VALUES = [60]


# ============================================================
# DATA PROCESSING FUNCTIONS
# ============================================================

def crop_start(input_path):
    """
    Loads initial spatial data, cleans missing variables (clay, sample years), 
    and calculates SOC to clay ratios and carbon differences over time.
    """
    df_working = gpd.read_file(input_path)
    df_working['c'] = df_working['c'].astype(float)
    
    # Remove rows missing crucial spatial/soil properties
    df_working = df_working[pd.notnull(df_working['ler'])]
    df_working = df_working[pd.notnull(df_working['prov_ar_2'])]
    df_working = df_working[pd.notnull(df_working['c_2'])]

    # Calculate temporal differences and SOC/Clay ratios
    df_working['time'] = df_working['prov_ar_2'] - df_working['prov_ar']
    df_working['c_diff'] = df_working['c_2'] - df_working['c']
    
    df_working['socclay_1'] = df_working['c'] / df_working['ler']
    df_working['socclay_2'] = df_working['c_2'] / df_working['ler']
    df_working['socclay_diff'] = df_working['socclay_2'] - df_working['socclay_1']
   
    # Isolate yearly major crop columns for counting
    year_cols = [f'{year}_major' for year in range(2020, 2002, -1)] + ['time']
    df_years = df_working[year_cols].copy()
    df_anno_work = df_years[pd.notnull(df_years['time'])]
    
    return df_working, df_anno_work


def crop_sort(df_main, df_years):
    """
    Categorizes the yearly crop codes into broad functional groups and sums 
    their occurrences over the time series for each spatial block.
    """
    dff = df_years.copy()

    # Sum occurrences of crop groups across the time series
    dff['cerealnum'] = dff.isin(SPANN_VALUES).sum(axis=1)
    dff['vallnum'] = dff.isin(VALL_VALUES).sum(axis=1)
    dff['rapsnum'] = dff.isin(RAPS_VALUES).sum(axis=1)
    dff['ovrigtnum'] = dff.isin(OVRIGT_VALUES).sum(axis=1)
    dff['tradanum'] = dff.isin(TRADA_VALUES).sum(axis=1)
    
    # Save the standalone crop counts
    dff.to_csv(CROP_COUNT_CSV, sep=';')
    
    # Merge categorized counts back to the main dataframe
    df_main['cereal'] = dff['cerealnum'].values
    df_main['vall'] = dff['vallnum'].values
    df_main['raps'] = dff['rapsnum'].values
    df_main['ovrigt'] = dff['ovrigtnum'].values
    df_main['trada'] = dff['tradanum'].values
    
    # Export spatial and tabular datasets
    df_saving = gpd.GeoDataFrame(df_main)
    df_saving.to_file(MCD_FULL_SHP)
    df_saving.to_pickle(MCD_FULL_PKL)
    
    # Cast geometries to string or drop for standard Excel export
    pd.DataFrame(df_saving.drop(columns='geometry')).to_excel(MCD_FULL_XLS, index=False)
    
    return df_saving


def mcd_analysis_prep(df_mcd):
    """
    Filters the consolidated dataset to required variables and recalculates 
    SOC/Clay dynamics to ensure consistency before statistical analysis.
    """
    target_columns = [
        'AREAL', 'x', 'y', 'pH', 'c', 'n', 'c/n', 'cacao', 'orgmat', 'ler', 
        'pH_2', 'c_2', 'n_2', 'c/n_2', 'orgmat_2', 'geometry', 'time', 
        'share_cereal', 'share_vall', 'share_raps', 'share_ovrigt', 'share_trada', 
        'KUND_LAN', 'GRODKOD', 'GRODBESKRI', 'AREAL_2'
    ]
    
    # Ensure columns exist to avoid KeyError
    existing_cols = [col for col in target_columns if col in df_mcd.columns]
    df_mcd_work = df_mcd[existing_cols].copy()

    df_mcd_work['socclay_1'] = df_mcd_work['c'] / df_mcd_work['ler']
    df_mcd_work['socclay_2'] = df_mcd_work['c_2'] / df_mcd_work['ler']
    df_mcd_work['socclay_diff'] = df_mcd_work['socclay_2'] - df_mcd_work['socclay_1']
    
    df_mcd_work.to_pickle(MCD_WORK_PKL)
    return df_mcd_work


def mcd_analysis_iqr(df_mcd_work):
    """
    Applies the Interquartile Range (IQR) method to remove outliers based 
    on the initial carbon ('c') concentration.
    """
    df_decimals = df_mcd_work[pd.notnull(df_mcd_work['time'])].round(decimals=3)
    
    # Isolate analysis columns
    analysis_cols = [
        'pH', 'c', 'n', 'c/n', 'orgmat', 'ler', 'pH_2', 'c_2', 'n_2', 'c/n_2', 
        'orgmat_2', 'time', 'share_cereal', 'share_vall', 'share_raps', 
        'share_ovrigt', 'share_trada', 'socclay_1', 'socclay_2', 'socclay_diff',
        'KUND_LAN', 'GRODKOD', 'GRODBESKRI', 'AREAL_2'
    ]
    
    existing_cols = [col for col in analysis_cols if col in df_decimals.columns]
    dff_mcd_w = df_decimals[existing_cols].copy()
    
    # IQR Outlier Removal Logic
    percentile25 = dff_mcd_w['c'].quantile(0.25)
    percentile75 = dff_mcd_w['c'].quantile(0.75)
    iqr = percentile75 - percentile25
    
    upper_limit = percentile75 + 1.5 * iqr
    lower_limit = percentile25 - 1.5 * iqr
    
    df_filtered_iqr = dff_mcd_w[(dff_mcd_w['c'] <= upper_limit) & (dff_mcd_w['c'] >= lower_limit)]
    
    # Save the filtered dataset for final modeling
    df_filtered_iqr.to_csv(FILTERED_IQR_CSV, index=False)
    print(f"Data cleaned via IQR. Original rows: {len(dff_mcd_w)}. Cleaned rows: {len(df_filtered_iqr)}.")
    
    return df_filtered_iqr


# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    # Ensure output directory exists
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # 1. Start and clean the base data
    df_working, df_anno_work = crop_start(INPUT_SHP_PATH)
    
    # 2. Sort crops and generate master shapefile/pickle
    df_mcd_full = crop_sort(df_working, df_anno_work)
    
    # 3. Filter variables for statistical modeling
    df_mcd_work = mcd_analysis_prep(df_mcd_full)
    
    # 4. Remove outliers via IQR and save final analytical dataset
    df_clean_final = mcd_analysis_iqr(df_mcd_work)