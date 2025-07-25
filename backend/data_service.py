import glob
import os
import glob
from typing import Optional

# Lazy import pandas to reduce memory usage during startup
pd = None

def get_pandas():
    """Lazy import pandas to reduce startup memory usage"""
    global pd
    if pd is None:
        try:
            import pandas as pandas_module
            pd = pandas_module
        except ImportError as e:
            print(f"Failed to import pandas: {e}")
            raise
    return pd


def get_csvdf(penfolder: str, beginwith: str, include_filename: bool = False):
    """
    Load and concatenate CSV files from a folder that begin with a specific string.
    
    Args:
        penfolder: Path to the folder containing CSV files
        beginwith: String that filenames should begin with
        include_filename: If True, adds a 'source_filename' column to track which file each row came from
        
    Returns:
        Concatenated DataFrame from all matching CSV files
    """
    import time
    import threading
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
    
    # Check if directory exists first to avoid long waits
    if not os.path.exists(penfolder):
        print(f"Directory does not exist: {penfolder}")
        return get_pandas().DataFrame()
    
    def search_files():
        """Search for CSV files with timeout protection"""
        return glob.glob(os.path.join(penfolder, f"{beginwith}*.csv"), recursive=False)
    
    try:
        start_time = time.time()
        
        # Use ThreadPoolExecutor with timeout for file search
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(search_files)
            try:
                files = future.result(timeout=30)  # Increased to 30 second timeout for file search
            except FutureTimeoutError:
                print(f"File search timed out after 30 seconds in {penfolder}")
                return get_pandas().DataFrame()
        
        search_time = time.time() - start_time
        print(f"File search took {search_time:.2f} seconds, found {len(files)} files")
        
        if not files:
            print(f"No CSV files found matching pattern: {beginwith}*.csv in {penfolder}")
            return get_pandas().DataFrame()
        
        dflist = []
        
        for i, filepath in enumerate(files):
            try:
                print(f"Reading file {i+1}/{len(files)}: {os.path.basename(filepath)}")
                
                # Use ThreadPoolExecutor with timeout for individual file reading
                def read_single_file():
                    return get_pandas().read_csv(filepath, encoding='utf-8-sig')
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(read_single_file)
                    try:
                        df = future.result(timeout=20)  # Increased to 20 second timeout per file
                        
                        # Add filename column if requested
                        if include_filename and not df.empty:
                            filename = os.path.basename(filepath)
                            df['source_filename'] = filename
                        
                        dflist.append(df)
                    except FutureTimeoutError:
                        print(f"Timeout reading {filepath}, skipping")
                        continue
                    
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue
        
        if len(dflist) > 0:
            result_df = get_pandas().concat(dflist, ignore_index=True)
            print(f"Successfully loaded {len(result_df)} rows from {len(dflist)} files")
            return result_df
        else:
            print("No data loaded from any files")
            return get_pandas().DataFrame()
            
    except Exception as e:
        print(f"Error accessing directory {penfolder}: {e}")
        return get_pandas().DataFrame()


def get_csrc2detail():
    """
    Get CSRC2 detail data from CSV files.
    
    Returns:
        DataFrame with CSRC2 detail data
    """
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2 = os.path.join(project_root, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 data in: {pencsrc2}")
    pendf = get_csvdf(pencsrc2, "csrcdtlall")
    
    if not pendf.empty:
        # Format date - handle both timestamp and date formats
        if "发文日期" in pendf.columns:
            # First try to convert timestamps (numeric values) to datetime
            def convert_date(date_val):
                if get_pandas().isna(date_val) or date_val == "":
                    return ""
                
                # If it's a numeric timestamp, convert it
                try:
                    # Check if it's a numeric timestamp (seconds or milliseconds)
                    if str(date_val).replace('.', '').isdigit():
                        timestamp = float(date_val)
                        # If timestamp is in milliseconds (> 1e10), convert to seconds
                        if timestamp > 1e10:
                            timestamp = timestamp / 1000
                        return get_pandas().to_datetime(timestamp, unit='s').strftime('%Y-%m-%d')
                    else:
                        # Try to parse as regular date string and return as string
                        parsed_date = get_pandas().to_datetime(date_val, errors='coerce')
                        if get_pandas().isna(parsed_date):
                            return ""
                        return parsed_date.strftime('%Y-%m-%d')
                except (ValueError, TypeError, OverflowError):
                    # If conversion fails, return empty string
                    return ""
            
            pendf["发文日期"] = pendf["发文日期"].apply(convert_date)
        # Fill NaN values
        pendf = pendf.fillna("")
    
    return pendf


def get_csrc2label():
    """
    Get CSRC2 label data from CSV files.
    
    Returns:
        DataFrame with CSRC2 label data
    """
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2 = os.path.join(project_root, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 label data in: {pencsrc2}")
    labeldf = get_csvdf(pencsrc2, "csrc2label")
    
    if not labeldf.empty:
        # Fill NaN values
        labeldf = labeldf.fillna("")
    
    return labeldf


def get_csrc2analysis():
    """
    Get CSRC2 analysis data from CSV files.
    
    Returns:
        DataFrame with CSRC2 analysis data including source filename
    """
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2 = os.path.join(project_root, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 analysis data in: {pencsrc2}")
    pendf = get_csvdf(pencsrc2, "csrc2analysis", include_filename=True)
    
    if not pendf.empty:
        # Format date - handle both timestamp and date formats
        if "发文日期" in pendf.columns:
            # First try to convert timestamps (numeric values) to datetime
            def convert_date(date_val):
                if get_pandas().isna(date_val) or date_val == "":
                    return ""
                
                # If it's a numeric timestamp, convert it
                try:
                    # Check if it's a numeric timestamp (seconds or milliseconds)
                    if str(date_val).replace('.', '').isdigit():
                        timestamp = float(date_val)
                        # If timestamp is in milliseconds (> 1e10), convert to seconds
                        if timestamp > 1e10:
                            timestamp = timestamp / 1000
                        return get_pandas().to_datetime(timestamp, unit='s').strftime('%Y-%m-%d')
                    else:
                        # Try to parse as regular date string and return as string
                        parsed_date = get_pandas().to_datetime(date_val, errors='coerce')
                        if get_pandas().isna(parsed_date):
                            return ""
                        return parsed_date.strftime('%Y-%m-%d')
                except (ValueError, TypeError, OverflowError):
                    # If conversion fails, return empty string
                    return ""
            
            pendf["发文日期"] = pendf["发文日期"].apply(convert_date)
        # Fill NaN values
        pendf = pendf.fillna("")
    
    return pendf


def get_csrc2cat():
    """
    Get CSRC2 category data from CSV files.
    
    Returns:
        DataFrame with CSRC2 category data
    """
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2 = os.path.join(project_root, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 category data in: {pencsrc2}")
    amtdf = get_csvdf(pencsrc2, "csrccat")
    
    if not amtdf.empty:
        # Process amount column
        if "amount" in amtdf.columns:
            # Only fill blank/null values with 0, leave other values unchanged
            # First, identify truly blank values (empty strings, None, NaN)
            blank_mask = amtdf["amount"].isna() | (amtdf["amount"] == "") | (amtdf["amount"] == "")
            # Fill only blank values with 0
            amtdf.loc[blank_mask, "amount"] = 0
            # Convert to numeric, but preserve existing non-blank values
            amtdf["amount"] = get_pandas().to_numeric(amtdf["amount"], errors='coerce')
        # Rename columns law to lawlist
        if "law" in amtdf.columns:
            amtdf.rename(columns={"law": "lawlist"}, inplace=True)
        # Fill NaN values for other columns
        amtdf = amtdf.fillna("")
    
    return amtdf


def get_csrc2split():
    """
    Get CSRC2 split data from CSV files.
    
    Returns:
        DataFrame with CSRC2 split data
    """
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2 = os.path.join(project_root, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 split data in: {pencsrc2}")
    pendf = get_csvdf(pencsrc2, "csrcsplit")
    
    if not pendf.empty:
        # Fill NaN values
        pendf = pendf.fillna("")
    
    return pendf


def get_csrc2_intersection():
    """
    Get intersection of csrc2analysis, csrccat, and csrcsplit data.
    
    Returns:
        DataFrame with intersection of three data sources based on common IDs
    """
    print("Loading three data sources for intersection...")
    
    # Load all three data sources
    analysis_df = get_csrc2analysis()
    cat_df = get_csrc2cat()
    split_df = get_csrc2split()
    
    if analysis_df.empty or cat_df.empty or split_df.empty:
        print("One or more data sources are empty, returning empty DataFrame")
        return get_pandas().DataFrame()
    
    print(f"Analysis data: {len(analysis_df)} rows")
    print(f"Category data: {len(cat_df)} rows")
    print(f"Split data: {len(split_df)} rows")
    
    # Check if required columns exist
    # Analysis uses '链接', others use 'id'
    if '链接' not in analysis_df.columns:
        print("Missing '链接' column in analysis data")
        return get_pandas().DataFrame()
    if 'id' not in cat_df.columns:
        print("Missing 'id' column in category data")
        return get_pandas().DataFrame()
    if 'id' not in split_df.columns:
        print("Missing 'id' column in split data")
        return get_pandas().DataFrame()
    
    # Get common IDs across all three datasets
    # Convert analysis '链接' to match 'id' format
    analysis_ids = set(analysis_df['链接'].dropna())
    cat_ids = set(cat_df['id'].dropna())
    split_ids = set(split_df['id'].dropna())
    
    common_ids = analysis_ids & cat_ids & split_ids
    print(f"Found {len(common_ids)} common IDs in intersection")
    
    if not common_ids:
        print("No common IDs found, returning empty DataFrame")
        return get_pandas().DataFrame()
    
    # Filter datasets to only include common IDs
    analysis_filtered = analysis_df[analysis_df['链接'].isin(common_ids)].copy()
    cat_filtered = cat_df[cat_df['id'].isin(common_ids)].copy()
    split_filtered = split_df[split_df['id'].isin(common_ids)].copy()
    
    # Rename 'id' columns to '链接' for consistent merging
    cat_filtered = cat_filtered.rename(columns={'id': '链接'})
    split_filtered = split_filtered.rename(columns={'id': '链接'})
    
    # Merge with category data to get additional fields like amount, lawlist, category, province, industry
    cat_subset = cat_filtered[['链接', 'amount', 'lawlist', 'category', 'province', 'industry']]
    intersection_df = analysis_filtered.merge(cat_subset, on='链接', how='left')
    
    # Merge with split data to get people, event, law, penalty, org, date
    split_subset = split_filtered[['链接', 'people', 'event', 'law', 'penalty', 'org', 'date']]
    intersection_df = intersection_df.merge(split_subset, on='链接', how='left')
    
    # Rename amount to 罚款金额 for consistency
    if 'amount' in intersection_df.columns:
        intersection_df['罚款金额'] = intersection_df['amount']
    
    # Rename lawlist to 法律依据 for consistency
    if 'lawlist' in intersection_df.columns:
        intersection_df['法律依据'] = intersection_df['lawlist']
    
    print(f"Intersection result: {len(intersection_df)} rows with {len(intersection_df.columns)} columns")
    return intersection_df


def get_csrclenanalysis():
    """
    Get CSRC length analysis dataframe including source filename.
    
    Returns:
        DataFrame with CSRC length analysis data from temp directory
    """
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
    
    print(f"Looking for CSRC length analysis data in: {tempdir}")
    pendf = get_csvdf(tempdir, "csrclenanalysis", include_filename=True)
    
    if not pendf.empty:
        pendf = pendf.fillna("")
    
    return pendf