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
STATEMENTS_BASE_FOLDER = BASE_DIR / "statements"

# Create base folder
STATEMENTS_BASE_FOLDER.mkdir(parents=True, exist_ok=True)

# Allowed file extensions
ALLOWED_STATEMENT_EXTENSIONS = {'csv', 'xlsx', 'xls'}
ALLOWED_RECEIPT_EXTENSIONS = {'pdf'}


def get_statement_folder(statement_name):
    """Get the folder path for a specific statement"""
    # Remove extension for folder name
    folder_name = statement_name.rsplit('.', 1)[0]
    return STATEMENTS_BASE_FOLDER / folder_name


def get_statement_receipts_folder(statement_name, subfolder='receipts'):
    """Get receipts subfolder for a statement"""
    return get_statement_folder(statement_name) / subfolder


def create_statement_folders(statement_name):
    """Create all necessary folders for a statement"""
    statement_folder = get_statement_folder(statement_name)
    receipts_folder = statement_folder / 'receipts'
    matched_folder = statement_folder / 'matched_receipts'
    
    statement_folder.mkdir(parents=True, exist_ok=True)
    receipts_folder.mkdir(parents=True, exist_ok=True)
    matched_folder.mkdir(parents=True, exist_ok=True)
    
    return {
        'base': statement_folder,
        'receipts': receipts_folder,
        'matched': matched_folder
    }


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_all_statements():
    """Get list of all statement folders"""
    statements = []
    
    # Look for statement CSV files in subfolders
    for folder in STATEMENTS_BASE_FOLDER.iterdir():
        if folder.is_dir():
            # Look for CSV/Excel files in the folder
            for ext in ALLOWED_STATEMENT_EXTENSIONS:
                statement_files = list(folder.glob(f"*.{ext}"))
                for s in statement_files:
                    statements.append({
                        'name': s.name,
                        'folder': folder.name,
                        'path': str(s.relative_to(BASE_DIR)),
                        'modified': datetime.fromtimestamp(s.stat().st_mtime).isoformat(),
                        'receipts_folder': str((folder / 'receipts').relative_to(BASE_DIR)),
                        'matched_folder': str((folder / 'matched_receipts').relative_to(BASE_DIR))
                    })
    
    # Sort by name
    statements.sort(key=lambda x: x['name'])
    
    return statements


def load_statement_data(statement_name=None):
    """Load statement data with match status"""
    if not statement_name:
        # Try to find first available statement
        all_statements = get_all_statements()
        if not all_statements:
            return pd.DataFrame()
        statement_name = all_statements[0]['name']
    
    # Find the statement file in its folder
    statement_folder = get_statement_folder(statement_name)
    statement_file = statement_folder / statement_name
    output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
    
    if not statement_file.exists():
        return pd.DataFrame()
    
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


def scan_receipts(statement_name=None):
    """Scan receipts folder for a specific statement"""
    if not statement_name:
        return 0
    
    receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
    if not receipts_folder.exists():
        return 0
    
    receipts = list(receipts_folder.glob("*.pdf"))
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
        
        # Add receipt counts for this statement
        if statement_name:
            stats['receipts_in_folder'] = scan_receipts(statement_name)
            matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
            stats['receipts_renamed'] = len(list(matched_folder.glob("*.pdf"))) if matched_folder.exists() else 0
        else:
            stats['receipts_in_folder'] = 0
            stats['receipts_renamed'] = 0
        
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
    """Get list of receipts for a specific statement"""
    try:
        statement_name = request.args.get('statement')
        if not statement_name:
            return jsonify([])
        
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        if not receipts_folder.exists():
            return jsonify([])
        
        receipts = list(receipts_folder.glob("*.pdf"))
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
    """Get list of matched/renamed receipts for a specific statement"""
    try:
        statement_name = request.args.get('statement')
        if not statement_name:
            return jsonify([])
        
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        if not matched_folder.exists():
            return jsonify([])
        
        receipts = list(matched_folder.glob("*.pdf"))
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
        
        # Create folders for this statement
        folders = create_statement_folders(filename)
        
        # Save statement file to its folder
        filepath = folders['base'] / filename
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'Statement uploaded: {filename}',
            'folders': {
                'receipts': str(folders['receipts'].relative_to(BASE_DIR)),
                'matched': str(folders['matched'].relative_to(BASE_DIR))
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/receipt', methods=['POST'])
def upload_receipt():
    """Upload receipt PDFs to a specific statement's folder"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        # Get which statement these receipts are for
        statement_name = request.form.get('statement')
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        files = request.files.getlist('files')
        uploaded = []
        
        # Get receipts folder for this statement
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        receipts_folder.mkdir(parents=True, exist_ok=True)
        
        for file in files:
            if file.filename == '':
                continue
            
            if not allowed_file(file.filename, ALLOWED_RECEIPT_EXTENSIONS):
                continue
            
            filename = secure_filename(file.filename)
            filepath = receipts_folder / filename
            file.save(filepath)
            uploaded.append(filename)
        
        return jsonify({
            'success': True,
            'count': len(uploaded),
            'files': uploaded,
            'message': f'Uploaded {len(uploaded)} receipt(s) to {statement_name}'
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
        statement_folder = get_statement_folder(statement_name)
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
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
