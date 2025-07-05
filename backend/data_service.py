import glob
import os
from typing import Optional

import pandas as pd


def get_csvdf(penfolder: str, beginwith: str) -> pd.DataFrame:
    """
    Load and concatenate CSV files from a folder that begin with a specific string.

    Args:
        penfolder: Path to the folder containing CSV files
        beginwith: String that filenames should begin with

    Returns:
        Concatenated DataFrame from all matching CSV files
    """
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as FutureTimeoutError

    # Check if directory exists first to avoid long waits
    if not os.path.exists(penfolder):
        print(f"Directory does not exist: {penfolder}")
        return pd.DataFrame()

    def search_files():
        """Search for CSV files with timeout protection"""
        return glob.glob(
            os.path.join(penfolder, "**", f"{beginwith}*.csv"), recursive=True
        )

    try:
        start_time = time.time()

        # Use ThreadPoolExecutor with timeout for file search
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(search_files)
            try:
                files = future.result(
                    timeout=30
                )  # Increased to 30 second timeout for file search
            except FutureTimeoutError:
                print(f"File search timed out after 30 seconds in {penfolder}")
                return pd.DataFrame()

        search_time = time.time() - start_time
        print(f"File search took {search_time:.2f} seconds, found {len(files)} files")

        if not files:
            print(
                f"No CSV files found matching pattern: {beginwith}*.csv in {penfolder}"
            )
            return pd.DataFrame()

        dflist = []

        for i, filepath in enumerate(files):
            try:
                print(f"Reading file {i+1}/{len(files)}: {os.path.basename(filepath)}")

                # Use ThreadPoolExecutor with timeout for individual file reading
                def read_single_file():
                    return pd.read_csv(filepath)

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(read_single_file)
                    try:
                        df = future.result(
                            timeout=20
                        )  # Increased to 20 second timeout per file
                        dflist.append(df)
                    except FutureTimeoutError:
                        print(f"Timeout reading {filepath}, skipping")
                        continue

            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue

        if len(dflist) > 0:
            result_df = pd.concat(dflist, ignore_index=True)
            print(f"Successfully loaded {len(result_df)} rows from {len(dflist)} files")
            return result_df
        else:
            print("No data loaded from any files")
            return pd.DataFrame()

    except Exception as e:
        print(f"Error accessing directory {penfolder}: {e}")
        return pd.DataFrame()


def get_csrc2detail() -> pd.DataFrame:
    """
    Get CSRC2 detail data from CSV files.

    Returns:
        DataFrame with CSRC2 detail data
    """
    # Use absolute path to ensure it works from any working directory
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pencsrc2 = os.path.join(base_dir, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 data in: {pencsrc2}")
    pendf = get_csvdf(pencsrc2, "csrcdtlall")

    if not pendf.empty:
        # Format date
        if "发文日期" in pendf.columns:
            pendf["发文日期"] = pd.to_datetime(
                pendf["发文日期"], errors="coerce"
            ).dt.date
        # Fill NaN values
        pendf = pendf.fillna("")

    return pendf


def get_csrc2label() -> pd.DataFrame:
    """
    Get CSRC2 label data from CSV files.

    Returns:
        DataFrame with CSRC2 label data
    """
    # Use absolute path to ensure it works from any working directory
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pencsrc2 = os.path.join(base_dir, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 label data in: {pencsrc2}")
    labeldf = get_csvdf(pencsrc2, "csrc2label")

    if not labeldf.empty:
        # Fill NaN values
        labeldf = labeldf.fillna("")

    return labeldf


def get_csrc2analysis() -> pd.DataFrame:
    """
    Get CSRC2 analysis data from CSV files.

    Returns:
        DataFrame with CSRC2 analysis data
    """
    # Use absolute path to ensure it works from any working directory
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pencsrc2 = os.path.join(base_dir, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 analysis data in: {pencsrc2}")
    pendf = get_csvdf(pencsrc2, "csrc2analysis")

    if not pendf.empty:
        # Format date
        if "发文日期" in pendf.columns:
            pendf["发文日期"] = pd.to_datetime(
                pendf["发文日期"], errors="coerce"
            ).dt.date
        # Fill NaN values
        pendf = pendf.fillna("")

    return pendf


def get_csrc2cat() -> pd.DataFrame:
    """
    Get CSRC2 category data from CSV files.

    Returns:
        DataFrame with CSRC2 category data
    """
    # Use absolute path to ensure it works from any working directory
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pencsrc2 = os.path.join(base_dir, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 category data in: {pencsrc2}")
    amtdf = get_csvdf(pencsrc2, "csrccat")

    if not amtdf.empty:
        # Process amount column
        if "amount" in amtdf.columns:
            amtdf["amount"] = pd.to_numeric(amtdf["amount"], errors="coerce")
        # Rename columns law to lawlist
        if "law" in amtdf.columns:
            amtdf.rename(columns={"law": "lawlist"}, inplace=True)
        # Fill NaN values
        amtdf = amtdf.fillna("")

    return amtdf


def get_csrc2split() -> pd.DataFrame:
    """
    Get CSRC2 split data from CSV files.

    Returns:
        DataFrame with CSRC2 split data
    """
    # Use absolute path to ensure it works from any working directory
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pencsrc2 = os.path.join(base_dir, "data", "penalty", "csrc2")
    print(f"Looking for CSRC2 split data in: {pencsrc2}")
    pendf = get_csvdf(pencsrc2, "csrcsplit")

    if not pendf.empty:
        # Fill NaN values
        pendf = pendf.fillna("")

    return pendf
