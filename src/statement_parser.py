"""Parse bank statement spreadsheets (CSV/Excel)"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class StatementParser:
    """Parse and process bank statement files"""
    
    def __init__(self, file_path: str):
        """
        Initialize the statement parser
        
        Args:
            file_path: Path to the bank statement file (CSV or Excel)
        """
        self.file_path = Path(file_path)
        self.df = None
        
    def load_statement(self, 
                      date_column: str = 'Date',
                      amount_column: str = 'Amount', 
                      description_column: str = 'Description') -> pd.DataFrame:
        """
        Load bank statement from file
        
        Args:
            date_column: Name of the date column
            amount_column: Name of the amount column
            description_column: Name of the description/merchant column
            
        Returns:
            DataFrame with standardized columns
        """
        # Detect file type and load
        if self.file_path.suffix.lower() == '.csv':
            # Try to detect delimiter automatically
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()
                # Count delimiters in first line
                if first_line.count(';') > first_line.count(','):
                    delimiter = ';'
                elif first_line.count(',') > first_line.count(';'):
                    delimiter = ','
                elif first_line.count('\t') > 0:
                    delimiter = '\t'
                else:
                    delimiter = ','
            
            self.df = pd.read_csv(self.file_path, sep=delimiter, encoding='utf-8-sig')
        elif self.file_path.suffix.lower() in ['.xlsx', '.xls']:
            self.df = pd.read_excel(self.file_path)
        else:
            raise ValueError(f"Unsupported file format: {self.file_path.suffix}")
        
        # Check if specified columns exist
        missing_cols = []
        if date_column not in self.df.columns:
            missing_cols.append(f"Date column '{date_column}' not found")
        if amount_column not in self.df.columns:
            missing_cols.append(f"Amount column '{amount_column}' not found")
        if description_column not in self.df.columns:
            missing_cols.append(f"Description column '{description_column}' not found")
        
        if missing_cols:
            available = ', '.join(self.df.columns.tolist())
            raise ValueError(f"{'; '.join(missing_cols)}. Available columns: {available}")
        
        # Standardize column names
        column_mapping = {
            date_column: 'date',
            amount_column: 'amount',
            description_column: 'description'
        }
        
        self.df = self.df.rename(columns=column_mapping)
        
        # Convert date to datetime (handle German format)
        self.df['date'] = pd.to_datetime(self.df['date'], format='%d.%m.%Y', errors='coerce')
        if self.df['date'].isna().all():
            # Try other common formats
            self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
        
        # Convert amount to float (handle negative signs, currency symbols, German format)
        self.df['amount'] = self.df['amount'].astype(str).str.replace('$', '').str.replace('€', '').str.replace('.', '').str.replace(',', '.')
        self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce')
        
        # Add match status column
        self.df['matched'] = False
        self.df['matched_receipt'] = None
        
        return self.df
    
    def get_transactions(self) -> List[Dict]:
        """
        Get list of transactions as dictionaries
        
        Returns:
            List of transaction dictionaries
        """
        if self.df is None:
            raise ValueError("No statement loaded. Call load_statement() first.")
        
        return self.df.to_dict('records')
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Filter transactions by date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Filtered DataFrame
        """
        mask = (self.df['date'] >= start_date) & (self.df['date'] <= end_date)
        return self.df[mask]
    
    def get_unmatched_transactions(self) -> pd.DataFrame:
        """Get transactions that haven't been matched to receipts"""
        return self.df[~self.df['matched']]
    
    def mark_as_matched(self, index: int, receipt_name: str):
        """
        Mark a transaction as matched
        
        Args:
            index: DataFrame index of the transaction
            receipt_name: Name of the matched receipt file
        """
        self.df.loc[index, 'matched'] = True
        self.df.loc[index, 'matched_receipt'] = receipt_name
    
    def export_results(self, output_path: str):
        """
        Export results to file
        
        Args:
            output_path: Path for output file (CSV or Excel)
        """
        output_path = Path(output_path)
        
        if output_path.suffix.lower() == '.csv':
            self.df.to_csv(output_path, index=False)
        elif output_path.suffix.lower() in ['.xlsx', '.xls']:
            self.df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")
