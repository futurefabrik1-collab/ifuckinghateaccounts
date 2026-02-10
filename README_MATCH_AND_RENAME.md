# Match and Rename - Bank Statement Receipt Matcher

Automatically match receipts to bank statement transactions and rename receipt files with row numbers and merchant names.

## Overview

This script:
1. Loads a GLS bank statement CSV
2. Scans a folder of PDF receipts (unsorted, unnumbered)
3. Matches receipts to transactions based on date, amount, and merchant
4. Adds columns to the CSV indicating which receipts match
5. Renames receipt files with format: `ROW_MerchantName.pdf`

## Usage

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
python match_and_rename.py
```

## Configuration

Edit these variables at the top of `match_and_rename.py`:

```python
STATEMENT_FILE = "data/statements/Umsatzanzeige Jan 31 2026.csv"
RECEIPTS_FOLDER = "data/receipts"
OUTPUT_CSV = "output/statement_with_matches.csv"
RENAMED_RECEIPTS_FOLDER = "output/renamed_receipts"
```

## Input Requirements

### Bank Statement CSV
- **Format**: GLS Gemeinschaftsbank format (semicolon-delimited)
- **Required columns**:
  - `Buchungstag` - Transaction date (DD.MM.YYYY)
  - `Betrag` - Amount in EUR (e.g., "-10,50")
  - `Verwendungszweck` - Transaction description

### Receipts Folder
- **Format**: PDF files
- **Naming**: Any naming convention (will be renamed)
- **Sorting**: Not required (can be unsorted/mixed)
- **Relevance**: May contain receipts not related to this statement

## Output

### 1. Updated CSV File
**Location**: `output/statement_with_matches.csv`

**New columns added**:
- `Matching Receipt Found` - True/False indicating if receipt was matched
- `Matched Receipt File` - Original filename of matched receipt
- `Match Confidence` - Score 0-100 indicating match quality

**Example**:
| Buchungstag | Betrag | Verwendungszweck | Matching Receipt Found | Matched Receipt File | Match Confidence |
|-------------|--------|------------------|------------------------|---------------------|------------------|
| 28.01.2026 | -9,62 | Bambulab GmbH... | True | Receipt (1).pdf | 72 |
| 27.01.2026 | -5,00 | Monthly fee | False | | 0 |

### 2. Renamed Receipt Files
**Location**: `output/renamed_receipts/`

**Naming format**: `ROW_MerchantName.pdf`

**Examples**:
- `005_Midjourney Inc.pdf` - Row 5 transaction
- `020_Suno.pdf` - Row 20 transaction
- `028_HeyGen Technology Inc.pdf` - Row 28 transaction

**Row numbering**: 
- Row numbers match the CSV file (including header)
- Row 1 = header
- Row 2 = first transaction
- etc.

## Matching Algorithm

### 1. Date Matching
- **Tolerance**: ±45 days
- **Rationale**: Allows for processing delays, billing cycles

### 2. Amount Matching
- **Tolerance**: ±10% of amount
- **Currency**: Handles both EUR and USD amounts
- **USD Extraction**: Extracts USD from "Verwendungszweck" for foreign transactions

### 3. Merchant Matching
- **Method**: Fuzzy string matching
- **Source**: Uses merchant name from **receipt**, not CSV
- **Contribution**: Adds to confidence score

### 4. Confidence Scoring
- **Base score**: 60 points (date + amount match)
- **Merchant similarity**: +0-40 points (fuzzy match)
- **Date proximity bonus**:
  - ≤3 days: +10 points
  - ≤7 days: +5 points
- **Total**: 60-100 points

### 5. Match Requirements
- Minimum confidence: 60
- Each receipt matched to only one transaction
- Best match selected when multiple candidates exist

## Merchant Name Extraction

Merchant names are extracted from **receipts**, not CSV transactions.

**Why?** 
- CSV shows payment processors (e.g., "Bambulab GmbH", "Cleverbridge GmbH")
- Receipts show actual merchants (e.g., "Midjourney Inc", "Suno")

**Extraction logic**:
1. Skip common headers: "Receipt", "Invoice", "Bill"
2. Look for company identifiers: Inc, LLC, GmbH, Ltd, Corp
3. Extract text before "Bill to"
4. Take first substantial line (>5 chars)
5. Clean special characters for filename

**Examples**:
- PDF line: "Midjourney Inc Bill to" → Merchant: "Midjourney Inc"
- PDF line: "Suno Bill to" → Merchant: "Suno"
- PDF line: "HeyGen Technology Inc" → Merchant: "HeyGen Technology Inc"

## Results Example

```
Matching Results
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Transactions │ 54    │
│ Matched            │ 5     │
│ Unmatched          │ 49    │
│ Match Rate         │ 9.3%  │
│ Receipts Used      │ 5/19  │
└────────────────────┴───────┘

Matched Transactions (5)
┏━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Row ┃ Date       ┃ Amount   ┃ Merchant          ┃ Receipt        ┃ Conf% ┃
┡━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 5   │ 2026-01-28 │ €-9.62   │ Midjourney Inc    │ Receipt (1)... │ 72    │
│ 20  │ 2026-01-21 │ €-37.74  │ Suno              │ Receipt 2193.. │ 70    │
│ 28  │ 2026-01-16 │ €-83.30  │ HeyGen Technology │ Receipt.pdf    │ 77    │
└─────┴────────────┴──────────┴───────────────────┴────────────────┴───────┘
```

## Adjusting Match Tolerances

Edit these values in `match_and_rename.py`:

### Date Tolerance
```python
# Line ~140
if date_diff > 45:  # Change this number (days)
    continue
```

### Amount Tolerance
```python
# Line ~151, ~157
if abs(usd_amount - receipt['amount']) / max(abs(usd_amount), receipt['amount']) < 0.10:  # Change 0.10 (10%)
```

### Minimum Confidence
```python
# Line ~183
if best_match and best_score >= 60:  # Change this threshold (0-100)
```

## Troubleshooting

### Low match rate
**Expected** - receipts may not be relevant to this statement period

**To increase matches**:
- Increase date tolerance to 60+ days
- Increase amount tolerance to 0.15 (15%)
- Lower minimum confidence to 50

### Wrong merchant names in filenames
Check the receipt PDF - the script extracts from the receipt, not the CSV.

**Common issues**:
- Receipt header is "Invoice" → Will skip and find next line
- Multiple merchants on receipt → Takes first one found
- No company identifier (Inc, LLC, etc.) → Takes first substantial line

### Files not being renamed
Check console output for errors during file copying.

**Common issues**:
- File permissions (receipts are read-only)
- Special characters in filenames
- Receipt file moved/deleted

### Receipts matched incorrectly
**Review**:
- Match confidence score (lower = less certain)
- Date difference between transaction and receipt
- Amount comparison

**Adjust**:
- Tighten date tolerance
- Reduce amount tolerance
- Increase minimum confidence threshold

## Files

### Input
- `data/statements/Umsatzanzeige Jan 31 2026.csv` - Bank statement
- `data/receipts/*.pdf` - Receipt PDFs (unsorted)

### Output
- `output/statement_with_matches.csv` - CSV with match columns
- `output/renamed_receipts/ROW_Merchant.pdf` - Renamed receipts

### Scripts
- `match_and_rename.py` - Main script
- `src/receipt_processor.py` - PDF processing and merchant extraction
- `src/statement_parser.py` - CSV parsing

## Advanced Usage

### Process Multiple Statements

Create a loop script:

```python
statements = [
    "Umsatzanzeige Jan 31 2026.csv",
    "Umsatzanzeige Feb 28 2026.csv",
]

for statement in statements:
    # Update STATEMENT_FILE and run matching
    ...
```

### Custom Merchant Extraction

Edit `src/receipt_processor.py` - `extract_merchant()` function

### Export to Accounting Software

The CSV can be imported into:
- Excel / Google Sheets
- Accounting software (QuickBooks, Xero, etc.)
- Custom scripts for further processing

## See Also

- `run_credit_card_matcher.py` - Specialized credit card matcher
- `main.py` - General receipt matching CLI
- `README.md` - Main project documentation
