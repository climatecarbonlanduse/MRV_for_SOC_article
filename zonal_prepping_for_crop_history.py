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
# QGIS Environment Paths
QGIS_HOME_PATH = r'<ENTER_QGIS_HOME_PATH_HERE>'
QGIS_PLUGIN_PATH = r'<ENTER_QGIS_PLUGIN_PATH_HERE>'

# Data Directories
ZONAL_SHP_DIR = r'<ENTER_ZONAL_SHP_DIR_HERE>'
MAJORITY_CROPS_PKL = r'<ENTER_MAJORITY_CROPS_PKL_PATH_HERE>'
BASE_SHP_2020 = r'<ENTER_BASE_SHP_2020_PATH_HERE>'
FINAL_OUT_SHP = r'<ENTER_FINAL_OUT_SHP_PATH_HERE>'


# ============================================================
# INITIALIZATION
# ============================================================
# Start QGIS application environment for spatial processing
app = QgsApplication([], True)
QgsApplication.setPrefixPath(QGIS_HOME_PATH, True)
QgsApplication.initQgis()

sys.path.append(QGIS_PLUGIN_PATH)
Processing.initialize()


# ============================================================
# MAIN FUNCTIONS
# ============================================================

def raster_calc_majority_import():
    """
    Reads zonal shapefiles, isolates the majority crop column for a given year, 
    and ensures standard data typing (float) for aggregation.
    """
    zon_shapes = [f for f in os.listdir(ZONAL_SHP_DIR) if f.endswith('.shp')]
    
    for eachShape in zon_shapes:
        path = os.path.join(ZONAL_SHP_DIR, eachShape)
        dfg = gpd.read_file(path)
        
        # Rename majority crop column to target year and cast to float
        dfgn_ = dfg.rename(columns={'_majority': 'maj2003'})
        dfgn_[['maj2003']] = dfgn_[['maj2003']].astype('float')
        
        # Note: Dataframe can be exported to pickle here for time-series merging

def shapefile_save():
    """
    Loads the aggregated majority crop time-series data (2003-2020) and merges 
    it into the base agricultural block shapefile geometries. 
    Saves the final unified spatial dataset.
    """
    # Load the compiled historical crops dataset
    majority_crops_data = pd.read_pickle(MAJORITY_CROPS_PKL)
    
    # Load base shapefile geometry
    base_data = gpd.read_file(BASE_SHP_2020)
    
    # Dynamically append historical crop columns (2003-2020) to the base spatial data
    years = range(2003, 2021)
    for year in years:
        # Check if year exists in the dataset before appending to avoid KeyError
        if year in majority_crops_data.columns:
            base_data[str(year)] = majority_crops_data[year]
        
    # Export the final consolidated shapefile
    base_data.to_file(FINAL_OUT_SHP)
    print("Shapefile successfully saved.")

# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    # raster_calc_majority_import()
    # shapefile_save()
    pass