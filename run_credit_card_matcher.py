#!/usr/bin/env python3
"""
Custom matcher for GLS credit card statements
Extracts USD amounts from Verwendungszweck field
"""

import pandas as pd
import re
from pathlib import Path
from src.receipt_processor import ReceiptProcessor
from rich.console import Console
from rich.table import Table

console = Console()

# Load statement
console.print("\n[bold blue]Credit Card Receipt Matcher[/bold blue]\n")
console.print("[yellow]Loading statement...[/yellow]")

df = pd.read_csv(
    'data/statements/Umsatzanzeige GLS Gemeinschaftsbank Dez 31 2025.csv',
    sep=';',
    encoding='utf-8-sig'
)

console.print(f"[green]✓[/green] Loaded {len(df)} transactions\n")

# Extract USD amounts from Verwendungszweck
def extract_usd_amount(text):
    """Extract USD amount from transaction description"""
    if pd.isna(text):
        return None
    
    # Look for "USD XX,XX" or "USD XX.XX" pattern
    match = re.search(r'USD\s+([\d,\.]+)', str(text))
    if match:
        amount_str = match.group(1).replace(',', '.')
        try:
            return float(amount_str)
        except:
            return None
    return None

# Add USD amount column
df['usd_amount'] = df['Verwendungszweck'].apply(extract_usd_amount)
df['date'] = pd.to_datetime(df['Buchungstag'], format='%d.%m.%Y')

# Extract merchant name
def extract_merchant(text):
    """Extract merchant name from Verwendungszweck"""
    if pd.isna(text):
        return ""
    
    # Take first part before location info
    parts = str(text).split()
    if parts:
        return parts[0]
    return ""

df['merchant'] = df['Verwendungszweck'].apply(extract_merchant)

# Process receipts
console.print("[yellow]Processing receipts...[/yellow]")
processor = ReceiptProcessor('data/receipts/CCard/')
receipts = processor.process_all_receipts()
console.print(f"[green]✓[/green] Processed {len(receipts)} receipts\n")

# Match transactions
console.print("[yellow]Matching transactions...[/yellow]\n")

matches = []
unmatched = []

for idx, row in df.iterrows():
    transaction_date = row['date']
    usd_amount = row['usd_amount']
    eur_amount = float(str(row['Betrag']).replace(',', '.'))
    merchant = row['merchant']
    
    best_match = None
    best_score = 0
    
    for receipt in receipts:
        if not receipt['amount'] or not receipt['date']:
            continue
        
        # Check date (within 30 days)
        date_diff = abs((transaction_date - receipt['date']).days)
        if date_diff > 30:
            continue
        
        # Check amount (prefer USD match, fallback to EUR)
        amount_match = False
        if usd_amount and not pd.isna(usd_amount):
            # Match USD amount
            if abs(usd_amount - receipt['amount']) / max(usd_amount, receipt['amount']) < 0.05:
                amount_match = True
        else:
            # Try EUR amount (for transactions that were already in EUR)
            if abs(abs(eur_amount) - receipt['amount']) / max(abs(eur_amount), receipt['amount']) < 0.05:
                amount_match = True
        
        if not amount_match:
            continue
        
        # Calculate score
        score = 70  # Base score for date + amount match
        
        # Check merchant name similarity
        from fuzzywuzzy import fuzz
        merchant_score = fuzz.partial_ratio(merchant.lower(), receipt['merchant'].lower() if receipt['merchant'] else '')
        score += merchant_score * 0.3
        
        if score > best_score:
            best_score = score
            best_match = receipt
    
    if best_match:
        matches.append({
            'date': transaction_date,
            'eur_amount': eur_amount,
            'usd_amount': usd_amount,
            'merchant': merchant,
            'receipt': best_match['filename'],
            'receipt_amount': best_match['amount'],
            'confidence': int(best_score)
        })
    else:
        unmatched.append({
            'date': transaction_date,
            'eur_amount': eur_amount,
            'usd_amount': usd_amount,
            'merchant': merchant
        })

# Display results
console.print("[bold green]Results[/bold green]\n")

table = Table(show_header=True, header_style="bold magenta")
table.add_column("Metric", style="cyan")
table.add_column("Value", style="green")

table.add_row("Total Transactions", str(len(df)))
table.add_row("Matched", str(len(matches)))
table.add_row("Unmatched", str(len(unmatched)))
table.add_row("Match Rate", f"{len(matches)/len(df)*100:.1f}%")

console.print(table)
console.print()

# Show matches
if matches:
    console.print("[bold green]Matched Transactions[/bold green]\n")
    match_table = Table(show_header=True, header_style="bold green")
    match_table.add_column("Date", style="cyan")
    match_table.add_column("EUR", style="yellow")
    match_table.add_column("USD", style="yellow")
    match_table.add_column("Merchant", style="white")
    match_table.add_column("Receipt", style="green")
    match_table.add_column("Conf%", style="magenta")
    
    for match in matches:
        match_table.add_row(
            str(match['date'].date()),
            f"€{match['eur_amount']:.2f}",
            f"${match['usd_amount']:.2f}" if match['usd_amount'] else "N/A",
            match['merchant'],
            match['receipt'][:30],
            str(match['confidence'])
        )
    
    console.print(match_table)
    console.print()

# Show unmatched
if unmatched:
    console.print(f"[bold yellow]Unmatched Transactions ({len(unmatched)})[/bold yellow]\n")
    unmatch_table = Table(show_header=True, header_style="bold yellow")
    unmatch_table.add_column("Date", style="cyan")
    unmatch_table.add_column("EUR", style="yellow")
    unmatch_table.add_column("USD", style="yellow")
    unmatch_table.add_column("Merchant", style="white")
    
    for item in unmatched:
        unmatch_table.add_row(
            str(item['date'].date()),
            f"€{item['eur_amount']:.2f}",
            f"${item['usd_amount']:.2f}" if item['usd_amount'] else "N/A",
            item['merchant']
        )
    
    console.print(unmatch_table)
    console.print()

console.print(f"[green]✓[/green] Done!\n")

# Export to Excel
console.print("[yellow]Exporting results to Excel...[/yellow]")

# Prepare matched data
matched_data = []
for match in matches:
    matched_data.append({
        'Date': match['date'].strftime('%Y-%m-%d'),
        'EUR Amount': match['eur_amount'],
        'USD Amount': match['usd_amount'] if match['usd_amount'] and not pd.isna(match['usd_amount']) else '',
        'Merchant': match['merchant'],
        'Receipt File': match['receipt'],
        'Receipt Amount': match['receipt_amount'],
        'Confidence %': match['confidence'],
        'Status': 'Matched'
    })

# Prepare unmatched data
for item in unmatched:
    matched_data.append({
        'Date': item['date'].strftime('%Y-%m-%d'),
        'EUR Amount': item['eur_amount'],
        'USD Amount': item['usd_amount'] if item['usd_amount'] and not pd.isna(item['usd_amount']) else '',
        'Merchant': item['merchant'],
        'Receipt File': '',
        'Receipt Amount': '',
        'Confidence %': '',
        'Status': 'Unmatched'
    })

# Create DataFrame and export
results_df = pd.DataFrame(matched_data)
results_df = results_df.sort_values('Date', ascending=False)

output_path = Path('output/credit_card_matches.xlsx')
output_path.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    results_df.to_excel(writer, sheet_name='Matches', index=False)
    
    # Format the worksheet
    worksheet = writer.sheets['Matches']
    
    # Set column widths
    worksheet.column_dimensions['A'].width = 12  # Date
    worksheet.column_dimensions['B'].width = 12  # EUR Amount
    worksheet.column_dimensions['C'].width = 12  # USD Amount
    worksheet.column_dimensions['D'].width = 25  # Merchant
    worksheet.column_dimensions['E'].width = 35  # Receipt File
    worksheet.column_dimensions['F'].width = 15  # Receipt Amount
    worksheet.column_dimensions['G'].width = 12  # Confidence
    worksheet.column_dimensions['H'].width = 12  # Status

console.print(f"[green]✓[/green] Results exported to {output_path}\n")
