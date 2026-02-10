# Changelog

All notable changes to SWEET DUDE SWEET DUDE SWEET DUDE SWEET will be documented in this file.

## [3.0.0] - 2026-02-10 (MAJOR OVERHAUL)

### 🎨 Complete UI Redesign
- **Rebranded** to "SWEET DUDE SWEET DUDE SWEET DUDE SWEET" 💰
- **Animated gradient background** (purple/pink) with smooth color shifting
- **Glass-morphism design** with frosted glass effects on all cards
- **Golden animated title** with pulsing glow effect (20% smaller font)
- **Improved stat cards** with hover animations and lift effects
- **Enhanced button styling** with ripple effects and smooth transitions

### 🚀 Drag-and-Drop Receipt Assignment
- **Drop files directly onto table rows** to assign receipts
- Works on all transaction tables (All, Matched, Unmatched)
- **Automatic file renaming** to `{row}_{merchant}.pdf` format
- **Replace/Restore dialog** for existing receipts:
  - Replace & Delete: Removes old receipt
  - Replace & Restore: Moves old receipt back to unassigned folder
- **Visual feedback** with purple gradient and golden dashed border on drag-over

### ↶ Undo System
- **Full undo support** for manual receipt assignments
- Stores last 50 operations per statement in memory
- **Undo button in header** next to Refresh button
- Shows operation count: "↶ Undo (3)"
- Keyboard shortcut: **Cmd/Ctrl + Z**

### 👥 Private Transaction Tracking
- **Mark/Flo ownership buttons** for each transaction
- Independent toggle buttons (both can be active simultaneously)
- **Red gradient** when active, white when inactive
- **Auto-activates "No Receipt Needed"** when set to private
- Ownership resets to neutral when receipt is assigned
- Stored in CSV with `Owner_Mark` and `Owner_Flo` columns

### 🗑️ Delete Receipt Assignment
- **Red X button** next to each matched receipt in transaction tables
- Click to remove receipt from row
- **File moved back to receipts folder** with random 6-character prefix
- Confirmation dialog before deletion
- Preserves ownership and "No Receipt Needed" settings

### 🧠 Machine Learning System
- **"Update Learning" button** appears at 100% completion
- Located inside Completion % stat card (compact green button)
- **Processes all matched receipts** to extract training data
- Saves to `learning_data.json` for future ML model training
- Tracks correlations between:
  - Receipt amounts vs Transaction amounts
  - Receipt dates vs Transaction dates
  - Receipt merchants vs Transaction descriptions
  - OCR patterns and corrections

### ⌨️ Keyboard Shortcuts
- **Cmd/Ctrl + Z**: Undo last assignment
- **Cmd/Ctrl + Enter**: Run matching
- **Cmd/Ctrl + R**: Refresh data
- **1-5**: Switch between tabs
- **Esc**: Close modals
- Shortcuts logged to console on page load

### 🔧 Receipt Processing Improvements
- **Fixed date parsing** for OCR errors (2029→2025, 2027→2025, etc.)
- **Added "Endsumme" pattern** for German totals
- **Added "Gesamtbetrag" pattern** (highest priority for invoices)
- **Improved currency detection** - EUR prioritized for German receipts
- **Better year correction logic** for receipts in early 2026

### 🎯 UI/UX Improvements
- Moved Undo button to header (consistent with Refresh)
- Removed duplicate action buttons
- Stats cards show hover effects (lift and glow)
- Table rows slide on hover with purple shadow
- Badges pulse with animations
- Matched badges glow green
- Glass-morphism on all major UI components

### 📊 Technical Improvements
- Undo history tracking with automatic state management
- Ownership data persisted in CSV files
- Learning data accumulation across statements
- Random prefix generation for restored receipts
- Improved transaction API with ownership fields

### Bug Fixes
- Fixed receipt amount extraction for "Endsumme 2.808,40" format
- Fixed currency misdetection (EUR receipts showing as GBP)
- Fixed date parsing for email receipts ("30 November 2025 at 14:07")
- Fixed ownership button disable state when receipt is matched

# Changelog

All notable changes to Receipt Checker will be documented in this file.

## [2.1.0] - 2026-02-10

### Added
- Date guidance in matching (tertiary criterion, provides bonus points)
- Currency conversion auto-detection (USD/GBP from transaction description)
- Multi-tier merchant validation (5 tiers: <30, 30-44, 45-59, 60-74, 75+)
- Web UI: CLEAR button to reset statement
- Web UI: DELETE button with CAPTCHA confirmation
- Hidden _matches.csv files from statement tabs
- Comprehensive BUILD_LOG.md documentation

### Changed
- Increased non-EUR tolerance from 10% to 20% (accounts for exchange rates + fees)
- Matching algorithm now uses date as guidance, not requirement
- Confidence scoring: Amount (50pts), Merchant (35pts), Date (15pts)

### Fixed
- get_all_statements() now filters out _matches.csv files
- Currency conversion matching for USD/GBP receipts
- German number format parsing in statements

### Test Results
- 2/2 currency conversion receipts matched (Midjourney, Panoee)
- 100% accuracy, no false positives
- Exchange rate handling verified (€10→€8.76 matched at 12.4% diff)

## [2.0.0] - 2026-02-10

### Added
- Relaxed matching algorithm (merchant threshold 35-50)
- Web interface management controls
- Clear statement functionality
- Delete statement with CAPTCHA
- Multi-currency support (USD, EUR, GBP)
- German invoice pattern recognition

### Changed
- Removed strict date matching requirement
- Amount tolerance: EUR ±2%, Non-EUR ±10%
- Merchant scoring more lenient

### Fixed
- German number format conversion (comma decimals)
- Receipt amount extraction for various formats
- Web app StatementParser integration

## [1.0.0] - Initial Release

### Added
- Basic receipt matching functionality
- Web interface with dashboard
- Statement upload and receipt management
- Manual matching with strict criteria
- Support for German bank statements (CSV format)


## [2.1.1] - 2026-02-10 (UI Update)

### Added
- Statement tabs now display in header for better visibility
- Label/rename prompt when uploading statements
- Custom statement labels stored in localStorage
- Single file restriction for statement uploads
- Hover tooltips showing full filenames on statement tabs

### Changed
- Moved statement tabs from separate section to header area
- Header layout reorganized (title + tabs + actions)
- Statement tab styling updated (bordered, cleaner look)

### Fixed
- Multi-file upload confusion (now enforces single file)
- Statement organization improved for better UX

### UI/UX Improvements
- Cleaner, more professional header layout
- Better space utilization
- User-friendly custom labels (e.g., "January 2026")
- Persistent labels across browser sessions


## [2.1.2] - 2026-02-10 (Delete Simplification)

### Changed
- Removed CAPTCHA requirement from delete function
- Delete now requires only single confirmation dialog
- Simpler, faster workflow for statement deletion

### Improved
- User experience: One confirmation instead of two
- Faster statement management
- Still shows warning dialog with consequences


## [2.1.3] - 2026-02-10 (Relaxed Matching for Poor PDF Extraction)

### Changed
- Relaxed merchant validation thresholds
- Lowered rejection threshold from 30 to 20
- Made 30-49 merchant score range more lenient
- Accepts matches with either good date OR good amount (was AND)

### Improved
- Matching rate improved from 6 to 10 matches (+67%) on December statement
- Better handling of receipts with poor PDF extraction
- More tolerant of date/amount extraction errors

### Context
- Addressing December statement with 62 receipts where PDF extraction is poor
- Many "Eigenbeleg" (self-made) receipts with placeholder amounts
- Dates often wrong (2026, 2027 instead of Dec 2025)

