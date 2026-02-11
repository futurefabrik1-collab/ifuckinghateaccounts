# Changelog - February 11, 2026

## Summary
Major update improving CSV handling, UI enhancements, and smart matching behavior.

---

## 🐛 Bug Fixes

### CSV Import & Parsing
- **Auto-detect CSV delimiters**: Now supports comma (`,`), semicolon (`;`), and tab (`\t`) delimiters automatically
- **Headerless CSV support**: Automatically detects CSVs without headers and assigns appropriate German column names (`Buchungstag`, `Verwendungszweck`, `Betrag`)
- **StatementParser improvements**: Added header detection logic to ensure consistent parsing across all functions
- **Match function delimiter handling**: Fixed delimiter detection when running the match process

### Technical Fixes
- **Logger import**: Added missing logger imports in `web/app.py`
- **Import order**: Fixed `sys.path.insert` order to ensure proper module loading
- **Column mapping**: Properly maps English column names to German equivalents when needed

---

## ✨ New Features

### Smart Matching Behavior
- **Manually Unmatched Flag**: New `Manually_Unmatched` column tracks when users manually delete receipt associations
  - Prevents automatic re-matching of manually unmatched transactions
  - Flag is cleared when user manually assigns a new receipt
  - Preserves user intent when running "Match Receipts" multiple times

### UI Enhancements

#### Branding Update
- Changed application name from "I FUCKING HATE ACCOUNTS" to **"I FUCKING HATE COUNTS"**
- Updated tagline to **"Because finding receipts fucking sucks!"**

#### Completion Card Visual Improvements
- **Dynamic background images**: 6 progression images that change based on completion percentage
  - Image 1: 0-19%
  - Image 2: 20-39%
  - Image 3: 40-59%
  - Image 4: 60-79%
  - Image 5: 80-99%
  - Image 6: 100%
- **100% image opacity**: Removed white overlay for full image visibility
- **Proper image sizing**: Using `contain` to show full images without cropping
- **Clean borders**: Removed borders for seamless image display

#### Statistics Display
- **20% larger numbers**: Stat values increased from 36px to 43px for better visibility
- **Color-matched labels**: Stat descriptions now match their corresponding number colors:
  - Total: Blue (#007aff)
  - Matched: Green (#34c759)
  - No Receipt: Orange (#ff9500)
  - Missing: Red (#ff3b30)
  - Completion %: Purple (#af52de)

---

## 📁 File Organization

### Cleanup
- Organized all images into `images/` folder
- Moved completion progression images (1.png - 6.png) to `web/static/images/`
- Cleaned up root directory image files

---

## 🚀 Deployment

### Railway Configuration
- Fixed PORT variable expansion issue
- Updated `railway.json` to use startup script
- Removed duplicate COPY commands in Dockerfile
- Fixed `.dockerignore` to allow `startup.sh`

### Environment
- All changes deployed to production: https://ifuckinghateaccounts-production.up.railway.app/
- Local development environment tested and verified

---

## 📊 Impact

### User Experience
- ✅ Supports more CSV formats without manual formatting
- ✅ Smarter matching that respects user decisions
- ✅ More visually appealing and readable interface
- ✅ Better progress visualization with dynamic images

### Developer Experience
- ✅ More robust CSV parsing
- ✅ Better error handling and logging
- ✅ Cleaner file organization
- ✅ Consistent delimiter handling across codebase

---

## 🔧 Technical Details

### Files Modified
- `web/app.py` - CSV parsing, logger, manually unmatched flag
- `web/templates/index.html` - UI improvements, completion card styling
- `src/statement_parser.py` - Header detection logic
- `railway.json` - Deployment configuration
- `Dockerfile` - Build process optimization
- `.dockerignore` - Allow startup script

### New Columns Added
- `Manually_Unmatched` (Boolean) - Tracks user-deleted matches

### Dependencies
No new dependencies added. All changes use existing libraries.

---

## 📝 Notes

### Migration
Existing statements will automatically get the `Manually_Unmatched` column added with default value `False` when loaded.

### Backward Compatibility
All changes are backward compatible with existing CSV files and matched data.

---

**Backup Created**: `Receipt_Checker_backup_20260211_155317.tar.gz` (9.0 MB)
