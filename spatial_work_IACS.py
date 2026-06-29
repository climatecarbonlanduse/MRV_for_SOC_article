"""
Intellectual property of Andreas Rehn.
Created for research purposes and should be used in association with climate mitigation research in agricultural system transitions.

Code part of the article: Building a platform for regionalized monitoring, reporting and verification (MRV) for soil organic carbon (SOC) change in agriculture – case Sweden.
"""

import re
import zipfile
import tempfile
import shutil
from pathlib import Path
import subprocess
import time

import pandas as pd
import geopandas as gpd

# ============================================================
# CONFIGURATION
# ============================================================
# Directory containing the zipped agricultural block shapefiles
ZIPS_DIR = Path("<ENTER_YOUR_ZIPS_DIR_PATH_HERE>")

ZIP_FILES = [
    ZIPS_DIR / "MULTI.JORDBRUKSBLOCK_GRODKOD2003-2004_GV.zip",
    ZIPS_DIR / "MULTI.JORDBRUKSBLOCK_GRODKOD2005-2007_GV.zip",
    ZIPS_DIR / "MULTI.JORDBRUKSBLOCK_GRODKOD2008-2012_GV.zip",
    ZIPS_DIR / "MULTI.JORDBRUKSBLOCK_GRODKOD2013-2017_GV.zip",
    ZIPS_DIR / "MULTI.JORDBRUKSBLOCK_GRODKOD2018-2020_GV.zip",
]

# Order of processing (True = newest data first)
PROCESS_NEWEST_FIRST = True

# Target points shapefile for the spatial join
POINTS_SHP = Path("<ENTER_YOUR_POINTS_SHP_PATH_HERE>")

# Output directory and file configurations
OUT_DIR = Path("./outputs_blockids")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_GPKG = OUT_DIR / "SASI_points_with_blockids_2003_2020.gpkg"
OUT_SHP  = OUT_DIR / "SASI_points_with_blockids_2003_2020.shp"
OUT_XLSX = OUT_DIR / "SASI_points_with_blockids_2003_2020.xlsx"

# Temporal constraints for validation
YEAR_MIN, YEAR_MAX = 2003, 2020

# Column mapping variables
BLOCKID_COL_CANDIDATES = ["GEOGRAFISK"]
POINT_ID_COL = "pt_id"

# Spatial join parameters
# "within" is strict for point-in-polygon mapping. 
# Toggle USE_INTERSECTS_WITH_BUFFER to True if boundary jitter creates omissions.
PREDICATE = "within"
USE_INTERSECTS_WITH_BUFFER = False
POINT_BUFFER_METERS = 0.5  


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def parse_zip_years(zip_path: Path):
    """
    Extracts the year range from the zip filename (e.g., GRODKOD2008-2012).
    Returns a tuple: (start_year, end_year) or (None, None).
    """
    m = re.search(r"GRODKOD((19|20)\d{2})-((19|20)\d{2})", zip_path.name)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(3))


def pick_existing_col(gdf, candidates):
    """
    Identifies the first matching column name from a list of candidates.
    """
    cols = set(gdf.columns)
    for c in candidates:
        if c in cols:
            return c
    return None


def infer_year_from_filename(path: Path):
    """
    Extracts a 4-digit year string from a shapefile name, returning as an integer.
    """
    m = re.search(r"(19|20)\d{2}", path.name)
    return int(m.group(0)) if m else None


def ensure_points_id(points: gpd.GeoDataFrame, id_col: str) -> gpd.GeoDataFrame:
    """
    Ensures a stable ID column exists in the dataset. Generates an index-based ID if missing.
    """
    if id_col in points.columns:
        return points
    points = points.copy()
    points[id_col] = range(1, len(points) + 1)
    return points


def safe_spatial_join(points: gpd.GeoDataFrame, blocks: gpd.GeoDataFrame, blockid_col: str) -> pd.DataFrame:
    """
    Executes a spatial join between point data and polygon blocks. 
    Applies an optional geometry buffer to points if USE_INTERSECTS_WITH_BUFFER is active.
    Returns a DataFrame containing point IDs mapped to block IDs.
    """
    pts = points
    predicate = PREDICATE

    if USE_INTERSECTS_WITH_BUFFER:
        pts = points.copy()
        pts["geometry"] = pts.geometry.buffer(POINT_BUFFER_METERS)
        predicate = "intersects"

    joined = gpd.sjoin(
        pts[[POINT_ID_COL, "geometry"]],
        blocks[[blockid_col, "geometry"]],
        how="left",
        predicate=predicate
    )

    out = joined[[POINT_ID_COL, blockid_col]].copy()
    out = out.rename(columns={blockid_col: "block_id"})
    
    # Drop duplicates to ensure 1:1 mapping in the event of polygon overlap
    out = out.drop_duplicates(subset=[POINT_ID_COL], keep="first")
    return out


# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    
    start_time = time.time()

    # Validate zip file paths
    for z in ZIP_FILES:
        if not z.exists():
            raise FileNotFoundError(f"Missing zip archive: {z}")

    # Load and validate points data
    points = gpd.read_file(POINTS_SHP)
    if points.crs is None:
        raise ValueError("Points CRS is None. A defined CRS is required for spatial joining.")

    points = ensure_points_id(points, POINT_ID_COL)

    # Initialize master lookup table for mapped associations
    lookup_rows = []

    # Apply specified processing order
    zips = ZIP_FILES[::-1] if PROCESS_NEWEST_FIRST else ZIP_FILES

    for zpath in zips:
        y0, y1 = parse_zip_years(zpath)
        print(f"\n=== Processing ZIP: {zpath.name} (Years {y0}-{y1}) ===")

        tmpdir = Path(tempfile.mkdtemp(prefix="jb_"))
        try:
            subprocess.run(
                ["unzip", "-q", str(zpath), "-d", str(tmpdir)],
                check=True
            )

            shp_files = sorted(tmpdir.rglob("*.shp"))
            if not shp_files:
                print("  No .shp files located in archive. Skipping.")
                continue

            for shp in shp_files:
                year = infer_year_from_filename(shp)
                blocks = gpd.read_file(shp)
                
                if blocks.crs is None:
                    raise ValueError(f"Blocks CRS is None for {shp}. Spatial join aborted.")

                # Harmonize Coordinate Reference Systems
                if blocks.crs != points.crs:
                    blocks = blocks.to_crs(points.crs)

                blockid_col = pick_existing_col(blocks, BLOCKID_COL_CANDIDATES)
                if blockid_col is None:
                    raise ValueError(
                        f"Missing BLOCKID column in {shp.name}. "
                        f"Target parameters: {BLOCKID_COL_CANDIDATES}\n"
                        f"Available columns: {list(blocks.columns)}"
                    )

                # Process based on inferred year from filename
                if year is not None and YEAR_MIN <= year <= YEAR_MAX:
                    print(f"  - {shp.name} -> Target year {year}")
                    joined_df = safe_spatial_join(points, blocks, blockid_col)
                    joined_df["year"] = year
                    lookup_rows.append(joined_df)
                    continue

                # Fallback: Process based on internal attribute data
                year_col_candidates = ["YEAR", "Year", "AR", "ÅR", "Ar", "ars", "year"]
                year_col = pick_existing_col(blocks, year_col_candidates)

                if year_col is None:
                    print(f"  - {shp.name}: Cannot infer year from filename or attributes. Skipping.")
                    continue

                blocks[year_col] = pd.to_numeric(blocks[year_col], errors="coerce")
                years_in_file = sorted({int(y) for y in blocks[year_col].dropna().unique() if YEAR_MIN <= int(y) <= YEAR_MAX})

                if not years_in_file:
                    print(f"  - {shp.name}: Attribute '{year_col}' contains no valid years. Skipping.")
                    continue

                print(f"  - {shp.name}: Segmenting by attribute '{year_col}' for years {years_in_file}")
                for yy in years_in_file:
                    sub = blocks[blocks[year_col] == yy].copy()
                    joined_df = safe_spatial_join(points, sub, blockid_col)
                    joined_df["year"] = yy
                    lookup_rows.append(joined_df)

        finally:
            # Purge temporary extraction directory to free memory
            shutil.rmtree(tmpdir, ignore_errors=True)

    if not lookup_rows:
        raise RuntimeError("No spatial joins completed successfully. Verify shapefile contents and year logic.")

    lookup = pd.concat(lookup_rows, ignore_index=True)
    lookup = lookup.drop_duplicates(subset=[POINT_ID_COL, "year"], keep="first")

    # Pivot joined data to a wide format for output
    wide = lookup.pivot(index=POINT_ID_COL, columns="year", values="block_id").reset_index()
    wide = wide.rename(columns={y: f"blockid_{int(y)}" for y in wide.columns if isinstance(y, (int, float))})

    points_out = points.merge(wide, on=POINT_ID_COL, how="left")

    # Write output to GeoPackage
    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    points_out.to_file(OUT_GPKG, layer="points", driver="GPKG")
    print(f"\nWrite successful. GeoPackage output: {OUT_GPKG}")

    # Write output to Shapefile (Note: possible column truncation)
    if OUT_SHP.exists():
        for f in OUT_SHP.parent.glob(OUT_SHP.stem + ".*"):
            f.unlink(missing_ok=True)
    points_out.to_file(OUT_SHP, driver="ESRI Shapefile")
    print(f"Write successful. Shapefile output: {OUT_SHP}")

    # Write non-spatial output to Excel
    non_geom = pd.DataFrame(points_out.drop(columns="geometry"))
    non_geom.to_excel(OUT_XLSX, index=False)
    print(f"Write successful. Excel output: {OUT_XLSX}")
    
    end_time = time.time()
    print(f"\nProcessing complete in {round(end_time - start_time, 2)} seconds.")

if __name__ == "__main__":
    main()