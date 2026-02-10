# How to Use Receipt Checker

## ✅ Installation Complete!

Your Receipt Checker is ready to use. Here's how to run it:

---

## 🚀 Quick Start

### 1. Open Terminal and Navigate to Project

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` appear in your terminal prompt.

### 3. Prepare Your Files

**Bank Statement:**
- Place your bank statement CSV or Excel file in `data/statements/`
- It should have columns for: Date, Amount, Description (or similar names)

**Receipts:**
- Your receipts are already in `data/receipts/Bank/` (34 PDFs found!)
- You also have credit card receipts in `data/receipts/CCard/`

---

## 📋 Available Commands

### Scan Receipts (Preview Data)

See what data can be extracted from your receipts:

```bash
python main.py scan data/receipts/Bank/
```

This shows:
- All PDF files found
- Extracted date, amount, merchant from each receipt
- No matching yet, just a preview

### Match Transactions with Receipts

Match your bank statement with receipts:

```bash
python main.py match \
  data/statements/YOUR_STATEMENT.csv \
  data/receipts/Bank/ \
  --output output/results.xlsx
```

**Replace `YOUR_STATEMENT.csv`** with your actual bank statement filename.

### Custom Column Names

If your bank statement has different column names:

```bash
python main.py match \
  data/statements/YOUR_STATEMENT.csv \
  data/receipts/Bank/ \
  --date-column "Transaction Date" \
  --amount-column "Debit" \
  --description-column "Merchant Name"
```

### Adjust Matching Tolerances

If you're not getting enough matches:

```bash
python main.py match \
  data/statements/YOUR_STATEMENT.csv \
  data/receipts/Bank/ \
  --date-tolerance 7 \
  --amount-tolerance 0.05
```

- `--date-tolerance 7` = Allow 7 days difference (default: 3)
- `--amount-tolerance 0.05` = Allow 5% amount difference (default: 1%)

---

## 📊 What You Have

### Your Receipts Found:

**Bank Account Receipts:** `data/receipts/Bank/`
- 34 PDF receipts
- Including: Google, Beatport, Stage2go, ILG invoices, Spotify, PayPal, etc.

**Credit Card Receipts:** `data/receipts/CCard/`
- Airtable, Midjourney, HeyGen, OpenAI invoices

### Your Statements:

**Found in:** `data/statements/`
- `Checklist December cc.gsheet`
- `Umsatzanzeige GLS Gemeinschaftsbank` (PDF and CSV)

---

## 💡 Example Workflow

### Step 1: Check your receipts
```bash
python main.py scan data/receipts/Bank/
```

### Step 2: Export bank statement to CSV
- Open your bank account online
- Download transactions as CSV
- Save to `data/statements/january_2025.csv`

### Step 3: Match!
```bash
python main.py match \
  data/statements/january_2025.csv \
  data/receipts/Bank/ \
  --output output/january_results.xlsx
```

### Step 4: Review Results
- Open `output/january_results.xlsx`
- Check matched transactions (marked with receipt filename)
- Review unmatched transactions

---

## 📈 Understanding Results

The app will show you:

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

- **Matched**: Transactions successfully matched to receipts
- **Unmatched**: Transactions without receipts
- **Match Rate**: Percentage of transactions matched
- **Avg Confidence**: How confident the matches are (0-100)

---

## 🔧 Troubleshooting

### "Command not found"
```bash
# Make sure virtual environment is activated
source venv/bin/activate
```

### "Module not found"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### "File not found"
```bash
# Check the file path is correct
ls data/statements/
ls data/receipts/Bank/
```

### Low Match Rate
- Increase date tolerance: `--date-tolerance 7`
- Increase amount tolerance: `--amount-tolerance 0.05`
- Check your column names match
- Verify receipts have readable text (not scanned images)

---

## 🎯 Next Steps

1. **Export your bank statement** to CSV
2. **Place it in** `data/statements/`
3. **Run the matcher** with your statement
4. **Review results** in Excel

---

## 💾 When You're Done

To exit the virtual environment:

```bash
deactivate
```

To reactivate later:

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
```

---

## 📞 Your Current Setup

- ✅ Virtual environment created
- ✅ All dependencies installed
- ✅ 34 bank receipts found in `data/receipts/Bank/`
- ✅ Credit card receipts in `data/receipts/CCard/`
- ✅ Sample statement created for testing
- ✅ App tested and working

**Ready to match your receipts!** 🎉
