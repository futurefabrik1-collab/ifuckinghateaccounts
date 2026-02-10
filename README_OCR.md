# OCR Support for Image Receipts

## Overview

The Receipt Checker now supports image receipts (JPG, PNG, TIFF, etc.) using Tesseract OCR.

## Supported Formats

**PDF** (via pdfplumber):
- Standard PDF receipts
- Multi-page invoices

**Images** (via Tesseract OCR):
- JPG, JPEG
- PNG
- TIFF, TIF
- BMP
- GIF

## Installation

### Prerequisites

1. **Tesseract OCR** must be installed on your system:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

2. **Python dependencies** (already in requirements.txt):

```bash
pip install pytesseract pillow
```

### Language Support

German and English are configured by default:

```bash
# macOS - check installed languages
tesseract --list-langs

# Install additional languages if needed
brew install tesseract-lang
```

## Usage

Simply upload image receipts to the receipts folder - they will be automatically detected and processed with OCR!

```python
from src.receipt_processor import ReceiptProcessor

processor = ReceiptProcessor("path/to/receipts/")
receipts = processor.scan_receipts()  # Finds both PDFs and images

for receipt in receipts:
    data = processor.process_receipt(receipt)
    print(f"{receipt.name}: {data['merchant']} - €{data['amount']}")
```

## Configuration

OCR settings in `src/receipt_processor.py`:

```python
custom_config = r'--oem 3 --psm 6 -l deu+eng'
```

- `--oem 3`: LSTM neural network mode
- `--psm 6`: Assume uniform block of text
- `-l deu+eng`: German + English languages

## Tips for Best Results

1. **Image Quality**: Use high-resolution images (300+ DPI)
2. **Lighting**: Ensure good, even lighting
3. **Orientation**: Keep images straight (minimal rotation)
4. **Format**: PNG or TIFF work best (lossless)
5. **Contrast**: High contrast between text and background

## Troubleshooting

### OCR returns empty text

- Check if Tesseract is installed: `tesseract --version`
- Verify language packs: `tesseract --list-langs`
- Try preprocessing image (increase contrast, convert to grayscale)

### Poor extraction quality

- Increase image resolution
- Improve lighting/contrast
- Remove shadows and glare
- Try different OCR modes (`--psm` values)

### German characters not recognized

- Install German language pack: `brew install tesseract-lang`
- Verify with: `tesseract --list-langs | grep deu`

## Performance

OCR is slower than PDF text extraction:
- PDFs: ~0.1-0.5 seconds
- Images: ~1-3 seconds (depending on resolution)

For bulk processing, consider running in background or showing progress indicators.

## Future Improvements

Planned enhancements:
- [ ] Image preprocessing (auto-rotation, denoising)
- [ ] OCR confidence scoring
- [ ] Batch processing optimization
- [ ] Multi-page image support
- [ ] Manual text correction UI

## Example

```python
# Process an image receipt
from pathlib import Path
from src.receipt_processor import ReceiptProcessor

processor = ReceiptProcessor("receipts/")
image_receipt = Path("receipts/photo_receipt.jpg")

data = processor.process_receipt(image_receipt)

print(f"Merchant: {data['merchant']}")
print(f"Amount: €{data['amount']}")
print(f"Date: {data['date']}")
print(f"Is Image: {data['is_image']}")
```

## Technical Details

The OCR implementation automatically:
1. Detects file type by extension
2. Routes to appropriate extractor (PDF vs Image)
3. Uses Tesseract with German+English config
4. Applies same extraction patterns as PDFs
5. Returns standardized data structure

No changes needed in the web interface - image uploads work automatically!
