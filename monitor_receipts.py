#!/usr/bin/env python3
"""
Receipt Monitor - Watch receipts folder and auto-match new receipts

Monitors the receipts folder for new PDF files and automatically:
1. Extracts data from the new receipt
2. Matches it against the bank statement
3. Renames and moves if matched
4. Updates the CSV
"""

import time
import pandas as pd
import re
import shutil
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.receipt_processor import ReceiptProcessor
from fuzzywuzzy import fuzz
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

console = Console()

# Configuration
STATEMENT_FILE = "data/statements/Umsatzanzeige Jan 31 2026.csv"
RECEIPTS_FOLDER = "data/receipts"
OUTPUT_CSV = "output/statement_with_matches.csv"
RENAMED_RECEIPTS_FOLDER = "output/renamed_receipts"

# Matching parameters
DATE_TOLERANCE_DAYS = 45
AMOUNT_TOLERANCE = 0.10
MIN_CONFIDENCE = 60


class ReceiptMonitor(FileSystemEventHandler):
    """Monitor for new receipt files"""
    
    def __init__(self):
        self.console = Console()
        self.processor = ReceiptProcessor(RECEIPTS_FOLDER)
        self.load_statement()
        self.processed_files = set()
        
    def load_statement(self):
        """Load bank statement CSV"""
        self.console.print("[yellow]Loading bank statement...[/yellow]")
        
        # Check if updated CSV exists, otherwise use original
        if Path(OUTPUT_CSV).exists():
            self.df = pd.read_csv(OUTPUT_CSV, sep=';', encoding='utf-8-sig')
            self.console.print(f"[green]✓[/green] Loaded existing matches from {OUTPUT_CSV}")
        else:
            self.df = pd.read_csv(STATEMENT_FILE, sep=';', encoding='utf-8-sig')
            # Add match columns if they don't exist
            if 'Matching Receipt Found' not in self.df.columns:
                self.df['Matching Receipt Found'] = False
                self.df['Matched Receipt File'] = ''
                self.df['Match Confidence'] = 0
            self.console.print(f"[green]✓[/green] Loaded {len(self.df)} transactions from statement")
        
        # Parse dates and amounts
        self.df['date'] = pd.to_datetime(self.df['Buchungstag'], format='%d.%m.%Y', errors='coerce')
        self.df['amount_float'] = self.df['Betrag'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        
        # Extract USD amounts
        self.df['usd_amount'] = self.df['Verwendungszweck'].apply(self.extract_usd_amount)
        
        # Extract merchant names
        self.df['merchant'] = self.df['Verwendungszweck'].apply(self.extract_merchant_name)
    
    def extract_usd_amount(self, text):
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
    
    def extract_merchant_name(self, text):
        """Extract clean merchant name from transaction description"""
        if pd.isna(text):
            return "Unknown"
        
        text = str(text).strip()
        
        # Remove common bank jargon
        text = re.sub(r'EREF:.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'MREF:.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'CRED:.*', '', text, flags=re.IGNORECASE)
        
        # Take first meaningful part
        parts = text.split()
        if parts:
            merchant_parts = []
            for part in parts[:5]:
                if len(part) > 2 and not re.match(r'^\d+$', part):
                    merchant_parts.append(part)
                    if len(merchant_parts) >= 3:
                        break
            
            if merchant_parts:
                merchant = ' '.join(merchant_parts)
                merchant = re.sub(r'[^\w\s-]', '', merchant)
                merchant = merchant.strip()[:50]
                return merchant if merchant else "Unknown"
        
        return "Unknown"
    
    def on_created(self, event):
        """Called when a file is created"""
        if event.is_directory:
            return
        
        # Only process PDF files
        if not event.src_path.endswith('.pdf'):
            return
        
        file_path = Path(event.src_path)
        
        # Skip if already processed
        if str(file_path) in self.processed_files:
            return
        
        # Wait a bit for file to be fully written
        time.sleep(1)
        
        # Process the new receipt
        self.process_new_receipt(file_path)
        self.processed_files.add(str(file_path))
    
    def process_new_receipt(self, receipt_path):
        """Process and match a new receipt"""
        self.console.print(f"\n[bold cyan]New receipt detected:[/bold cyan] {receipt_path.name}")
        
        # Extract data from receipt
        self.console.print("[yellow]Extracting receipt data...[/yellow]")
        receipt_data = self.processor.process_receipt(receipt_path)
        
        if not receipt_data['amount'] or not receipt_data['date']:
            self.console.print(f"[red]✗[/red] Could not extract date or amount from receipt")
            return
        
        self.console.print(f"[green]✓[/green] Receipt: {receipt_data['merchant']} - ${receipt_data['amount']:.2f} on {receipt_data['date'].strftime('%Y-%m-%d')}")
        
        # Try to match with unmatched transactions
        self.console.print("[yellow]Searching for matching transaction...[/yellow]")
        
        unmatched = self.df[self.df['Matching Receipt Found'] == False]
        
        best_match_idx = None
        best_score = 0
        
        for idx, row in unmatched.iterrows():
            transaction_date = row['date']
            eur_amount = row['amount_float']
            usd_amount = row['usd_amount']
            merchant = row['merchant']
            
            if pd.isna(transaction_date) or eur_amount == 0:
                continue
            
            # Date matching
            date_diff = abs((transaction_date - receipt_data['date']).days)
            if date_diff > DATE_TOLERANCE_DAYS:
                continue
            
            # Amount matching
            amount_match = False
            
            # Try USD match first
            if usd_amount and not pd.isna(usd_amount):
                if abs(usd_amount - receipt_data['amount']) / max(abs(usd_amount), receipt_data['amount']) < AMOUNT_TOLERANCE:
                    amount_match = True
            
            # Try EUR match
            if not amount_match:
                if abs(abs(eur_amount) - receipt_data['amount']) / max(abs(eur_amount), receipt_data['amount']) < AMOUNT_TOLERANCE:
                    amount_match = True
            
            if not amount_match:
                continue
            
            # Calculate confidence score
            score = 60  # Base score for date + amount
            
            # Add merchant similarity
            if receipt_data['merchant']:
                merchant_sim = fuzz.partial_ratio(merchant.lower(), receipt_data['merchant'].lower())
                score += merchant_sim * 0.4
            
            # Prefer closer dates
            if date_diff <= 3:
                score += 10
            elif date_diff <= 7:
                score += 5
            
            if score > best_score:
                best_score = score
                best_match_idx = idx
        
        # Process match
        if best_match_idx is not None and best_score >= MIN_CONFIDENCE:
            row = self.df.loc[best_match_idx]
            row_num = best_match_idx + 2  # +2 for header and 0-index
            
            # Get merchant from receipt
            receipt_merchant = receipt_data.get('merchant', '').strip() if receipt_data.get('merchant') else row['merchant']
            clean_merchant = re.sub(r'[^\w\s-]', '', receipt_merchant)
            clean_merchant = clean_merchant.strip()[:50] if clean_merchant else row['merchant']
            
            self.console.print(f"[bold green]✓ MATCH FOUND![/bold green]")
            self.console.print(f"  Row: {row_num}")
            self.console.print(f"  Date: {row['date'].strftime('%Y-%m-%d')}")
            self.console.print(f"  Amount: €{row['amount_float']:.2f}")
            self.console.print(f"  Merchant: {clean_merchant}")
            self.console.print(f"  Confidence: {int(best_score)}%")
            
            # Update dataframe
            self.df.loc[best_match_idx, 'Matching Receipt Found'] = True
            self.df.loc[best_match_idx, 'Matched Receipt File'] = receipt_path.name
            self.df.loc[best_match_idx, 'Match Confidence'] = int(best_score)
            
            # Save updated CSV
            self.df.to_csv(OUTPUT_CSV, sep=';', index=False, encoding='utf-8-sig')
            self.console.print(f"[green]✓[/green] Updated CSV: {OUTPUT_CSV}")
            
            # Rename and move receipt
            renamed_folder = Path(RENAMED_RECEIPTS_FOLDER)
            renamed_folder.mkdir(parents=True, exist_ok=True)
            
            new_filename = f"{row_num:03d}_{clean_merchant}.pdf"
            new_path = renamed_folder / new_filename
            
            try:
                shutil.copy2(receipt_path, new_path)
                self.console.print(f"[green]✓[/green] Renamed: {new_filename}")
                
                # Remove original
                receipt_path.unlink()
                self.console.print(f"[green]✓[/green] Removed original from source folder")
                
            except Exception as e:
                self.console.print(f"[red]✗[/red] Error processing file: {e}")
        else:
            self.console.print(f"[yellow]✗ No match found[/yellow] (best confidence: {int(best_score)}%)")
            self.console.print(f"  Receipt will remain in folder for manual review")


def main():
    console.print("\n[bold blue]Receipt Monitor - Auto-Match Service[/bold blue]\n")
    console.print(f"[cyan]Monitoring:[/cyan] {RECEIPTS_FOLDER}")
    console.print(f"[cyan]Statement:[/cyan] {STATEMENT_FILE}")
    console.print(f"[cyan]Output:[/cyan] {OUTPUT_CSV}")
    console.print()
    
    # Create event handler
    event_handler = ReceiptMonitor()
    
    # Process existing files first
    console.print("[yellow]Checking for existing unprocessed receipts...[/yellow]")
    receipts_folder = Path(RECEIPTS_FOLDER)
    existing_files = list(receipts_folder.glob("**/*.pdf"))
    
    unprocessed_count = 0
    for pdf_file in existing_files:
        if str(pdf_file) not in event_handler.processed_files:
            console.print(f"[cyan]Processing existing file:[/cyan] {pdf_file.name}")
            event_handler.process_new_receipt(pdf_file)
            event_handler.processed_files.add(str(pdf_file))
            unprocessed_count += 1
    
    if unprocessed_count > 0:
        console.print(f"[green]✓[/green] Processed {unprocessed_count} existing receipts\n")
    else:
        console.print(f"[green]✓[/green] No unprocessed receipts found\n")
    
    # Start monitoring for new files
    observer = Observer()
    observer.schedule(event_handler, RECEIPTS_FOLDER, recursive=True)
    observer.start()
    console.print("[bold green]✓ Monitoring started![/bold green]")
    console.print("[yellow]Watching for new receipts... (Press Ctrl+C to stop)[/yellow]\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping monitor...[/yellow]")
        observer.stop()
        observer.join()
        console.print("[green]✓ Monitor stopped[/green]\n")


if __name__ == '__main__':
    main()
