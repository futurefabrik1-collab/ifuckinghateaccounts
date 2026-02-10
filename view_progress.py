#!/usr/bin/env python3
"""
Progress Viewer - Show matching status in a simplified table

Displays a clean table showing:
- Row number
- Date
- Merchant/Description
- Receipt matched (True/False)
"""

import pandas as pd
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
import sys

console = Console()

# Configuration
STATEMENT_FILE = "data/statements/Umsatzanzeige Jan 31 2026.csv"
OUTPUT_CSV = "output/statement_with_matches.csv"


def load_data():
    """Load the statement with match status"""
    # Try to load updated CSV first, otherwise use original
    if Path(OUTPUT_CSV).exists():
        df = pd.read_csv(OUTPUT_CSV, sep=';', encoding='utf-8-sig')
        source = OUTPUT_CSV
    else:
        df = pd.read_csv(STATEMENT_FILE, sep=';', encoding='utf-8-sig')
        # Add match columns if they don't exist
        if 'Matching Receipt Found' not in df.columns:
            df['Matching Receipt Found'] = False
            df['Matched Receipt File'] = ''
            df['Match Confidence'] = 0
        source = STATEMENT_FILE
    
    return df, source


def create_summary_stats(df):
    """Create summary statistics"""
    total = len(df)
    matched = df['Matching Receipt Found'].sum() if 'Matching Receipt Found' in df.columns else 0
    unmatched = total - matched
    match_rate = (matched / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'matched': matched,
        'unmatched': unmatched,
        'match_rate': match_rate
    }


def create_progress_table(df, show_all=True, show_matched_only=False, show_unmatched_only=False):
    """Create the progress table"""
    
    # Filter based on options
    if show_matched_only:
        display_df = df[df['Matching Receipt Found'] == True].copy()
        title = "Matched Transactions"
    elif show_unmatched_only:
        display_df = df[df['Matching Receipt Found'] == False].copy()
        title = "Unmatched Transactions"
    else:
        display_df = df.copy()
        title = "All Transactions"
    
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    # Add columns
    table.add_column("Row", style="cyan", width=5)
    table.add_column("Date", style="yellow", width=12)
    table.add_column("Amount", style="green", width=12)
    table.add_column("Merchant/Description", style="white", width=50)
    table.add_column("Matched", style="bold", width=10)
    table.add_column("Receipt", style="dim", width=30)
    
    # Add rows
    for idx, row in display_df.iterrows():
        row_num = idx + 2  # +2 for header and 0-index
        
        # Format date
        date_str = row['Buchungstag'] if pd.notna(row['Buchungstag']) else 'N/A'
        
        # Format amount
        amount_str = f"€{row['Betrag']}" if pd.notna(row['Betrag']) else 'N/A'
        
        # Get merchant/description
        description = str(row['Verwendungszweck'])[:50] if pd.notna(row['Verwendungszweck']) else 'N/A'
        
        # Match status
        is_matched = row['Matching Receipt Found'] if 'Matching Receipt Found' in row else False
        matched_str = "[green]✓ Yes[/green]" if is_matched else "[red]✗ No[/red]"
        
        # Receipt file
        receipt = row['Matched Receipt File'][:30] if pd.notna(row.get('Matched Receipt File', '')) and row.get('Matched Receipt File', '') else '-'
        
        table.add_row(
            str(row_num),
            date_str,
            amount_str,
            description,
            matched_str,
            receipt
        )
    
    return table


def main():
    """Main viewer"""
    console.print("\n[bold blue]Receipt Matching Progress Viewer[/bold blue]\n")
    
    # Load data
    df, source = load_data()
    console.print(f"[dim]Loaded from: {source}[/dim]\n")
    
    # Show summary
    stats = create_summary_stats(df)
    
    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Transactions", str(stats['total']))
    summary_table.add_row("Matched", f"[green]{stats['matched']}[/green]")
    summary_table.add_row("Unmatched", f"[red]{stats['unmatched']}[/red]")
    summary_table.add_row("Match Rate", f"{stats['match_rate']:.1f}%")
    
    console.print(Panel(summary_table, title="Summary", border_style="blue"))
    console.print()
    
    # Check command line arguments
    show_matched = '--matched' in sys.argv or '-m' in sys.argv
    show_unmatched = '--unmatched' in sys.argv or '-u' in sys.argv
    
    # Show progress table
    table = create_progress_table(
        df, 
        show_all=not (show_matched or show_unmatched),
        show_matched_only=show_matched,
        show_unmatched_only=show_unmatched
    )
    
    console.print(table)
    console.print()
    
    # Show help
    console.print("[dim]Options:[/dim]")
    console.print("[dim]  python view_progress.py          - Show all transactions[/dim]")
    console.print("[dim]  python view_progress.py --matched   - Show only matched[/dim]")
    console.print("[dim]  python view_progress.py --unmatched - Show only unmatched[/dim]")
    console.print()


if __name__ == '__main__':
    main()
