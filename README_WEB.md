# Web Interface - Receipt Checker Dashboard

Beautiful web dashboard for viewing and managing receipt matching status.

## Overview

The web interface provides a clean, modern dashboard for:
- Viewing summary statistics
- Browsing all transactions with match status
- Filtering matched/unmatched transactions
- Viewing receipts in folder
- Viewing renamed receipts
- Downloading receipt files

## Quick Start

### Start the Web Server

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
cd web
python app.py
```

### Access the Dashboard

Open in your browser:
```
http://localhost:5001
```

### Stop the Server

Press **Ctrl+C** in the terminal where the server is running.

## Features

### 📊 Dashboard Overview

**Summary Statistics:**
- Total Transactions
- Matched Count (green)
- Unmatched Count (red)
- Match Rate Percentage (purple)

**Auto-refresh:** Statistics refresh every 10 seconds

### 📋 Transaction Views

**Tabs:**
1. **All Transactions** - Shows complete bank statement
2. **Matched Only** - Shows only transactions with receipts
3. **Unmatched Only** - Shows transactions needing receipts
4. **Receipts in Folder** - Browse unprocessed receipts
5. **Renamed Receipts** - Browse matched and renamed receipts

**Table Columns:**
- Row number
- Date
- Amount (red = debit, green = credit)
- Description (truncated to fit)
- Status (✓ Matched badge or ✗ No Receipt badge)
- Receipt filename

### 📁 File Management

**Receipts in Folder:**
- View all PDFs in `data/receipts/`
- See file size and modified date
- Download individual receipts

**Renamed Receipts:**
- View all renamed receipts in `output/renamed_receipts/`
- Files sorted by row number
- Download matched receipts

## API Endpoints

The web app provides a REST API:

### GET /api/summary
Get summary statistics

**Response:**
```json
{
    "total": 54,
    "matched": 5,
    "unmatched": 49,
    "match_rate": 9.3,
    "receipts_in_folder": 14,
    "receipts_renamed": 5
}
```

### GET /api/transactions?filter={all|matched|unmatched}
Get transactions list

**Parameters:**
- `filter` (optional): `all`, `matched`, or `unmatched`

**Response:**
```json
[
    {
        "row": 5,
        "date": "28.01.2026",
        "amount": "-9,62",
        "description": "Google...",
        "matched": true,
        "receipt": "Receipt.pdf",
        "confidence": 72
    }
]
```

### GET /api/receipts
Get list of receipts in folder

**Response:**
```json
[
    {
        "name": "Receipt.pdf",
        "size": 123456,
        "modified": "2026-02-09T12:00:00",
        "path": "data/receipts/Receipt.pdf"
    }
]
```

### GET /api/renamed-receipts
Get list of renamed receipts

### GET /api/download/{filepath}
Download a receipt file

## Integration with Other Tools

### Run Monitor in Background, View in Browser

**Terminal 1:**
```bash
python monitor_receipts.py
```

**Terminal 2:**
```bash
cd web
python app.py
```

**Browser:**
Open `http://localhost:5001` and watch updates in real-time

### Process Receipts, View Results

```bash
# Process receipts
python match_and_rename.py

# Start web interface
cd web
python app.py

# View results in browser
```

## Configuration

### Change Port

Edit `web/app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)  # Change port
```

### Change Data Source

Edit `web/app.py`:
```python
STATEMENT_FILE = BASE_DIR / "data/statements/YOUR_FILE.csv"
```

## Running as Background Service

### Mac/Linux

```bash
# Start in background
cd web
nohup python app.py > web.log 2>&1 &

# Check if running
ps aux | grep app.py

# View logs
tail -f web.log

# Stop
pkill -f app.py
```

### Keep Running After Terminal Closes

```bash
# Use screen
screen -S receipt-web
cd web
python app.py

# Detach: Ctrl+A then D
# Reattach: screen -r receipt-web
```

## Browser Compatibility

- ✅ Chrome/Edge (recommended)
- ✅ Safari
- ✅ Firefox
- ✅ Any modern browser

## Mobile Friendly

The interface is responsive and works on:
- Desktop
- Tablet
- Mobile phones

## Security

**Development Mode:**
- Accessible only on local network
- Debug mode enabled
- Not suitable for production

**For Production:**
- Set `debug=False`
- Use proper WSGI server (gunicorn, uwsgi)
- Add authentication
- Use HTTPS

## Customization

### Change Theme Colors

Edit `web/templates/index.html` CSS:
```css
.stat-value.matched { color: #34c759; }  /* Change green */
.stat-value.unmatched { color: #ff3b30; }  /* Change red */
```

### Add New Features

The Flask app is modular:
1. Add new route in `app.py`
2. Add new section in `index.html`
3. Add JavaScript to fetch and display data

## Troubleshooting

### Port already in use

**Error:** `Address already in use`

**Fix:** Change port or stop other service:
```bash
# Find what's using the port
lsof -i :5001

# Stop the process
kill <PID>

# Or use different port
```

### Can't connect to server

**Check:**
1. Server is running: `ps aux | grep app.py`
2. Using correct URL: `http://localhost:5001`
3. Firewall not blocking

### Data not showing

**Check:**
1. CSV files exist
2. Paths in `app.py` are correct
3. Check browser console for errors (F12)

### Auto-refresh not working

**Fix:** Refresh page manually or check browser console for JavaScript errors

## Development

### File Structure

```
web/
├── app.py              # Flask backend
├── templates/
│   └── index.html      # Frontend HTML/CSS/JS
└── static/             # (optional) Static assets
```

### Add New API Endpoint

```python
@app.route('/api/your-endpoint')
def your_endpoint():
    try:
        # Your logic here
        data = {'result': 'success'}
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Add New Frontend Feature

Edit `index.html`:
1. Add HTML markup
2. Add CSS styling
3. Add JavaScript to fetch and display data

## Performance

- **Load time**: < 1 second
- **API response**: < 500ms
- **Auto-refresh**: Every 10 seconds
- **Concurrent users**: Suitable for single user (dev mode)

## Advantages over CLI

| Feature | CLI | Web Interface |
|---------|-----|---------------|
| Visual | Text table | Color-coded dashboard |
| Updates | Manual refresh | Auto-refresh |
| Filtering | Command line args | Click tabs |
| File access | Terminal commands | Click to download |
| Sharing | Send text output | Share URL |
| Mobile | Not practical | Fully responsive |

## Future Enhancements

Potential features to add:
- [ ] Upload receipts via web
- [ ] Manual matching interface
- [ ] Edit transaction details
- [ ] Export to PDF/Excel
- [ ] Email notifications
- [ ] Multi-user support
- [ ] Authentication
- [ ] Dark mode

## See Also

- `view_progress.py` - CLI progress viewer
- `match_and_rename.py` - Batch matching
- `monitor_receipts.py` - Auto-monitoring
- `README.md` - Main documentation
