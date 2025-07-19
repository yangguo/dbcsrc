"""CSRCCAT data analysis module

This module provides functions for analyzing CSRCCAT data,
particularly for identifying records with invalid amount fields.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

def analyze_csrccat_invalid_amounts() -> Dict[str, Any]:
    """Analyze csrccat data to find records where amount field is not a valid number
    
    Returns:
        Dict containing:
        - result: List of invalid records
        - summary: Summary statistics
    """
    try:
        from data_service import get_csrc2cat
        
        # Get csrccat data
        cat_df = get_csrc2cat()
        
        if cat_df.empty:
            return {
                'result': [],
                'summary': {
                    'total': 0,
                    'invalid': 0,
                    'valid': 0,
                    'invalidPercentage': 0,
                    'nanCount': 0,
                    'zeroCount': 0,
                    'negativeCount': 0
                }
            }
        
        # Check if amount column exists
        if 'amount' not in cat_df.columns:
            raise ValueError("Amount column not found in csrccat data")
        
        # Find records with invalid amount values
        total_records = len(cat_df)
        
        # Create a copy to work with
        analysis_df = cat_df.copy()
        
        # Store original amount values before any conversion
        original_amount = analysis_df['amount'].copy()
        
        # Check for invalid amounts (NaN, null, non-numeric, negative)
        # Note: Zero values are now considered valid
        
        # First, identify non-numeric values by trying to convert to numeric
        numeric_amount = pd.to_numeric(analysis_df['amount'], errors='coerce')
        
        # Invalid mask includes:
        # 1. Originally NaN/null values
        # 2. Non-numeric strings (became NaN after conversion but weren't originally NaN)
        # 3. Negative values
        invalid_mask = (
            analysis_df['amount'].isna() |  # Originally NaN/null
            (original_amount.notna() & numeric_amount.isna()) |  # Non-numeric strings
            (numeric_amount < 0)  # Negative values
        )
        
        invalid_records = analysis_df[invalid_mask]
        valid_records = analysis_df[~invalid_mask]
        
        # Convert invalid records to list of dictionaries
        result_data = []
        for index, row in invalid_records.iterrows():
            item = {
                'id': row.get('id', str(index)),
                'url': row.get('链接', row.get('url', '')),
                'title': row.get('案例标题', row.get('title', '')),
                'date': row.get('发文日期', row.get('date', '')),
                'org': row.get('机构', row.get('org', '')),
                'amount': row.get('amount', None),
                'amountStatus': (
                    'NaN' if pd.isna(row.get('amount')) else
                    'NonNumeric' if pd.notna(row.get('amount')) and pd.isna(pd.to_numeric(row.get('amount'), errors='coerce')) else
                    'Negative'
                ),
                'category': row.get('category', ''),
                'province': row.get('province', ''),
                'industry': row.get('industry', ''),
                'lawlist': row.get('lawlist', row.get('law', ''))
            }
            result_data.append(item)
        
        # Create summary statistics
        numeric_amount = pd.to_numeric(analysis_df['amount'], errors='coerce')
        
        summary = {
            'total': total_records,
            'invalid': len(invalid_records),
            'valid': len(valid_records),
            'invalidPercentage': round((len(invalid_records) / total_records * 100), 2) if total_records > 0 else 0,
            'nanCount': len(analysis_df[analysis_df['amount'].isna()]),
            'nonNumericCount': len(analysis_df[(analysis_df['amount'].notna()) & (numeric_amount.isna())]),
            'zeroCount': len(analysis_df[numeric_amount == 0]),
            'negativeCount': len(analysis_df[numeric_amount < 0])
        }
        
        logger.info(f"Found {len(invalid_records)} invalid amount records out of {total_records} total records")
        
        return {
            'result': result_data,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze csrccat invalid amounts: {str(e)}", exc_info=True)
        raise e

def get_csrccat_statistics() -> Dict[str, Any]:
    """Get basic statistics about csrccat data
    
    Returns:
        Dict containing basic statistics about the dataset
    """
    try:
        from data_service import get_csrc2cat
        
        cat_df = get_csrc2cat()
        
        if cat_df.empty:
            return {
                'total_records': 0,
                'columns': [],
                'amount_stats': {}
            }
        
        stats = {
            'total_records': len(cat_df),
            'columns': list(cat_df.columns),
        }
        
        # Add amount column statistics if it exists
        if 'amount' in cat_df.columns:
            amount_series = cat_df['amount']
            stats['amount_stats'] = {
                'count': len(amount_series),
                'non_null_count': amount_series.count(),
                'null_count': amount_series.isna().sum(),
                'mean': float(amount_series.mean()) if amount_series.count() > 0 else 0,
                'median': float(amount_series.median()) if amount_series.count() > 0 else 0,
                'min': float(amount_series.min()) if amount_series.count() > 0 else 0,
                'max': float(amount_series.max()) if amount_series.count() > 0 else 0,
                'zero_count': (amount_series == 0).sum(),
                'negative_count': (amount_series < 0).sum(),
                'positive_count': (amount_series > 0).sum()
            }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get csrccat statistics: {str(e)}", exc_info=True)
        raise e