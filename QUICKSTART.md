# Quick Start Guide

## Setup (First Time Only)

### 1. Navigate to project
```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
```

### 2. Create virtual environment
```bash
python3 -m venv venv
```

### 3. Activate virtual environment
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Every time you use the app:

1. **Activate virtual environment**
   ```bash
   cd "/Users/markburnett/DevPro/Receipt Checker"
   source venv/bin/activate
   ```

2. **Place your files**
   - Bank statement → `data/statements/`
   - Receipt PDFs → `data/receipts/`

3. **Run the matcher**
   ```bash
   python main.py match data/statements/your_statement.csv data/receipts/
   ```

4. **Check results**
   - Results saved to `output/results.xlsx`
   - Open in Excel/Numbers to review

## Example Commands

### Scan receipts only (preview data)
```bash
python main.py scan data/receipts/
```

### Match with custom settings
```bash
python main.py match \
  data/statements/statement.csv \
  data/receipts/ \
  --output output/january_results.xlsx \
  --date-tolerance 5 \
  --amount-tolerance 0.02
```

### If your bank statement has different column names
```bash
python main.py match \
  data/statements/statement.csv \
  data/receipts/ \
  --date-column "Transaction Date" \
  --amount-column "Debit" \
  --description-column "Merchant"
```

## Troubleshooting

**Command not found error?**
- Make sure virtual environment is activated: `source venv/bin/activate`

**Module not found error?**
- Install dependencies: `pip install -r requirements.txt`

**No matches found?**
- Try increasing tolerances: `--date-tolerance 7 --amount-tolerance 0.05`
- Check that your statement has Date, Amount, Description columns
- Use `--date-column`, `--amount-column`, `--description-column` if needed

**PDF extraction issues?**
- Install Tesseract: `brew install tesseract` (Mac)
- Make sure PDFs contain searchable text

## Deactivate Virtual Environment

When done:
```bash
deactivate
```
