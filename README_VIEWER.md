# Progress Viewer - Receipt Matching Status

View your receipt matching progress in a clean, simplified table.

## Overview

The progress viewer displays your bank statement transactions with their match status in an easy-to-read format showing:
- Row number
- Date
- Amount
- Merchant/Description
- Matched status (✓ Yes / ✗ No)
- Receipt filename (if matched)

## Usage

### View All Transactions

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
python view_progress.py
```

### View Only Matched Transactions

```bash
python view_progress.py --matched
```

### View Only Unmatched Transactions

```bash
python view_progress.py --unmatched
```

## Output

### Summary Statistics

```
╭─────────────── Summary ───────────────╮
│ Total Transactions │ 54    │
│ Matched            │ 5     │
│ Unmatched          │ 49    │
│ Match Rate         │ 9.3%  │
└────────────────────┴───────┘
```

### Transaction Table

```
All Transactions
┏━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Row ┃ Date       ┃ Amount   ┃ Merchant       ┃ Matched ┃ Receipt       ┃
┡━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ 5   │ 28.01.2026 │ €-9,62   │ Google         │ ✓ Yes   │ Receipt.pdf   │
│ 20  │ 21.01.2026 │ €-37,74  │ Wolt           │ ✓ Yes   │ Receipt.pdf   │
│ 27  │ 15.01.2026 │ €-142,80 │ elbgoods       │ ✓ Yes   │ EL-15520.pdf  │
│ 28  │ 16.01.2026 │ €-83,30  │ Stage2go       │ ✓ Yes   │ Receipt.pdf   │
│ 45  │ 03.01.2026 │ €-10,08  │ STRATO GmbH    │ ✓ Yes   │ Receipt.pdf   │
│ 6   │ 27.01.2026 │ €-9,62   │ Bambulab GmbH  │ ✗ No    │ -             │
│ ... │ ...        │ ...      │ ...            │ ...     │ ...           │
└─────┴────────────┴──────────┴────────────────┴─────────┴───────────────┘
```

## Display Options

| Option | Command | Description |
|--------|---------|-------------|
| All | `python view_progress.py` | Shows all transactions |
| Matched only | `python view_progress.py --matched` | Shows only matched transactions |
| Unmatched only | `python view_progress.py --unmatched` | Shows only unmatched transactions |

## Column Descriptions

### Row
- CSV row number (includes header, so row 2 = first transaction)
- Corresponds to renamed receipt filenames (e.g., `005_Merchant.pdf`)

### Date
- Transaction date from bank statement
- Format: DD.MM.YYYY

### Amount
- Transaction amount in EUR
- Negative = debit, Positive = credit

### Merchant/Description
- Transaction description from CSV
- Truncated to 50 characters for readability
- Full text available in CSV

### Matched
- ✓ Yes (green) = Receipt matched
- ✗ No (red) = No receipt found

### Receipt
- Filename of matched receipt
- "-" if no match
- Truncated to 30 characters

## Use Cases

### Check Overall Progress
```bash
python view_progress.py
```
See summary stats and all transactions at a glance.

### Find Unmatched Transactions
```bash
python view_progress.py --unmatched
```
Identify which transactions still need receipts.

### Verify Matched Receipts
```bash
python view_progress.py --matched
```
Review successfully matched transactions.

### Quick Status Check
Run anytime to see current matching status without opening CSV in Excel.

## Data Source

The viewer loads data from:
1. **First choice**: `output/statement_with_matches.csv` (if exists)
2. **Fallback**: `data/statements/Umsatzanzeige Jan 31 2026.csv` (original)

If loading original statement, match columns are initialized to False.

## Integration with Other Tools

### After Running Matcher
```bash
# 1. Run matcher
python match_and_rename.py

# 2. View results
python view_progress.py
```

### While Monitor is Running
```bash
# Terminal 1: Run monitor
python monitor_receipts.py

# Terminal 2: Check progress anytime
python view_progress.py
```

### Before/After Comparison
```bash
# Before
python view_progress.py --unmatched > before.txt

# Run matcher
python match_and_rename.py

# After
python view_progress.py --unmatched > after.txt

# Compare
diff before.txt after.txt
```

## Refresh Data

The viewer reads the current CSV file each time. To see updated results:
1. Run the viewer again (no need to restart)
2. Data is loaded fresh on every execution

## Export Options

### Save to Text File
```bash
python view_progress.py > progress.txt
python view_progress.py --matched > matched.txt
python view_progress.py --unmatched > unmatched.txt
```

### Copy to Clipboard (Mac)
```bash
python view_progress.py | pbcopy
```

## Performance

- **Load time**: < 1 second
- **Display**: Instant
- **Memory**: Minimal (loads only necessary columns)

## Troubleshooting

### No data showing
**Check:**
- CSV file exists
- CSV is not corrupted
- Run from correct directory

**Fix:**
```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
ls output/statement_with_matches.csv  # Should exist
```

### Wrong data displayed
**Cause:** Looking at old CSV

**Fix:**
- Run `match_and_rename.py` to regenerate CSV
- Check date modified on CSV file

### Display too wide
**Fix:** Reduce terminal width or pipe to `less`:
```bash
python view_progress.py | less -S
```

## Keyboard Shortcuts

When viewing in terminal:
- **Scroll**: Use mouse wheel or arrow keys
- **Search**: Use terminal's find function (Cmd+F on Mac)
- **Copy**: Select text and Cmd+C

## Related Commands

```bash
# View progress
python view_progress.py

# Match receipts
python match_and_rename.py

# Monitor for new receipts
python monitor_receipts.py

# Open CSV in Excel
open output/statement_with_matches.csv
```

## Examples

### Check progress quickly
```bash
python view_progress.py
# Shows: 54 total, 5 matched (9.3%)
```

### Find what still needs receipts
```bash
python view_progress.py --unmatched
# Shows: 49 transactions without receipts
```

### Verify specific matches
```bash
python view_progress.py --matched
# Shows: 5 matched transactions with receipt names
```

## Tips

1. **Run often** - Quick way to check status without opening Excel
2. **Use filters** - `--matched` and `--unmatched` to focus on specific items
3. **Combine with grep** - `python view_progress.py | grep "Google"` to find specific merchants
4. **Save snapshots** - Export to file before/after matching sessions

## See Also

- `match_and_rename.py` - Match and rename receipts
- `monitor_receipts.py` - Monitor for new receipts
- `README_MATCH_AND_RENAME.md` - Matching documentation
- `README_MONITOR.md` - Monitor documentation
