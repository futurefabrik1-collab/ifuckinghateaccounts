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
from collections import deque
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.receipt_processor import ReceiptProcessor
from src.statement_parser import StatementParser

app = Flask(__name__)
CORS(app)

# Undo history - store last 50 operations per statement
undo_history = {}  # {statement_name: deque([{operation_data}, ...], maxlen=50)}

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
                    # Skip files ending with _matches.csv or _matches.xlsx or _backup
                    if s.stem.endswith('_matches') or '_backup' in s.stem:
                        continue
                    
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
        # Auto-detect delimiter
        with open(statement_file, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline()
            if first_line.count(';') > first_line.count(','):
                delimiter = ';'
            elif first_line.count(',') > 0:
                delimiter = ','
            elif first_line.count('\t') > 0:
                delimiter = '\t'
            else:
                delimiter = ';'
        
        # Try to read with headers first
        try:
            df = pd.read_csv(statement_file, sep=delimiter, encoding='utf-8-sig')
            
            # Check if it looks like there are no headers (first row contains data)
            # If first column name looks like a date pattern or number, probably no headers
            first_col = str(df.columns[0])
            has_headers = True
            
            # Check if first column looks like data (date pattern or pure numbers)
            if (any(char.isdigit() for char in first_col) and 
                ('.' in first_col or '/' in first_col or first_col.replace('.', '').replace('/', '').isdigit())):
                has_headers = False
            
            if not has_headers:
                # Reload without headers
                df = pd.read_csv(statement_file, sep=delimiter, encoding='utf-8-sig', header=None)
                # Use German column names that the app expects
                if len(df.columns) >= 3:
                    df.columns = ['Buchungstag', 'Verwendungszweck', 'Betrag'] + [f'Col{i}' for i in range(3, len(df.columns))]
                else:
                    df.columns = [f'Col{i}' for i in range(len(df.columns))]
                logger.info(f"No headers detected, assigned columns: {df.columns.tolist()}")
            else:
                # Has headers - map common English names to German if needed
                column_mapping = {
                    'Date': 'Buchungstag',
                    'Description': 'Verwendungszweck', 
                    'Amount': 'Betrag'
                }
                df.rename(columns=column_mapping, inplace=True)
                logger.info(f"Headers detected: {df.columns.tolist()}")
                
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            df = pd.read_csv(statement_file, sep=delimiter, encoding='utf-8-sig', header=None)
            # Use German column names
            if len(df.columns) >= 3:
                df.columns = ['Buchungstag', 'Verwendungszweck', 'Betrag'] + [f'Col{i}' for i in range(3, len(df.columns))]
            else:
                df.columns = [f'Col{i}' for i in range(len(df.columns))]
        
        # Add match status columns if they don't exist
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
                'confidence': int(row['Match Confidence']) if pd.notna(row.get('Match Confidence', 0)) else 0,
                'owner_mark': bool(row['Owner_Mark']) if 'Owner_Mark' in row and pd.notna(row.get('Owner_Mark')) else False,
                'owner_flo': bool(row['Owner_Flo']) if 'Owner_Flo' in row and pd.notna(row.get('Owner_Flo')) else False
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


@app.route('/api/match-receipts', methods=['POST'])
def match_receipts():
    """Run matching process for a statement"""
    try:
        data = request.json
        statement_name = data.get('statement')
        
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        
        if not receipts_folder.exists():
            return jsonify({'error': 'No receipts folder found'}), 400
        
        # Import matching components
        from src.receipt_processor import ReceiptProcessor
        from src.matcher import ReceiptMatcher
        
        # Process receipts
        processor = ReceiptProcessor(str(receipts_folder))
        receipts = processor.process_all_receipts()
        
        # Load statement using StatementParser (to handle German format properly)
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        # Parse statement with proper German format handling
        parser = StatementParser(str(statement_file))
        parsed_df = parser.load_statement(
            date_column='Buchungstag',
            amount_column='Betrag',
            description_column='Verwendungszweck'
        )
        
        # Load original CSV to preserve all columns and match status
        if output_csv.exists():
            original_df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig', dtype={'Matched Receipt File': str})
        else:
            original_df = pd.read_csv(statement_file, sep=';', encoding='utf-8-sig')
            if 'Matching Receipt Found' not in original_df.columns:
                original_df['Matching Receipt Found'] = False
                original_df['Matched Receipt File'] = ''
                original_df['Match Confidence'] = 0
            if 'No Receipt Needed' not in original_df.columns:
                original_df['No Receipt Needed'] = False
        
        # Ensure correct dtypes for match columns
        if 'Matched Receipt File' in original_df.columns:
            original_df['Matched Receipt File'] = original_df['Matched Receipt File'].astype(str).replace('nan', '')
        
        # Get unmatched transactions from parsed data
        unmatched_mask = original_df['Matching Receipt Found'] == False
        unmatched_indices = original_df[unmatched_mask].index.tolist()
        
        # Get parsed transactions for unmatched rows
        transactions = []
        for idx in unmatched_indices:
            transactions.append({
                'original_index': idx,
                'date': parsed_df.loc[idx, 'date'],
                'amount': parsed_df.loc[idx, 'amount'],
                'description': parsed_df.loc[idx, 'description']
            })
        
        # Match
        matcher = ReceiptMatcher()
        results = matcher.match_all_transactions(transactions, receipts)
        
        # Update dataframe
        matched_count = 0
        for result in results:
            if result['matched']:
                transaction = result['transaction']
                original_idx = transaction['original_index']
                receipt = result['receipt']
                
                # IMPORTANT: Rename/move receipt FIRST, then update CSV with new name
                row_num = original_idx + 2  # +2 for header and 0-index
                # Use merchant from receipt if available
                import re
                clean_merchant = receipt.get('merchant', 'Unknown').strip()[:50]
                clean_merchant = re.sub(r'[^\w\s-]', '', clean_merchant)
                
                new_filename = f"{row_num:03d}_{clean_merchant}.pdf"
                original_path = Path(receipt['path'])
                new_path = matched_folder / new_filename
                
                # Move/rename the file
                if original_path.exists():
                    matched_folder.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original_path, new_path)
                    original_path.unlink()  # Remove from receipts folder
                
                # NOW update CSV with the NEW filename
                original_df.loc[original_idx, 'Matching Receipt Found'] = True
                original_df.loc[original_idx, 'Matched Receipt File'] = new_filename  # Use NEW name
                original_df.loc[original_idx, 'Match Confidence'] = result['confidence']
                
                matched_count += 1
        
        # Save updated CSV
        original_df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
        
        return jsonify({
            'success': True,
            'matched': matched_count,
            'total_receipts': len(receipts),
            'message': f'Matched {matched_count} receipt(s)'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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


@app.route('/api/clear-statement', methods=['POST'])
def clear_statement():
    """Clear/reset a statement - remove all matches and move receipts back"""
    try:
        data = request.json
        statement_name = data.get('statement')
        confirm = data.get('confirm', False)
        
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        if not confirm:
            return jsonify({'error': 'Confirmation required'}), 400
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        
        # Move all matched receipts back to receipts folder
        moved_count = 0
        if matched_folder.exists():
            for receipt_file in matched_folder.glob("*.pdf"):
                # Move back to receipts folder
                dest = receipts_folder / receipt_file.name
                shutil.move(str(receipt_file), str(dest))
                moved_count += 1
        
        # Delete the _matches.csv file
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        if output_csv.exists():
            output_csv.unlink()
        
        return jsonify({
            'success': True,
            'receipts_moved': moved_count,
            'message': f'Statement reset: {moved_count} receipts moved back, match data cleared'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/assign-receipt', methods=['POST'])
def assign_receipt():
    """Manually assign a receipt to a transaction row"""
    try:
        # Get the file from the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get parameters
        statement_name = request.form.get('statement')
        row_number = request.form.get('row')
        action = request.form.get('action', 'replace')  # 'replace' or 'restore'
        
        if not statement_name or not row_number:
            return jsonify({'error': 'Missing statement or row number'}), 400
        
        try:
            row_number = int(row_number)
        except ValueError:
            return jsonify({'error': 'Invalid row number'}), 400
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        matched_folder.mkdir(parents=True, exist_ok=True)
        
        # Load statement data
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        if output_csv.exists():
            df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig', dtype={'Matched Receipt File': str})
        else:
            df = pd.read_csv(statement_file, sep=';', encoding='utf-8-sig')
            if 'Matching Receipt Found' not in df.columns:
                df['Matching Receipt Found'] = False
                df['Matched Receipt File'] = ''
                df['Match Confidence'] = 0
            if 'No Receipt Needed' not in df.columns:
                df['No Receipt Needed'] = False
        
        # Convert row number to dataframe index (row - 2 because of header and 0-index)
        df_index = row_number - 2
        
        if df_index < 0 or df_index >= len(df):
            return jsonify({'error': 'Invalid row index'}), 400
        
        # Check if row already has a receipt
        existing_receipt = str(df.loc[df_index, 'Matched Receipt File']) if pd.notna(df.loc[df_index, 'Matched Receipt File']) else ''
        existing_receipt = existing_receipt if existing_receipt != 'nan' else ''
        
        # Handle existing receipt based on action
        if existing_receipt and action == 'restore':
            # Move existing receipt back to receipts folder
            existing_path = matched_folder / existing_receipt
            if existing_path.exists():
                restore_path = receipts_folder / existing_receipt
                shutil.move(str(existing_path), str(restore_path))
        elif existing_receipt:
            # Delete existing receipt (replace action)
            existing_path = matched_folder / existing_receipt
            if existing_path.exists():
                existing_path.unlink()
        
        # Get transaction description for filename
        import re
        description = str(df.loc[df_index, 'Verwendungszweck'])
        
        # Extract merchant name from description
        merchant = description.split('/')[0] if '/' in description else description.split(',')[0]
        merchant = merchant.strip()[:50]
        merchant = re.sub(r'[^\w\s-]', '', merchant).strip()
        merchant = re.sub(r'\s+', '_', merchant)
        
        # Create new filename
        file_ext = Path(file.filename).suffix
        new_filename = f"{row_number:03d}_{merchant}{file_ext}"
        new_path = matched_folder / new_filename
        
        # Save the uploaded file
        file.save(str(new_path))
        
        # Update dataframe
        df.loc[df_index, 'Matching Receipt Found'] = True
        df.loc[df_index, 'Matched Receipt File'] = new_filename
        df.loc[df_index, 'Match Confidence'] = 100  # Manual assignment = 100% confidence
        df.loc[df_index, 'No Receipt Needed'] = False  # Clear "no receipt needed" flag
        
        # Reset ownership buttons to off when receipt is assigned
        if 'Owner_Mark' in df.columns:
            df.loc[df_index, 'Owner_Mark'] = False
        if 'Owner_Flo' in df.columns:
            df.loc[df_index, 'Owner_Flo'] = False
        
        # Save updated CSV
        df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
        
        # Add to undo history
        if statement_name not in undo_history:
            undo_history[statement_name] = deque(maxlen=50)
        
        undo_history[statement_name].append({
            'type': 'assign',
            'row': row_number,
            'new_file': new_filename,
            'old_file': existing_receipt if existing_receipt else None,
            'action': action,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'row': row_number,
            'filename': new_filename,
            'action': action,
            'existing_removed': existing_receipt,
            'message': f'Receipt assigned to row {row_number}',
            'undo_available': len(undo_history[statement_name]) > 0
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/undo', methods=['POST'])
def undo_last_action():
    """Undo the last manual assignment"""
    try:
        data = request.json
        statement_name = data.get('statement')
        
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        # Check if there's any history for this statement
        if statement_name not in undo_history or len(undo_history[statement_name]) == 0:
            return jsonify({'error': 'Nothing to undo'}), 400
        
        # Pop the last action
        last_action = undo_history[statement_name].pop()
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        
        # Load statement data
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        if not output_csv.exists():
            return jsonify({'error': 'No matches file found'}), 400
        
        df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig', dtype={'Matched Receipt File': str})
        
        # Convert row number to dataframe index
        row_number = last_action['row']
        df_index = row_number - 2
        
        if df_index < 0 or df_index >= len(df):
            return jsonify({'error': 'Invalid row index in undo history'}), 400
        
        # Undo based on action type
        if last_action['type'] == 'assign':
            new_file = last_action['new_file']
            old_file = last_action.get('old_file')
            action = last_action.get('action', 'replace')
            
            # Remove the newly assigned file
            new_path = matched_folder / new_file
            if new_path.exists():
                # Move back to receipts folder instead of deleting
                restore_path = receipts_folder / new_file
                shutil.move(str(new_path), str(restore_path))
            
            # Restore the old file if it was moved (restore action)
            if old_file and action == 'restore':
                # The old file should be in receipts folder, move it back to matched
                old_receipts_path = receipts_folder / old_file
                old_matched_path = matched_folder / old_file
                if old_receipts_path.exists():
                    shutil.move(str(old_receipts_path), str(old_matched_path))
                    # Update CSV to reflect old file
                    df.loc[df_index, 'Matching Receipt Found'] = True
                    df.loc[df_index, 'Matched Receipt File'] = old_file
                    df.loc[df_index, 'Match Confidence'] = 100
                else:
                    # Old file not found, just clear the match
                    df.loc[df_index, 'Matching Receipt Found'] = False
                    df.loc[df_index, 'Matched Receipt File'] = ''
                    df.loc[df_index, 'Match Confidence'] = 0
            else:
                # No old file or it was deleted (replace action)
                # Just clear the match
                df.loc[df_index, 'Matching Receipt Found'] = False
                df.loc[df_index, 'Matched Receipt File'] = ''
                df.loc[df_index, 'Match Confidence'] = 0
            
            # Save updated CSV
            df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
            
            return jsonify({
                'success': True,
                'message': f'Undid assignment for row {row_number}',
                'row': row_number,
                'undo_available': len(undo_history[statement_name]) > 0
            })
        
        return jsonify({'error': 'Unknown action type'}), 400
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/set-ownership', methods=['POST'])
def set_ownership():
    """Set ownership for a transaction (Mark and/or Flo - independent toggles)"""
    try:
        data = request.json
        statement_name = data.get('statement')
        row_number = data.get('row')
        owner = data.get('owner')  # 'mark' or 'flo'
        active = data.get('active', True)  # True or False
        
        if not statement_name or not row_number or not owner:
            return jsonify({'error': 'Missing statement, row number, or owner'}), 400
        
        try:
            row_number = int(row_number)
        except ValueError:
            return jsonify({'error': 'Invalid row number'}), 400
        
        # Validate owner value
        if owner not in ['mark', 'flo']:
            return jsonify({'error': 'Invalid owner value'}), 400
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        # Load or create matches CSV
        if output_csv.exists():
            df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig', dtype={'Matched Receipt File': str})
        else:
            df = pd.read_csv(statement_file, sep=';', encoding='utf-8-sig')
            if 'Matching Receipt Found' not in df.columns:
                df['Matching Receipt Found'] = False
                df['Matched Receipt File'] = ''
                df['Match Confidence'] = 0
            if 'No Receipt Needed' not in df.columns:
                df['No Receipt Needed'] = False
        
        # Add owner columns if they don't exist
        if 'Owner_Mark' not in df.columns:
            df['Owner_Mark'] = False
        if 'Owner_Flo' not in df.columns:
            df['Owner_Flo'] = False
        
        # Convert row number to dataframe index
        df_index = row_number - 2
        
        if df_index < 0 or df_index >= len(df):
            return jsonify({'error': 'Invalid row index'}), 400
        
        # Update ownership
        if owner == 'mark':
            df.loc[df_index, 'Owner_Mark'] = active
        elif owner == 'flo':
            df.loc[df_index, 'Owner_Flo'] = active
        
        # Auto-activate "No Receipt Needed" when either Mark or Flo is active
        mark_active = bool(df.loc[df_index, 'Owner_Mark'])
        flo_active = bool(df.loc[df_index, 'Owner_Flo'])
        
        if mark_active or flo_active:
            df.loc[df_index, 'No Receipt Needed'] = True
        # When both are deactivated, keep "No Receipt Needed" (persistent behavior)
        
        # Save updated CSV
        df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
        
        return jsonify({
            'success': True,
            'row': row_number,
            'owner': owner,
            'active': active
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-receipt-assignment', methods=['POST'])
def delete_receipt_assignment():
    """Delete a receipt assignment and move file back to receipts folder with random prefix"""
    try:
        data = request.json
        statement_name = data.get('statement')
        row_number = data.get('row')
        filename = data.get('filename')
        
        if not statement_name or not row_number or not filename:
            return jsonify({'error': 'Missing statement, row number, or filename'}), 400
        
        try:
            row_number = int(row_number)
        except ValueError:
            return jsonify({'error': 'Invalid row number'}), 400
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        receipts_folder = get_statement_receipts_folder(statement_name, 'receipts')
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        
        # Load statement data
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        if not output_csv.exists():
            return jsonify({'error': 'No matches file found'}), 400
        
        df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig', dtype={'Matched Receipt File': str})
        
        # Convert row number to dataframe index
        df_index = row_number - 2
        
        if df_index < 0 or df_index >= len(df):
            return jsonify({'error': 'Invalid row index'}), 400
        
        # Move file back to receipts folder with random prefix
        import random
        import string
        
        matched_file_path = matched_folder / filename
        if matched_file_path.exists():
            # Generate random 6-character prefix
            random_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            new_filename = f"{random_prefix}_{filename}"
            new_path = receipts_folder / new_filename
            
            # Move file
            shutil.move(str(matched_file_path), str(new_path))
        else:
            return jsonify({'error': 'Receipt file not found'}), 404
        
        # Clear match in CSV
        df.loc[df_index, 'Matching Receipt Found'] = False
        df.loc[df_index, 'Matched Receipt File'] = ''
        df.loc[df_index, 'Match Confidence'] = 0
        # Note: We keep "No Receipt Needed" and ownership settings as they were
        
        # Save updated CSV
        df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
        
        return jsonify({
            'success': True,
            'row': row_number,
            'old_filename': filename,
            'new_filename': new_filename,
            'message': f'Receipt removed and moved to receipts folder as {new_filename}'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/undo-history', methods=['GET'])
def get_undo_history():
    """Get undo history for a statement"""
    try:
        statement_name = request.args.get('statement')
        
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        history = []
        if statement_name in undo_history:
            history = list(undo_history[statement_name])
        
        return jsonify({
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update-learning', methods=['POST'])
def update_learning():
    """Update learning model using all matched receipts from a statement"""
    try:
        data = request.json
        statement_name = data.get('statement')
        
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        # Get folders
        statement_folder = get_statement_folder(statement_name)
        matched_folder = get_statement_receipts_folder(statement_name, 'matched_receipts')
        
        if not matched_folder.exists():
            return jsonify({'error': 'No matched receipts found'}), 400
        
        # Load statement data
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        if not output_csv.exists():
            return jsonify({'error': 'No matches file found'}), 400
        
        df = pd.read_csv(output_csv, sep=';', encoding='utf-8-sig', dtype={'Matched Receipt File': str})
        
        # Get all matched receipts
        matched_receipts = []
        for idx, row in df.iterrows():
            if row.get('Matching Receipt Found', False):
                receipt_file = str(row.get('Matched Receipt File', ''))
                if receipt_file and receipt_file != 'nan' and receipt_file != '':
                    matched_receipts.append({
                        'file': receipt_file,
                        'date': row['Buchungstag'],
                        'amount': row['Betrag'],
                        'description': row['Verwendungszweck']
                    })
        
        if len(matched_receipts) == 0:
            return jsonify({'error': 'No matched receipts to learn from'}), 400
        
        # Process each matched receipt to extract features for learning
        from src.receipt_processor import ReceiptProcessor
        
        processor = ReceiptProcessor(str(matched_folder))
        learning_data = []
        
        for receipt in matched_receipts:
            receipt_path = matched_folder / receipt['file']
            if receipt_path.exists():
                try:
                    # Extract receipt data
                    receipt_data = processor.process_receipt(receipt_path)
                    
                    # Store the match for learning
                    learning_data.append({
                        'receipt_file': receipt['file'],
                        'receipt_amount': receipt_data.get('amount'),
                        'receipt_date': receipt_data.get('date'),
                        'receipt_merchant': receipt_data.get('merchant'),
                        'transaction_amount': receipt['amount'],
                        'transaction_date': receipt['date'],
                        'transaction_description': receipt['description']
                    })
                except Exception as e:
                    print(f"Error processing {receipt['file']}: {e}")
                    continue
        
        # Save learning data to a training file
        learning_file = statement_folder / 'learning_data.json'
        import json
        
        # Load existing learning data if it exists
        if learning_file.exists():
            with open(learning_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        # Append new learning data
        existing_data.extend(learning_data)
        
        # Save updated learning data
        with open(learning_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False, default=str)
        
        return jsonify({
            'success': True,
            'receipts_processed': len(learning_data),
            'total_learning_samples': len(existing_data),
            'message': f'Learning model updated with {len(learning_data)} receipts'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-statement', methods=['POST'])
def delete_statement():
    """Delete a statement and all associated data"""
    try:
        data = request.json
        statement_name = data.get('statement')
        confirm = data.get('confirm', False)
        
        if not statement_name:
            return jsonify({'error': 'No statement specified'}), 400
        
        if not confirm:
            return jsonify({'error': 'Confirmation required'}), 400
        
        # Get statement folder
        statement_folder = get_statement_folder(statement_name)
        
        if not statement_folder.exists():
            return jsonify({'error': 'Statement not found'}), 404
        
        # Count items before deletion for reporting
        receipts_count = len(list(statement_folder.glob("receipts/*.pdf")))
        matched_count = len(list(statement_folder.glob("matched_receipts/*.pdf")))
        
        # Delete the entire statement folder
        shutil.rmtree(statement_folder)
        
        return jsonify({
            'success': True,
            'message': f'Statement deleted: {statement_name}',
            'receipts_deleted': receipts_count,
            'matched_deleted': matched_count
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    """Open a folder in the system file manager"""
    try:
        data = request.get_json()
        folder_path = data.get('path')
        
        if not folder_path:
            return jsonify({'error': 'No path provided'}), 400
        
        # Make path absolute
        if not os.path.isabs(folder_path):
            folder_path = os.path.join(os.path.dirname(__file__), '..', folder_path)
        
        folder_path = os.path.abspath(folder_path)
        
        if not os.path.exists(folder_path):
            return jsonify({'error': f'Folder does not exist: {folder_path}'}), 404
        
        # Open folder based on OS
        import platform
        import subprocess
        
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', folder_path])
        elif system == 'Windows':
            subprocess.Popen(['explorer', folder_path])
        else:  # Linux
            subprocess.Popen(['xdg-open', folder_path])
        
        return jsonify({'success': True, 'message': f'Opened folder: {os.path.basename(folder_path)}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/learned-urls', methods=['GET'])
def get_learned_urls():
    """Get learned merchant URLs from file"""
    try:
        urls_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'learned_urls.json')
        if os.path.exists(urls_file):
            with open(urls_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/learned-urls', methods=['POST'])
def save_learned_urls():
    """Save learned merchant URLs to file"""
    try:
        data = request.get_json()
        urls_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'learned_urls.json')
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(urls_file), exist_ok=True)
        
        with open(urls_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({'success': True, 'message': f'Saved {len(data)} learned URLs'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
