# Receipt Monitor - Auto-Match Service

Automatically monitor the receipts folder and match new receipts as they arrive.

## Overview

The receipt monitor runs in the background and watches the `data/receipts/` folder. When a new PDF receipt is added:

1. ✅ **Detects** the new file instantly
2. ✅ **Extracts** date, amount, and merchant from the PDF
3. ✅ **Searches** for matching transaction in the bank statement
4. ✅ **Renames** the receipt with row number + merchant name (if matched)
5. ✅ **Updates** the CSV with match status
6. ✅ **Removes** the original receipt from source folder
7. ✅ **Leaves** unmatched receipts in folder for manual review

## Usage

### Start the Monitor

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
python monitor_receipts.py
```

### What You'll See

```
Receipt Monitor - Auto-Match Service

Monitoring: data/receipts
Statement: data/statements/Umsatzanzeige Jan 31 2026.csv
Output: output/statement_with_matches.csv

✓ Monitoring started!
Watching for new receipts... (Press Ctrl+C to stop)
```

### When a New Receipt Arrives

```
New receipt detected: Invoice_Spotify.pdf
Extracting receipt data...
✓ Receipt: Spotify AB - $9.99 on 2026-01-15
Searching for matching transaction...
✓ MATCH FOUND!
  Row: 12
  Date: 2026-01-15
  Amount: €8.68
  Merchant: Spotify AB
  Confidence: 85%
✓ Updated CSV: output/statement_with_matches.csv
✓ Renamed: 012_Spotify AB.pdf
✓ Removed original from source folder
```

### Stop the Monitor

Press **Ctrl+C** to stop monitoring:

```
^C
Stopping monitor...
✓ Monitor stopped
```

## How It Works

### 1. File Detection
- Uses `watchdog` library to monitor file system events
- Triggers when new PDF files are created in `data/receipts/`
- Waits 1 second for file to be fully written

### 2. Receipt Processing
- Extracts date, amount, merchant using PDF text extraction
- Same logic as `match_and_rename.py`

### 3. Transaction Matching
- Searches unmatched transactions in the CSV
- Matches based on:
  - **Date**: Within ±45 days
  - **Amount**: Within ±10% (EUR or USD)
  - **Merchant**: Fuzzy matching for confidence score
- Minimum confidence: 60%

### 4. Auto-Actions
If matched (≥60% confidence):
- ✅ Updates CSV with match status
- ✅ Renames receipt: `ROW_Merchant.pdf`
- ✅ Moves to `output/renamed_receipts/`
- ✅ Deletes from source folder

If not matched:
- ⚠️ Receipt stays in `data/receipts/` for manual review
- ⚠️ CSV not updated

## Configuration

Edit these variables in `monitor_receipts.py`:

```python
STATEMENT_FILE = "data/statements/Umsatzanzeige Jan 31 2026.csv"
RECEIPTS_FOLDER = "data/receipts"
OUTPUT_CSV = "output/statement_with_matches.csv"
RENAMED_RECEIPTS_FOLDER = "output/renamed_receipts"

# Matching parameters
DATE_TOLERANCE_DAYS = 45
AMOUNT_TOLERANCE = 0.10  # 10%
MIN_CONFIDENCE = 60
```

## Use Cases

### 1. Real-Time Processing
- Email receipts automatically save to `data/receipts/`
- Monitor instantly processes and matches them
- No manual intervention needed

### 2. Batch Processing
- Copy multiple receipts to folder at once
- Monitor processes each one sequentially
- Results appear immediately in CSV

### 3. Background Service
- Run monitor in background terminal
- Continue working on other tasks
- Check results periodically

## Running as Background Process

### Mac/Linux

```bash
# Start in background
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
nohup python monitor_receipts.py > monitor.log 2>&1 &

# Check if running
ps aux | grep monitor_receipts

# Stop (find PID from above, then)
kill <PID>

# View logs
tail -f monitor.log
```

### Keep Running After Terminal Closes

```bash
# Use screen or tmux
screen -S receipt-monitor
source venv/bin/activate
python monitor_receipts.py

# Detach: Ctrl+A then D
# Reattach: screen -r receipt-monitor
```

## Comparison with Manual Matching

### Manual (`match_and_rename.py`)
- ✅ Process all receipts at once
- ✅ Batch operations
- ✅ One-time run
- ✅ Good for initial setup

```bash
python match_and_rename.py
```

### Monitor (`monitor_receipts.py`)
- ✅ Real-time processing
- ✅ Automatic as receipts arrive
- ✅ Continuous monitoring
- ✅ Good for ongoing use

```bash
python monitor_receipts.py
```

**Recommendation**: Use `match_and_rename.py` first to process existing receipts, then run `monitor_receipts.py` for new ones.

## Workflow Example

### Initial Setup
```bash
# 1. Process existing receipts
python match_and_rename.py

# 2. Start monitoring for new receipts
python monitor_receipts.py
```

### Daily Use
1. Monitor runs in background
2. Download receipts from email → Save to `data/receipts/`
3. Monitor auto-processes and matches
4. Review CSV to see matches
5. Check `output/renamed_receipts/` for organized files

## Troubleshooting

### Monitor not detecting files

**Check:**
- Monitor is running (not stopped)
- Files are being added to correct folder (`data/receipts/`)
- Files are PDF format
- Files are fully written before detection (monitor waits 1 sec)

**Fix:**
```bash
# Restart monitor
^C  # Stop
python monitor_receipts.py  # Start again
```

### Files not matching

**Check console output:**
- "Could not extract date or amount" → PDF is not readable
- "No match found" → No transaction in CSV matches criteria
- Best confidence score shown → Adjust tolerances if close

**Adjust tolerances:**
```python
DATE_TOLERANCE_DAYS = 60  # Increase from 45
AMOUNT_TOLERANCE = 0.15   # Increase from 0.10
MIN_CONFIDENCE = 50       # Decrease from 60
```

### Monitor crashes

**Check logs:**
```bash
tail -f monitor.log  # If running in background
```

**Common issues:**
- File permissions (can't read/write)
- CSV file locked by Excel
- Disk full

**Fix:**
- Close Excel/Numbers if CSV is open
- Ensure write permissions on output folder
- Check disk space

## Integration Ideas

### Email Auto-Save
Configure email client to auto-save receipt attachments to `data/receipts/`:
- Gmail: Use filters + scripts
- Outlook: Use rules to save attachments
- Apple Mail: Use rules

### Dropbox/Cloud Sync
- Sync `data/receipts/` with Dropbox/iCloud
- Add receipts from phone/email to cloud folder
- Monitor processes them automatically

### Notification on Match
Add to `process_new_receipt()`:
```python
# After successful match
import subprocess
subprocess.run(['osascript', '-e', 
    'display notification "Receipt matched!" with title "Receipt Monitor"'])
```

## Files

### Input
- `data/receipts/*.pdf` - New receipts (watched folder)
- `data/statements/Umsatzanzeige Jan 31 2026.csv` - Bank statement
- `output/statement_with_matches.csv` - Existing matches (if any)

### Output
- `output/statement_with_matches.csv` - Updated with new matches
- `output/renamed_receipts/ROW_Merchant.pdf` - Renamed receipts

### Scripts
- `monitor_receipts.py` - Main monitoring script
- `src/receipt_processor.py` - PDF processing
- `src/statement_parser.py` - CSV parsing

## Performance

- **Detection**: Instant (< 1 second)
- **Processing**: 2-5 seconds per receipt
- **Matching**: 1-2 seconds
- **Total**: ~5 seconds from save to matched

**Note**: Processing time depends on PDF size and complexity.

## Security

- Monitor only reads from `data/receipts/`
- Only writes to `output/` folder
- Does not modify original bank statement
- Does not send data anywhere
- All processing is local

## See Also

- `match_and_rename.py` - Batch processing of existing receipts
- `README_MATCH_AND_RENAME.md` - Detailed matching documentation
- `README.md` - Main project documentation
