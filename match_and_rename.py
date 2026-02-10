#!/usr/bin/env python3
"""
Match receipts to GLS bank statement and rename files with row numbers
"""

import pandas as pd
import re
import shutil
from pathlib import Path
from datetime import datetime
from src.receipt_processor import ReceiptProcessor
from fuzzywuzzy import fuzz
from rich.console import Console
from rich.table import Table
from rich.progress import track

console = Console()

# Configuration
STATEMENT_FILE = "data/statements/Umsatzanzeige Jan 31 2026.csv"
RECEIPTS_FOLDER = "data/receipts"
OUTPUT_CSV = "output/statement_with_matches.csv"
RENAMED_RECEIPTS_FOLDER = "output/renamed_receipts"

console.print("\n[bold blue]Receipt Matcher & File Renamer[/bold blue]\n")

# Load statement
console.print("[yellow]Loading bank statement...[/yellow]")
df = pd.read_csv(STATEMENT_FILE, sep=';', encoding='utf-8-sig')
console.print(f"[green]✓[/green] Loaded {len(df)} transactions\n")

# Parse dates and amounts
df['date'] = pd.to_datetime(df['Buchungstag'], format='%d.%m.%Y', errors='coerce')
df['amount_float'] = df['Betrag'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)

# Extract merchant name from Verwendungszweck
def extract_merchant_name(text):
    """Extract clean merchant name from transaction description"""
    if pd.isna(text):
        return "Unknown"
    
    text = str(text).strip()
    
    # Remove common bank jargon
    text = re.sub(r'EREF:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'MREF:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'CRED:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'IBAN:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'BIC:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Mandatsreferenz:.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Glaeubiger-ID:.*', '', text, flags=re.IGNORECASE)
    
    # Take first meaningful part
    parts = text.split()
    if parts:
        # Take first 3-4 words or until we hit numbers/codes
        merchant_parts = []
        for part in parts[:5]:
            if len(part) > 2 and not re.match(r'^\d+$', part):
                merchant_parts.append(part)
                if len(merchant_parts) >= 3:
                    break
        
        if merchant_parts:
            merchant = ' '.join(merchant_parts)
            # Clean up special characters for filename
            merchant = re.sub(r'[^\w\s-]', '', merchant)
            merchant = merchant.strip()[:50]  # Max 50 chars
            return merchant if merchant else "Unknown"
    
    return "Unknown"

df['merchant'] = df['Verwendungszweck'].apply(extract_merchant_name)

# Extract USD amounts if present
def extract_usd_amount(text):
    """Extract USD amount from transaction description"""
    if pd.isna(text):
        return None
    match = re.search(r'USD\s+([\d,\.]+)', str(text))
    if match:
        amount_str = match.group(1).replace(',', '.')
        try:
            return float(amount_str)
        except:
            return None
    return None

df['usd_amount'] = df['Verwendungszweck'].apply(extract_usd_amount)

# Process receipts
console.print("[yellow]Scanning receipts...[/yellow]")
processor = ReceiptProcessor(RECEIPTS_FOLDER)
receipt_files = processor.scan_receipts()
console.print(f"[green]✓[/green] Found {len(receipt_files)} receipt PDFs\n")

console.print("[yellow]Extracting receipt data...[/yellow]")
receipts = []
for receipt_path in track(receipt_files, description="Processing receipts..."):
    data = processor.process_receipt(receipt_path)
    receipts.append(data)

console.print(f"[green]✓[/green] Processed {len(receipts)} receipts\n")

# Match each transaction with receipts
console.print("[yellow]Matching transactions with receipts...[/yellow]\n")

df['Matching Receipt Found'] = False
df['Matched Receipt File'] = ''
df['Match Confidence'] = 0

matches = []
used_receipts = set()

for idx, row in df.iterrows():
    transaction_date = row['date']
    eur_amount = row['amount_float']
    usd_amount = row['usd_amount']
    merchant = row['merchant']
    
    if pd.isna(transaction_date) or eur_amount == 0:
        continue
    
    best_match = None
    best_score = 0
    best_receipt_idx = None
    
    for r_idx, receipt in enumerate(receipts):
        # Skip already matched receipts
        if receipt['filename'] in used_receipts:
            continue
        
        if not receipt['amount'] or not receipt['date']:
            continue
        
        # Date matching (within 45 days)
        date_diff = abs((transaction_date - receipt['date']).days)
        if date_diff > 45:
            continue
        
        # Amount matching
        amount_match = False
        
        # Try USD match first
        if usd_amount and not pd.isna(usd_amount):
            if abs(usd_amount - receipt['amount']) / max(abs(usd_amount), receipt['amount']) < 0.10:
                amount_match = True
        
        # Try EUR match
        if not amount_match:
            if abs(abs(eur_amount) - receipt['amount']) / max(abs(eur_amount), receipt['amount']) < 0.10:
                amount_match = True
        
        if not amount_match:
            continue
        
        # Calculate confidence score
        score = 60  # Base score for date + amount
        
        # Add merchant similarity
        if receipt['merchant']:
            merchant_sim = fuzz.partial_ratio(merchant.lower(), receipt['merchant'].lower())
            score += merchant_sim * 0.4
        
        # Prefer closer dates
        if date_diff <= 3:
            score += 10
        elif date_diff <= 7:
            score += 5
        
        if score > best_score:
            best_score = score
            best_match = receipt
            best_receipt_idx = r_idx
    
    # Record match
    if best_match and best_score >= 60:
        df.loc[idx, 'Matching Receipt Found'] = True
        df.loc[idx, 'Matched Receipt File'] = best_match['filename']
        df.loc[idx, 'Match Confidence'] = int(best_score)
        used_receipts.add(best_match['filename'])
        
        # Use merchant from receipt if available, otherwise use CSV merchant
        receipt_merchant = best_match.get('merchant', '').strip() if best_match.get('merchant') else merchant
        # Clean merchant name for filename
        clean_merchant = re.sub(r'[^\w\s-]', '', receipt_merchant)
        clean_merchant = clean_merchant.strip()[:50] if clean_merchant else merchant
        
        matches.append({
            'row': idx + 2,  # +2 because CSV has header and 0-index
            'date': transaction_date,
            'amount': eur_amount,
            'merchant': clean_merchant,  # Use receipt merchant for renaming
            'csv_merchant': merchant,  # Keep original for reference
            'receipt': best_match['filename'],
            'receipt_path': best_match['path'],
            'confidence': int(best_score)
        })

# Display results
console.print("[bold green]Matching Results[/bold green]\n")

summary_table = Table(show_header=True, header_style="bold magenta")
summary_table.add_column("Metric", style="cyan")
summary_table.add_column("Value", style="green")

total = len(df)
matched = df['Matching Receipt Found'].sum()
summary_table.add_row("Total Transactions", str(total))
summary_table.add_row("Matched", str(matched))
summary_table.add_row("Unmatched", str(total - matched))
summary_table.add_row("Match Rate", f"{matched/total*100:.1f}%")
summary_table.add_row("Receipts Used", f"{len(used_receipts)}/{len(receipts)}")

console.print(summary_table)
console.print()

# Show matched transactions
if matches:
    console.print(f"[bold green]Matched Transactions ({len(matches)})[/bold green]\n")
    match_table = Table(show_header=True, header_style="bold green")
    match_table.add_column("Row", style="cyan")
    match_table.add_column("Date", style="yellow")
    match_table.add_column("Amount", style="green")
    match_table.add_column("Merchant", style="white")
    match_table.add_column("Receipt", style="magenta")
    match_table.add_column("Conf%", style="blue")
    
    for match in matches[:10]:
        match_table.add_row(
            str(match['row']),
            match['date'].strftime('%Y-%m-%d'),
            f"€{match['amount']:.2f}",
            match['merchant'][:30],
            match['receipt'][:35],
            str(match['confidence'])
        )
    
    if len(matches) > 10:
        match_table.add_row("...", "...", "...", "...", f"...and {len(matches)-10} more", "...")
    
    console.print(match_table)
    console.print()

# Export updated CSV
console.print("[yellow]Exporting updated CSV...[/yellow]")
Path(OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_CSV, sep=';', index=False, encoding='utf-8-sig')
console.print(f"[green]✓[/green] Saved to {OUTPUT_CSV}\n")

# Rename and copy receipt files
if matches:
    console.print("[yellow]Renaming and copying receipt files...[/yellow]")
    renamed_folder = Path(RENAMED_RECEIPTS_FOLDER)
    renamed_folder.mkdir(parents=True, exist_ok=True)
    
    renamed_count = 0
    for match in track(matches, description="Renaming files..."):
        row_num = match['row']
        merchant = match['merchant']
        original_path = Path(match['receipt_path'])
        
        # Create new filename: ROW_Merchant.pdf
        new_filename = f"{row_num:03d}_{merchant}.pdf"
        new_path = renamed_folder / new_filename
        
        # Copy file with new name
        try:
            shutil.copy2(original_path, new_path)
            renamed_count += 1
        except Exception as e:
            console.print(f"[red]Error copying {original_path.name}: {e}[/red]")
    
    console.print(f"[green]✓[/green] Renamed {renamed_count} receipt files to {RENAMED_RECEIPTS_FOLDER}\n")

console.print("[bold green]Done![/bold green]\n")
console.print(f"[cyan]Updated CSV:[/cyan] {OUTPUT_CSV}")
console.print(f"[cyan]Renamed receipts:[/cyan] {RENAMED_RECEIPTS_FOLDER}")
console.print()
