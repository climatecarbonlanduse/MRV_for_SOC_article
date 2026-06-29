# Codes in Python used for article
Code sharing for the article Building a platform for regionalized monitoring, reporting and verification (MRV) for soil organic carbon (SOC) change in agriculture – case Sweden



Listed are the methods developed and the codes that are linked to these for full transparancy of the method of the article


##
##

spatial_work_IACS.py - this file is a starting point of using the IACS data to create a long term history/record of land use. Specificed for Sweden should be adapted for national or regional purpose. 

##
##

zonal_prepp.py - this script compiles a historical crop time-series. It takes spatial data (likely zonal statistics from rasters) representing the dominant ("majority") crop grown on specific agricultural blocks for each year. It formats this data and merges the historical timeline (2003–2020) into a single master shapefile.
