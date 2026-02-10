#!/usr/bin/env python3
"""
Receipt Checker - Main CLI Interface

Match bank statement transactions with receipt PDFs
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print as rprint

from src.statement_parser import StatementParser
from src.receipt_processor import ReceiptProcessor
from src.matcher import ReceiptMatcher


console = Console()


@click.group()
def cli():
    """Receipt Checker - Match bank statements with receipt PDFs"""
    pass


@cli.command()
@click.argument('statement_file', type=click.Path(exists=True))
@click.argument('receipts_folder', type=click.Path(exists=True))
@click.option('--output', '-o', default='output/results.xlsx', help='Output file path')
@click.option('--date-column', default='Date', help='Name of date column in statement')
@click.option('--amount-column', default='Amount', help='Name of amount column in statement')
@click.option('--description-column', default='Description', help='Name of description column in statement')
@click.option('--date-tolerance', default=None, help='DEPRECATED - dates no longer used for matching')
@click.option('--amount-tolerance', default=0.001, help='Percentage tolerance for EUR amount matching (0.001 = 0.1% - essentially exact)')
@click.option('--amount-tolerance-non-eur', default=0.20, help='Percentage tolerance for non-EUR amounts (0.20 = 20% for exchange rates + fees)')
def match(statement_file, receipts_folder, output, date_column, amount_column, 
         description_column, date_tolerance, amount_tolerance, amount_tolerance_non_eur):
    """Match transactions with receipts"""
    
    console.print("\n[bold blue]Receipt Checker[/bold blue] :receipt:\n")
    
    # Load bank statement
    console.print("[yellow]Loading bank statement...[/yellow]")
    parser = StatementParser(statement_file)
    df = parser.load_statement(
        date_column=date_column,
        amount_column=amount_column,
        description_column=description_column
    )
    console.print(f"[green]✓[/green] Loaded {len(df)} transactions\n")
    
    # Process receipts
    console.print("[yellow]Processing receipts...[/yellow]")
    processor = ReceiptProcessor(receipts_folder)
    receipts = processor.scan_receipts()
    console.print(f"[green]✓[/green] Found {len(receipts)} receipt PDFs")
    
    receipt_data = []
    for receipt_path in track(receipts, description="Extracting receipt data..."):
        data = processor.process_receipt(receipt_path)
        receipt_data.append(data)
    
    console.print(f"[green]✓[/green] Processed {len(receipt_data)} receipts\n")
    
    # Match transactions with receipts
    console.print("[yellow]Matching transactions with receipts...[/yellow]")
    console.print(f"[dim]Amount tolerance: EUR ±{amount_tolerance*100}%, Non-EUR ±{amount_tolerance_non_eur*100}%[/dim]")
    console.print(f"[dim]Note: Dates no longer required (receipts can be weeks apart)[/dim]\n")
    
    matcher = ReceiptMatcher(
        amount_tolerance_percent=amount_tolerance,
        amount_tolerance_non_eur=amount_tolerance_non_eur
    )
    
    transactions = parser.get_transactions()
    results = matcher.match_all_transactions(transactions, receipt_data)
    
    # Update statement with matches
    for result in results:
        if result['matched']:
            idx = result['transaction_index']
            parser.mark_as_matched(idx, result['receipt']['filename'])
    
    # Generate report
    report = matcher.generate_report(results)
    
    # Display results
    console.print("\n[bold green]Matching Results[/bold green]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Transactions", str(report['total_transactions']))
    table.add_row("Matched", str(report['matched']))
    table.add_row("Unmatched", str(report['unmatched']))
    table.add_row("Match Rate", f"{report['match_rate']:.1f}%")
    table.add_row("Avg Confidence", f"{report['average_confidence']:.1f}")
    
    console.print(table)
    
    # Export results
    console.print(f"\n[yellow]Exporting results to {output}...[/yellow]")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parser.export_results(output)
    console.print(f"[green]✓[/green] Results saved to {output}\n")
    
    # Show unmatched transactions
    unmatched = parser.get_unmatched_transactions()
    if len(unmatched) > 0:
        console.print(f"\n[bold yellow]Unmatched Transactions ({len(unmatched)})[/bold yellow]\n")
        unmatched_table = Table(show_header=True, header_style="bold yellow")
        unmatched_table.add_column("Date", style="cyan")
        unmatched_table.add_column("Amount", style="green")
        unmatched_table.add_column("Description", style="white")
        
        for _, row in unmatched.head(10).iterrows():
            unmatched_table.add_row(
                str(row['date'].date()),
                f"${row['amount']:.2f}",
                str(row['description'])[:50]
            )
        
        if len(unmatched) > 10:
            unmatched_table.add_row("...", "...", f"...and {len(unmatched) - 10} more")
        
        console.print(unmatched_table)
        console.print()


@cli.command()
@click.argument('receipts_folder', type=click.Path(exists=True))
def scan(receipts_folder):
    """Scan and preview receipt data"""
    
    console.print("\n[bold blue]Scanning Receipts[/bold blue] :mag:\n")
    
    processor = ReceiptProcessor(receipts_folder)
    receipts = processor.scan_receipts()
    
    console.print(f"Found {len(receipts)} PDF files\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Amount", style="yellow")
    table.add_column("Merchant", style="white")
    
    for receipt_path in track(receipts[:20], description="Processing receipts..."):
        data = processor.process_receipt(receipt_path)
        
        date_str = data['date'].strftime('%Y-%m-%d') if data['date'] else 'N/A'
        amount_str = f"${data['amount']:.2f}" if data['amount'] else 'N/A'
        merchant_str = data['merchant'][:30] if data['merchant'] else 'N/A'
        
        table.add_row(
            data['filename'],
            date_str,
            amount_str,
            merchant_str
        )
    
    if len(receipts) > 20:
        table.add_row("...", "...", "...", f"...and {len(receipts) - 20} more files")
    
    console.print(table)
    console.print()


if __name__ == '__main__':
    cli()
