"""
Intellectual property of Andreas Rehn.
Created for research purposes and should be used in association with climate mitigation research in agricultural system transitions.

Code part of the article: Building a platform for regionalized monitoring, reporting and verification (MRV) for soil organic carbon (SOC) change in agriculture – case Sweden.
"""

import os
import sys
import pandas as pd
import geopandas as gpd
from qgis.core import QgsApplication
import processing
from processing.core.Processing import Processing

# ============================================================
# CONFIGURATION & PATHS
# ============================================================
QGIS_HOME_PATH = r'<ENTER_QGIS_HOME_PATH_HERE>'
QGIS_PLUGIN_PATH = r'<ENTER_QGIS_PLUGIN_PATH_HERE>'

# Data directories
INPUT_DIR = r'<ENTER_INPUT_DIR_PATH_HERE>'
OUTPUT_DIR = r'<ENTER_OUTPUT_DIR_PATH_HERE>'

# ============================================================
# INITIALIZATION
# ============================================================
app = QgsApplication([], True)
QgsApplication.setPrefixPath(QGIS_HOME_PATH, True)
QgsApplication.initQgis()

sys.path.append(QGIS_PLUGIN_PATH)
Processing.initialize()

# ============================================================
# CORE PROCESSING FUNCTIONS
# ============================================================

def process_majority_data(input_shp_path):
    """
    Sorts and filters the majority crop data. Removes records outside the study 
    area (NaN ler/clay), calculates SOC/clay ratios, and aggregates crop 
    shares over time.
    """
    # Load and prepare initial data
    df_work = gpd.read_file(input_shp_path)
    
    # Remove records missing soil property data
    df_work = df_work[df_work['ler'].notnull()]
    
    # Ensure unique records per block based on ID and Area
    df_clean = df_work.sort_values(['BLOCKID', 'AREAL'], ascending=[True, False]) \
                      .drop_duplicates(['BLOCKID']).reset_index(drop=True)
    
    # Cast necessary columns to float for calculation
    for col in ['c', 'c_2', 'ler', 'ler_2']:
        df_clean[col] = df_clean[col].astype(float)
    
    # Filter by valid time/year entries and calculate temporal metrics
    df_clean = df_clean[df_clean['year_2'].notnull() & df_clean['year_1'].notnull()]
    df_clean['time'] = df_clean['year_2'] - df_clean['year_1']
    df_clean['c_diff'] = df_clean['c_2'] - df_clean['c']
    
    df_clean['socclay_1'] = df_clean['c'] / df_clean['ler']
    df_clean['socclay_2'] = df_clean['c_2'] / df_clean['ler']
    df_clean['socclay_diff'] = df_clean['socclay_2'] - df_clean['socclay_1']
    
    return df_clean

def calculate_crop_shares(df_main):
    """
    Categorizes crop years into groups and calculates their proportional 
    share over the study period.
    """
    # Define crop code categories
    crop_groups = {
        'cereal': [1, 2, 3, 4, 5, 7, 8],
        'raps': [20, 21],
        'vall': [16, 49, 50, 53, 58, 59, 80, 62],
        'ovrigt': [95, 90, 89, 88, 82, 81, 68, 67, 66, 65, 52, 45, 34, 32, 31, 23, 12, 6],
        'trada': [60]
    }
    
    year_cols = [str(y) for y in range(2003, 2021)]
    df_years = df_main[year_cols].copy()
    
    # Count occurrences of each crop group
    for group, codes in crop_groups.items():
        df_main[group] = df_years.isin(codes).sum(axis=1)
        # Calculate share based on total time span
        df_main[f'share_{group}'] = (df_main[group] / df_main['time']) / 1.8
        
    return df_main

# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    # Path to the majority merge shapefile
    input_file = os.path.join(INPUT_DIR, "majority_merge3.shp")
    
    # Process data
    df_result = process_majority_data(input_file)
    df_final = calculate_crop_shares(df_result)
    
    # Final cleanup: drop processed year columns and save
    cols_to_drop = [str(y) for y in range(2003, 2021)]
    df_final.drop(columns=cols_to_drop, inplace=True)
    
    print("Processing complete. Final dataframe ready for analysis.")