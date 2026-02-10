# Credit Card Receipt Matcher

Custom matcher for GLS Gemeinschaftsbank credit card statements.

## Overview

This script specifically handles GLS Bank credit card statements that contain USD-to-EUR conversions. It:
- Extracts USD amounts from the transaction description
- Matches both USD and EUR receipts
- Handles date matching with 30-day tolerance
- Exports results to Excel

## Usage

### Run the Credit Card Matcher

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
python run_credit_card_matcher.py
```

### What It Does

1. **Loads Statement**: `data/statements/Umsatzanzeige GLS Gemeinschaftsbank Dez 31 2025.csv`
2. **Scans Receipts**: All PDFs in `data/receipts/CCard/`
3. **Extracts USD Amounts**: From the "Verwendungszweck" field (e.g., "USD 72,00")
4. **Matches Transactions**:
   - Prefers USD amount matches
   - Falls back to EUR amount for EUR transactions
   - Matches dates within 30 days
   - Uses fuzzy merchant name matching
5. **Exports to Excel**: `output/credit_card_matches.xlsx`

## Results

The script outputs:
- **Console Summary**: Match statistics and lists
- **Excel File**: Complete results with:
  - Date
  - EUR Amount
  - USD Amount (if applicable)
  - Merchant
  - Matched Receipt File
  - Receipt Amount
  - Confidence Score
  - Match Status (Matched/Unmatched)

## Example Output

```
Results
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Transactions │ 7     │
│ Matched            │ 6     │
│ Unmatched          │ 1     │
│ Match Rate         │ 85.7% │
└────────────────────┴───────┘
```

## How It Works

### 1. USD Amount Extraction

For transactions like:
```
AIRTABLE.COM/BILL USA SAN FRANCISCO USD 72,00 KURS: 1,176086...
```

Extracts: `$72.00`

### 2. Matching Logic

- **Date Match**: Within 30 days tolerance
- **Amount Match**: 
  - If USD amount exists: Match against receipt USD amount (5% tolerance)
  - If no USD: Match EUR amount against receipt amount (5% tolerance)
- **Merchant Match**: Fuzzy matching (contributes to confidence score)

### 3. Confidence Scoring

- 70 points: Date + Amount match
- +30 points: Merchant name similarity (0-30%)
- Final score: 70-100%

## File Formats

### Input: GLS Bank CSV

Required columns:
- `Buchungstag` - Transaction date (DD.MM.YYYY)
- `Betrag` - EUR amount (with comma as decimal)
- `Verwendungszweck` - Description (contains USD amounts)

### Output: Excel

Columns:
- Date (YYYY-MM-DD)
- EUR Amount
- USD Amount
- Merchant
- Receipt File
- Receipt Amount
- Confidence %
- Status

## Troubleshooting

### No matches found

**Check:**
- Receipts are in `data/receipts/CCard/`
- Receipt dates are within 30 days of transaction dates
- Amounts match within 5% tolerance

### Wrong matches

**Adjust:**
- Date tolerance (currently 30 days)
- Amount tolerance (currently 5%)
- Merchant threshold (currently 60)

Edit these values in `run_credit_card_matcher.py`:
```python
date_diff = abs((transaction_date - receipt['date']).days)
if date_diff > 30:  # Change this value
    continue

# Amount tolerance
if abs(usd_amount - receipt['amount']) / max(usd_amount, receipt['amount']) < 0.05:  # Change 0.05
```

## Files

- **Input Statement**: `data/statements/Umsatzanzeige GLS Gemeinschaftsbank Dez 31 2025.csv`
- **Input Receipts**: `data/receipts/CCard/*.pdf`
- **Output Excel**: `output/credit_card_matches.xlsx`
- **Script**: `run_credit_card_matcher.py`

## Related

See also:
- `main.py` - General receipt matcher (for other bank formats)
- `HOW_TO_USE.md` - General usage guide
- `README.md` - Main project documentation
