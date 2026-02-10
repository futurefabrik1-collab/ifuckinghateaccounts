#!/usr/bin/env python3
"""
Receipt Checker Web Interface

Flask web application for managing receipt matching
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.receipt_processor import ReceiptProcessor
from src.statement_parser import StatementParser

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent.parent
STATEMENT_FILE = BASE_DIR / "data/statements/Umsatzanzeige Jan 31 2026.csv"
OUTPUT_CSV = BASE_DIR / "output/statement_with_matches.csv"
RECEIPTS_FOLDER = BASE_DIR / "data/receipts"
RENAMED_RECEIPTS_FOLDER = BASE_DIR / "output/renamed_receipts"


def load_statement_data():
    """Load statement data with match status"""
    if OUTPUT_CSV.exists():
        df = pd.read_csv(OUTPUT_CSV, sep=';', encoding='utf-8-sig')
    else:
        df = pd.read_csv(STATEMENT_FILE, sep=';', encoding='utf-8-sig')
        if 'Matching Receipt Found' not in df.columns:
            df['Matching Receipt Found'] = False
            df['Matched Receipt File'] = ''
            df['Match Confidence'] = 0
    
    return df


def get_summary_stats(df):
    """Calculate summary statistics"""
    total = int(len(df))
    matched = int(df['Matching Receipt Found'].sum()) if 'Matching Receipt Found' in df.columns else 0
    unmatched = int(total - matched)
    match_rate = float((matched / total * 100) if total > 0 else 0)
    
    return {
        'total': total,
        'matched': matched,
        'unmatched': unmatched,
        'match_rate': round(match_rate, 1)
    }


def scan_receipts():
    """Scan receipts folder and return count"""
    receipts = list(RECEIPTS_FOLDER.glob("**/*.pdf"))
    return len(receipts)


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/summary')
def api_summary():
    """Get summary statistics"""
    try:
        df = load_statement_data()
        stats = get_summary_stats(df)
        
        # Add receipt counts
        stats['receipts_in_folder'] = scan_receipts()
        renamed_count = len(list(RENAMED_RECEIPTS_FOLDER.glob("*.pdf"))) if RENAMED_RECEIPTS_FOLDER.exists() else 0
        stats['receipts_renamed'] = renamed_count
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transactions')
def api_transactions():
    """Get all transactions"""
    try:
        df = load_statement_data()
        
        # Get filter from query params
        filter_type = request.args.get('filter', 'all')
        
        if filter_type == 'matched':
            df = df[df['Matching Receipt Found'] == True]
        elif filter_type == 'unmatched':
            df = df[df['Matching Receipt Found'] == False]
        
        # Convert to list of dicts
        transactions = []
        for idx, row in df.iterrows():
            transactions.append({
                'row': idx + 2,  # +2 for header and 0-index
                'date': row['Buchungstag'],
                'amount': str(row['Betrag']),
                'description': str(row['Verwendungszweck'])[:100],
                'matched': bool(row['Matching Receipt Found']) if 'Matching Receipt Found' in row else False,
                'receipt': str(row['Matched Receipt File']) if pd.notna(row.get('Matched Receipt File', '')) else '',
                'confidence': int(row['Match Confidence']) if pd.notna(row.get('Match Confidence', 0)) else 0
            })
        
        return jsonify(transactions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/receipts')
def api_receipts():
    """Get list of receipts in folder"""
    try:
        receipts = list(RECEIPTS_FOLDER.glob("**/*.pdf"))
        receipt_list = []
        
        for receipt in receipts:
            stat = receipt.stat()
            receipt_list.append({
                'name': receipt.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(receipt.relative_to(BASE_DIR))
            })
        
        # Sort by modified date (newest first)
        receipt_list.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify(receipt_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/renamed-receipts')
def api_renamed_receipts():
    """Get list of renamed receipts"""
    try:
        if not RENAMED_RECEIPTS_FOLDER.exists():
            return jsonify([])
        
        receipts = list(RENAMED_RECEIPTS_FOLDER.glob("*.pdf"))
        receipt_list = []
        
        for receipt in receipts:
            stat = receipt.stat()
            receipt_list.append({
                'name': receipt.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(receipt.relative_to(BASE_DIR))
            })
        
        # Sort by name (row number)
        receipt_list.sort(key=lambda x: x['name'])
        
        return jsonify(receipt_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<path:filepath>')
def download_file(filepath):
    """Download a file"""
    try:
        file_path = BASE_DIR / filepath
        if file_path.exists() and file_path.is_file():
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
