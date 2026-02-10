#!/usr/bin/env python3
"""
Receipt Checker Web Interface

Flask web application for managing receipt matching
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.receipt_processor import ReceiptProcessor
from src.statement_parser import StatementParser

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent.parent
STATEMENTS_FOLDER = BASE_DIR / "data/statements"
RECEIPTS_FOLDER = BASE_DIR / "data/receipts"
OUTPUT_FOLDER = BASE_DIR / "output"
RENAMED_RECEIPTS_FOLDER = BASE_DIR / "output/renamed_receipts"

# Create folders if they don't exist
STATEMENTS_FOLDER.mkdir(parents=True, exist_ok=True)
RECEIPTS_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Allowed file extensions
ALLOWED_STATEMENT_EXTENSIONS = {'csv', 'xlsx', 'xls'}
ALLOWED_RECEIPT_EXTENSIONS = {'pdf'}


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_all_statements():
    """Get list of all statement files"""
    statements = []
    for ext in ALLOWED_STATEMENT_EXTENSIONS:
        statements.extend(list(STATEMENTS_FOLDER.glob(f"*.{ext}")))
    
    # Sort by name
    statements.sort(key=lambda x: x.name)
    
    return [{
        'name': s.name,
        'path': str(s.relative_to(BASE_DIR)),
        'modified': datetime.fromtimestamp(s.stat().st_mtime).isoformat()
    } for s in statements]


def load_statement_data(statement_name=None):
    """Load statement data with match status"""
    if statement_name:
        statement_file = STATEMENTS_FOLDER / statement_name
        output_csv = OUTPUT_FOLDER / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
    else:
        # Try to find a default statement
        statements = list(STATEMENTS_FOLDER.glob("*.csv"))
        if not statements:
            return pd.DataFrame()
        statement_file = statements[0]
        output_csv = OUTPUT_FOLDER / f"{statement_file.stem}_matches.csv"
    
    # Load from output if exists, otherwise from original
    if output_csv.exists():
        df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig')
    else:
        df = pd.read_csv(statement_file, sep=';', encoding='utf-8-sig')
        if 'Matching Receipt Found' not in df.columns:
            df['Matching Receipt Found'] = False
            df['Matched Receipt File'] = ''
            df['Match Confidence'] = 0
        if 'No Receipt Needed' not in df.columns:
            df['No Receipt Needed'] = False
    
    return df


def get_summary_stats(df):
    """Calculate summary statistics"""
    total = int(len(df))
    matched = int(df['Matching Receipt Found'].sum()) if 'Matching Receipt Found' in df.columns else 0
    no_receipt_needed = int(df['No Receipt Needed'].sum()) if 'No Receipt Needed' in df.columns else 0
    completed = matched + no_receipt_needed
    missing = total - completed
    completion_rate = float((completed / total * 100) if total > 0 else 0)
    
    return {
        'total': total,
        'matched': matched,
        'no_receipt_needed': no_receipt_needed,
        'completed': completed,
        'missing': missing,
        'completion_rate': round(completion_rate, 1)
    }


def scan_receipts():
    """Scan receipts folder and return count"""
    receipts = list(RECEIPTS_FOLDER.glob("**/*.pdf"))
    return len(receipts)


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/statements')
def api_statements():
    """Get list of available statements"""
    try:
        statements = get_all_statements()
        return jsonify(statements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/summary')
def api_summary():
    """Get summary statistics"""
    try:
        statement_name = request.args.get('statement')
        df = load_statement_data(statement_name)
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
        statement_name = request.args.get('statement')
        df = load_statement_data(statement_name)
        
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
                'no_receipt_needed': bool(row['No Receipt Needed']) if 'No Receipt Needed' in row else False,
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


@app.route('/api/upload/statement', methods=['POST'])
def upload_statement():
    """Upload a bank statement"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, ALLOWED_STATEMENT_EXTENSIONS):
            return jsonify({'error': 'Invalid file type. Only CSV, XLS, XLSX allowed'}), 400
        
        filename = secure_filename(file.filename)
        filepath = STATEMENTS_FOLDER / filename
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'Statement uploaded: {filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/receipt', methods=['POST'])
def upload_receipt():
    """Upload receipt PDFs"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        uploaded = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if not allowed_file(file.filename, ALLOWED_RECEIPT_EXTENSIONS):
                continue
            
            filename = secure_filename(file.filename)
            filepath = RECEIPTS_FOLDER / filename
            file.save(filepath)
            uploaded.append(filename)
        
        return jsonify({
            'success': True,
            'count': len(uploaded),
            'files': uploaded,
            'message': f'Uploaded {len(uploaded)} receipt(s)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/toggle-no-receipt', methods=['POST'])
def toggle_no_receipt():
    """Toggle 'No Receipt Needed' status for a transaction"""
    try:
        data = request.json
        statement_name = data.get('statement')
        row_index = data.get('row')  # CSV row number (1-indexed with header)
        checked = data.get('checked', False)
        
        if not statement_name or row_index is None:
            return jsonify({'error': 'Missing statement or row'}), 400
        
        # Load the data
        statement_file = STATEMENTS_FOLDER / statement_name
        output_csv = OUTPUT_FOLDER / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        # Load from output if exists, otherwise from original
        if output_csv.exists():
            df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig')
        else:
            df = pd.read_csv(statement_file, sep=';', encoding='utf-8-sig')
            # Add columns if they don't exist
            if 'Matching Receipt Found' not in df.columns:
                df['Matching Receipt Found'] = False
                df['Matched Receipt File'] = ''
                df['Match Confidence'] = 0
            if 'No Receipt Needed' not in df.columns:
                df['No Receipt Needed'] = False
        
        # Ensure column exists
        if 'No Receipt Needed' not in df.columns:
            df['No Receipt Needed'] = False
        
        # Convert row number to dataframe index (row - 2 because of header and 0-index)
        df_index = row_index - 2
        
        if df_index < 0 or df_index >= len(df):
            return jsonify({'error': 'Invalid row index'}), 400
        
        # Update the value
        df.loc[df_index, 'No Receipt Needed'] = checked
        
        # Save to output CSV
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
        
        return jsonify({
            'success': True,
            'row': row_index,
            'checked': checked
        })
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
