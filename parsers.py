import pandas as pd
import pdfplumber
import io
import re
from typing import List
from models import Transaction

def parse_csv(content: bytes) -> List[Transaction]:
    """
    Parse a CSV file of transactions. 
    Handles columns: Date, Time, Money In, Money out, Amount, Currency, Category, Name, Description, Balance
    """
    df = pd.read_csv(io.BytesIO(content))
    
    # Clean up column names by making them lower case
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    transactions = []
    for _, row in df.iterrows():
        # Date
        raw_date = row.get('date')
        if pd.notna(raw_date) and str(raw_date).strip() != '' and str(raw_date).lower() != 'nan':
            try:
                parsed_date = pd.to_datetime(str(raw_date).strip())
                date_val = parsed_date.strftime('%Y-%m-%d')
            except Exception:
                date_val = str(raw_date).strip()
        else:
            date_val = 'Unknown Date'
            
        # Description
        name_val = str(row.get('name', '')).strip()
        desc_raw = str(row.get('description', '')).strip()
        
        if name_val and desc_raw and name_val != 'nan' and desc_raw != 'nan':
            desc_val = f"{name_val} - {desc_raw}"
        elif name_val and name_val != 'nan':
            desc_val = name_val
        elif desc_raw and desc_raw != 'nan':
            desc_val = desc_raw
        else:
            desc_val = 'Unknown Description'
            
        # Handle amount robustly
        amount_val = 0.0
        
        raw_amt = row.get('amount')
        money_in = row.get('money in')
        money_out = row.get('money out')
        
        # aggressively strip everything that is not a digit, minus, or period
        def clean_amount(val) -> float:
            val_str = str(val).strip()
            # If the value is 'nan' or empty, return 0.0
            if val_str.lower() == 'nan' or not val_str:
                return 0.0
            
            # Remove any unwanted characters (commas, currency symbols, generic text)
            cleaned_str = re.sub(r'[^\d.-]', '', val_str)
            if not cleaned_str or cleaned_str == '-' or cleaned_str == '.':
                return 0.0
                
            return float(cleaned_str)
        
        if pd.notna(raw_amt) and str(raw_amt).strip() != '' and str(raw_amt).lower() != 'nan':
            amount_val = clean_amount(raw_amt)
            if pd.notna(money_out) and str(money_out).strip() != '' and str(money_out).lower() != 'nan':
                 amount_val = -abs(amount_val)
                 
        elif pd.notna(money_in) and str(money_in).strip() != '' and str(money_in).lower() != 'nan':
            amount_val = clean_amount(money_in)
            
        elif pd.notna(money_out) and str(money_out).strip() != '' and str(money_out).lower() != 'nan':
            amount_val = -abs(clean_amount(money_out))
            
        category_val = str(row.get('category', 'Uncategorized'))
        if category_val == 'nan' or not category_val.strip():
            category_val = 'Uncategorized'
        
        tx = Transaction(
            date=date_val,
            description=desc_val,
            amount=amount_val,
            category=category_val
        )
        transactions.append(tx)
        
    return transactions

def parse_pdf(content: bytes) -> List[Transaction]:
    """
    Very naive PDF parser using pdfplumber.
    This attempts to extract tables from the document 
    assuming columns: Date, Description, Amount, Category
    """
    transactions = []
    
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                
                # Assume first row is header
                header = [str(h).lower().strip() if h else '' for h in table[0]]
                
                # Basic mapping index check
                try:
                    date_idx = header.index('date')
                    desc_idx = header.index('description')
                    amt_idx = header.index('amount')
                    
                    # Category might be missing
                    cat_idx = header.index('category') if 'category' in header else -1
                except ValueError:
                    # Table didn't have expected headers, skip
                    continue
                
                for row in table[1:]:
                    if not row or not row[date_idx]:
                        continue # Skip empty rows
                        
                    date_val = str(row[date_idx])
                    desc_val = str(row[desc_idx])
                    
                    raw_amt = row[amt_idx]
                    try:
                        if isinstance(raw_amt, str):
                           raw_amt = raw_amt.replace(',', '').replace('$', '').strip()
                        amount_val = float(raw_amt)
                    except (ValueError, TypeError):
                        amount_val = 0.0
                        
                    category_val = str(row[cat_idx]) if cat_idx != -1 and row[cat_idx] else "Uncategorized"
                    
                    tx = Transaction(
                        date=date_val,
                        description=desc_val,
                        amount=amount_val,
                        category=category_val
                    )
                    transactions.append(tx)
                    
    return transactions
