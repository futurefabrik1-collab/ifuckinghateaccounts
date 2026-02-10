# Receipt Checker

An intelligent application to match bank statement entries with receipt PDFs automatically.

## Overview

Receipt Checker processes your bank statement spreadsheet (CSV or Excel) and matches transactions with PDF receipts in a folder based on:
- Transaction date (±3 days tolerance)
- Transaction amount (±1% tolerance)
- Merchant/vendor name (fuzzy matching)

## Features

✅ **Smart Matching**
- Fuzzy matching for merchant names
- Configurable date and amount tolerances
- Confidence scoring for each match

✅ **Multiple Formats**
- Supports CSV and Excel bank statements
- Processes PDF receipts
- OCR text extraction from receipts

✅ **Rich Reporting**
- Color-coded CLI interface
- Match statistics and confidence scores
- Export results to Excel/CSV
- List unmatched transactions

✅ **Flexible Configuration**
- Custom column names for bank statements
- Adjustable matching tolerances
- Date range filtering

## Installation

### 1. Create Virtual Environment

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Tesseract (Optional - for OCR)

```bash
# Mac
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

### Quick Start

```bash
python main.py match statement.csv receipts/ --output output/results.xlsx
```

### Scan Receipts Only

Preview what data can be extracted from your receipts:

```bash
python main.py scan receipts/
```

### Full Match Command

```bash
python main.py match \
  path/to/statement.csv \
  path/to/receipts/ \
  --output results.xlsx \
  --date-column "Transaction Date" \
  --amount-column "Amount" \
  --description-column "Description" \
  --date-tolerance 3 \
  --amount-tolerance 0.01
```

### Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `output/results.xlsx` | Output file path |
| `--date-column` | `Date` | Column name for transaction date |
| `--amount-column` | `Amount` | Column name for amount |
| `--description-column` | `Description` | Column name for merchant/description |
| `--date-tolerance` | `3` | Days tolerance for date matching |
| `--amount-tolerance` | `0.01` | Percentage tolerance for amount (0.01 = 1%) |

## Project Structure

```
Receipt Checker/
├── README.md
├── requirements.txt
├── setup.py
├── main.py                 # CLI interface
├── src/
│   ├── __init__.py
│   ├── statement_parser.py    # Parse bank statements
│   ├── receipt_processor.py   # Extract data from PDFs
│   └── matcher.py             # Match transactions with receipts
├── data/
│   ├── statements/            # Place bank statements here
│   └── receipts/              # Place receipt PDFs here
├── output/                    # Results will be saved here
└── tests/                     # Unit tests
```

## How It Works

### 1. Statement Processing
- Loads CSV or Excel bank statement
- Standardizes column names
- Converts dates and amounts to proper formats

### 2. Receipt Processing
- Scans folder for PDF files
- Extracts text from each PDF
- Identifies:
  - Transaction date
  - Total amount
  - Merchant name

### 3. Matching Algorithm
- Compares each transaction with all receipts
- Scores matches based on:
  - Date proximity (within tolerance)
  - Amount accuracy (within tolerance)
  - Merchant name similarity (fuzzy matching)
- Selects best match with highest confidence
- Marks transactions as matched/unmatched

### 4. Output
- Creates Excel/CSV with match results
- Adds columns:
  - `matched` (True/False)
  - `matched_receipt` (filename of matched receipt)
- Displays summary statistics

## Bank Statement Format

Your bank statement should have these columns (names can be customized):

| Date | Amount | Description |
|------|--------|-------------|
| 2024-01-15 | -45.99 | WALMART SUPERCENTER |
| 2024-01-16 | -12.50 | STARBUCKS #12345 |
| 2024-01-17 | -89.00 | AMAZON.COM |

Supported formats:
- CSV (.csv)
- Excel (.xlsx, .xls)

## Receipt PDF Requirements

- Must be in PDF format
- Should contain readable text (not scanned images without OCR)
- Common receipt formats are supported

## Example Output

```
Matching Results

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Transactions │ 50    │
│ Matched            │ 42    │
│ Unmatched          │ 8     │
│ Match Rate         │ 84.0% │
│ Avg Confidence     │ 87.3  │
└────────────────────┴───────┘
```

## Troubleshooting

### No matches found
- Check that dates and amounts are in correct formats
- Increase date tolerance: `--date-tolerance 7`
- Increase amount tolerance: `--amount-tolerance 0.05`

### Wrong column names
- Specify correct columns:
  ```bash
  --date-column "Posted Date" \
  --amount-column "Debit" \
  --description-column "Memo"
  ```

### PDF extraction issues
- Ensure PDFs contain searchable text
- Install Tesseract for OCR support
- Check that receipt PDFs aren't corrupted

## Advanced Usage

### Python API

```python
from src.statement_parser import StatementParser
from src.receipt_processor import ReceiptProcessor
from src.matcher import ReceiptMatcher

# Parse statement
parser = StatementParser('statement.csv')
df = parser.load_statement()

# Process receipts
processor = ReceiptProcessor('receipts/')
receipts = processor.process_all_receipts()

# Match
matcher = ReceiptMatcher()
transactions = parser.get_transactions()
results = matcher.match_all_transactions(transactions, receipts)

# Generate report
report = matcher.generate_report(results)
print(report)
```

## Future Enhancements

- [ ] Web interface
- [ ] Drag-and-drop file upload
- [ ] Machine learning for better matching
- [ ] Support for more bank formats
- [ ] Automatic categorization
- [ ] Export to accounting software

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
