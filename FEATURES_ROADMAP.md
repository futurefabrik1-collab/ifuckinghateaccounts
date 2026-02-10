# Receipt Checker - Feature Roadmap

**Version**: 3.1.0+  
**Last Updated**: February 10, 2026

This document outlines potential new features for future development, organized by priority.

---

## 🎯 Priority 1: Essential Features (Ready to Implement)

### 1. **Web Layer Refactoring** 
**Status**: Design complete, implementation needed  
**Effort**: Medium (2-3 hours)

**Tasks**:
- [ ] Update `web/app.py` to use `StatementService`
- [ ] Replace manual CSV loading with service methods
- [ ] Add security validation to all endpoints
- [ ] Integrate backup system on all writes
- [ ] Use persistent undo manager

**Benefits**:
- Cleaner, more maintainable code
- Automatic backups and security
- Consistent error handling

---

### 2. **Health Check API Endpoint**
**Status**: Utilities ready, endpoint needed  
**Effort**: Small (30 minutes)

**Implementation**:
```python
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    from src.utils.monitoring import get_health_status, get_uptime
    
    health = get_health_status()
    health['uptime'] = get_uptime()
    health['version'] = '3.1.0'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code
```

**Benefits**:
- Production monitoring
- Load balancer health checks
- Early warning for issues

---

### 3. **Rate Limiting**
**Status**: Ready to implement  
**Effort**: Small (1 hour)

**Implementation**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/match-receipts', methods=['POST'])
@limiter.limit("10 per minute")
def match_receipts():
    # Expensive operation - limit requests
    pass
```

**Benefits**:
- Prevent abuse
- Protect server resources
- Better performance for legitimate users

---

### 4. **Integrate OCR Caching**
**Status**: Cache ready, integration needed  
**Effort**: Medium (1-2 hours)

**Implementation**:
```python
# In src/receipt_processor.py
from src.utils.ocr_cache import OCRCache

class ReceiptProcessor:
    def __init__(self, receipts_folder: str):
        self.receipts_folder = Path(receipts_folder)
        self.cache = OCRCache()
    
    def extract_text(self, file_path: Path) -> str:
        # Try cache first
        cached = self.cache.get(file_path)
        if cached:
            return cached['text']
        
        # Extract text (slow)
        text = self._extract_text_internal(file_path)
        
        # Cache result
        self.cache.set(file_path, {'text': text})
        
        return text
```

**Benefits**:
- 50-100x faster receipt processing
- Reduced server load
- Better user experience

---

## 🚀 Priority 2: Enhanced Matching

### 5. **Machine Learning Auto-Matching**
**Effort**: Large (1-2 days)

**Concept**:
- Train model on matched receipt patterns
- Use features: amount diff, merchant score, date proximity
- Auto-improve matching over time

**Implementation Outline**:
```python
from sklearn.ensemble import RandomForestClassifier

class MLMatcher:
    def train(self, learning_data):
        features = [
            [d['amount_diff'], d['merchant_score'], d['days_diff']]
            for d in learning_data
        ]
        labels = [1] * len(features)  # All positive matches
        
        self.model = RandomForestClassifier()
        self.model.fit(features, labels)
    
    def predict_match_probability(self, transaction, receipt):
        features = self.extract_features(transaction, receipt)
        return self.model.predict_proba([features])[0][1]
```

**Benefits**:
- Higher automatic match rates (current: ~70%, target: ~85%)
- Learns from user corrections
- Adapts to specific use patterns

---

### 6. **Duplicate Receipt Detection**
**Effort**: Medium (2-3 hours)

**Features**:
- Detect receipts with same amount, date, merchant
- Flag potential duplicates before matching
- Allow merging/deletion of duplicates

**Benefits**:
- Prevent duplicate expense claims
- Cleaner receipt folder
- Better matching accuracy

---

### 7. **Real-Time Exchange Rates**
**Effort**: Medium (2-3 hours)

**API Integration**:
```python
import requests

class ExchangeRateService:
    def get_rate(self, from_currency, to_currency, date):
        """Get historical exchange rate"""
        response = requests.get(
            f'https://api.exchangerate.host/{date}',
            params={'base': from_currency, 'symbols': to_currency}
        )
        return response.json()['rates'][to_currency]
```

**Benefits**:
- More accurate currency matching
- Historical rate accuracy
- Support for more currencies

---

## 💼 Priority 3: Productivity Features

### 8. **Email Receipt Import**
**Effort**: Large (1 day)

**Features**:
- Connect to Gmail/Outlook via IMAP
- Auto-fetch PDF receipts from emails
- Parse email metadata (sender, date)
- Auto-categorize by sender

**Use Case**:
Many receipts arrive by email (online purchases, subscriptions). Auto-import saves manual downloading.

---

### 9. **Receipt Categories & Tags**
**Effort**: Medium (4-6 hours)

**Database Schema**:
```python
class Transaction:
    category: str  # "Office Supplies", "Travel", "Meals"
    tags: List[str]  # ["tax-deductible", "client-ABC", "project-X"]
    notes: str
```

**Features**:
- Dropdown category selection
- Tag autocomplete
- Filter/search by category
- Monthly category reports

---

### 10. **Monthly Reporting Dashboard**
**Effort**: Large (1-2 days)

**Reports**:
- Total expenses by month
- Category breakdown (pie chart)
- Mark vs Flo expenses
- Match rate trends
- Top merchants
- Export to PDF/Excel

**Implementation**:
```python
def generate_monthly_report(statement_name):
    df = load_statement_csv(statement_name)
    
    return {
        'total': df['amount'].sum(),
        'by_category': df.groupby('category')['amount'].sum(),
        'by_owner': {
            'mark': df[df['owner_mark']]['amount'].sum(),
            'flo': df[df['owner_flo']]['amount'].sum()
        },
        'match_rate': df['matched'].sum() / len(df) * 100
    }
```

---

### 11. **Bulk Operations**
**Effort**: Small (2-3 hours)

**Features**:
- Select multiple transactions (checkboxes)
- Bulk mark as "No Receipt Needed"
- Bulk assign owner (Mark/Flo)
- Bulk delete assignments
- Bulk export selected

**UI Changes**:
```javascript
// Add checkbox column
// Add "Select All" header checkbox
// Show action bar when items selected
// Execute bulk API calls
```

---

### 12. **Advanced Search & Filters**
**Effort**: Medium (3-4 hours)

**Features**:
- Search by merchant name
- Filter by date range
- Filter by amount range
- Filter by match status
- Filter by owner
- Filter by category
- Saved filter presets

---

## 🔗 Priority 4: Integration Features

### 13. **Cloud Storage Sync**
**Effort**: Large (2 days)

**Integrations**:
- Dropbox
- Google Drive
- OneDrive

**Features**:
- Auto-backup receipts to cloud
- Sync across devices
- Share statements with collaborators
- Access from mobile

---

### 14. **Accounting Software Export**
**Effort**: Large (1-2 days)

**Formats**:
- QuickBooks CSV
- Xero format
- DATEV (German accounting standard)
- Generic CSV with mapping

**Implementation**:
```python
def export_to_quickbooks(statement_name):
    df = load_statement_csv(statement_name)
    
    # Map to QuickBooks columns
    qb_df = pd.DataFrame({
        'Date': df['date'].dt.strftime('%m/%d/%Y'),
        'Description': df['description'],
        'Amount': df['amount'].abs(),
        'Account': df['category'],
        'Vendor': df['merchant'],
        'Receipt': df['matched_receipt']
    })
    
    return qb_df
```

---

### 15. **Mobile App API**
**Effort**: Large (3-5 days)

**Features**:
- Mobile-optimized API endpoints
- Photo upload from phone camera
- Push notifications
- Offline support
- Quick scan & upload

**API Design**:
```python
@app.route('/api/mobile/upload-receipt', methods=['POST'])
def mobile_upload_receipt():
    """
    Upload receipt from mobile
    Auto-detect which statement (by date)
    Return match suggestions
    """
    photo = request.files['photo']
    
    # Process immediately
    receipt_data = process_receipt(photo)
    
    # Auto-match to latest statement
    suggestions = find_match_suggestions(receipt_data)
    
    return jsonify({
        'receipt_id': receipt_id,
        'suggestions': suggestions
    })
```

---

### 16. **Webhook Notifications**
**Effort**: Medium (3-4 hours)

**Events**:
- Statement uploaded
- Matching completed
- Low match rate detected
- Duplicate receipt found
- Weekly summary

**Integrations**:
- Email
- Slack
- Discord
- SMS (Twilio)

---

## 🎨 Priority 5: UX Improvements

### 17. **Loading States & Progress**
**Effort**: Small (2-3 hours)

**Features**:
- Spinner during OCR processing
- Progress bar for batch matching
- Estimated time remaining
- Background job status
- Success/error toasts

---

### 18. **Drag-and-Drop Enhancements**
**Effort**: Medium (3-4 hours)

**Features**:
- Visual preview on hover
- Drop zone highlighting
- Multi-file drag
- Drag from matched back to unmatched
- Undo after drag-drop

---

### 19. **Keyboard Navigation**
**Effort**: Small (2 hours)

**Shortcuts**:
- `↑/↓` - Navigate transactions
- `Space` - Preview receipt
- `M` - Mark as Mark's
- `F` - Mark as Flo's
- `N` - Toggle "No Receipt Needed"
- `Delete` - Remove receipt
- `Ctrl+Z` - Undo
- `Ctrl+Shift+Z` - Redo

---

### 20. **Dark Mode**
**Effort**: Small (1-2 hours)

**Implementation**:
- CSS variables for colors
- Toggle switch
- Save preference in localStorage
- System preference detection

---

## 🔬 Priority 6: Advanced Features

### 21. **Multi-User Authentication**
**Effort**: Large (2-3 days)

**Features**:
- User registration/login
- Role-based access (admin, editor, viewer)
- Per-user statement permissions
- Activity audit log
- Password reset

**Stack**:
- Flask-Login
- Bcrypt for passwords
- JWT tokens
- SQLite/PostgreSQL for users

---

### 22. **API Documentation**
**Effort**: Medium (4-6 hours)

**Tools**:
- OpenAPI/Swagger
- Auto-generated from Flask routes
- Interactive API explorer
- Code examples
- API versioning

---

### 23. **Receipt Type Detection**
**Effort**: Large (1-2 days)

**AI Detection**:
- Restaurant receipt
- Invoice
- Travel ticket
- Parking receipt
- Fuel receipt

**Benefits**:
- Auto-categorization
- Template-based parsing
- Better extraction accuracy

---

### 24. **Smart Suggestions**
**Effort**: Medium (4-6 hours)

**Features**:
- Show top 3 receipt candidates per transaction
- Explain why each was suggested
- Quick accept/reject
- Learn from user choices

---

### 25. **Scheduled Jobs**
**Effort**: Medium (3-4 hours)

**Tasks**:
- Nightly backup cleanup
- Weekly summary email
- Monthly reports
- Cache cleanup
- Duplicate detection scan

**Implementation**:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=2)
def nightly_cleanup():
    clean_old_backups()
    clean_old_cache()
    check_for_duplicates()

scheduler.start()
```

---

## 📊 Feature Comparison Matrix

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| Web Refactoring | Medium | High | 1 |
| Health Check | Small | Medium | 1 |
| Rate Limiting | Small | Medium | 1 |
| OCR Caching Integration | Medium | High | 1 |
| ML Matching | Large | High | 2 |
| Duplicate Detection | Medium | Medium | 2 |
| Exchange Rates | Medium | Medium | 2 |
| Email Import | Large | High | 3 |
| Categories/Tags | Medium | High | 3 |
| Reporting | Large | High | 3 |
| Bulk Operations | Small | Medium | 3 |
| Search/Filter | Medium | Medium | 3 |
| Cloud Sync | Large | Medium | 4 |
| Accounting Export | Large | High | 4 |
| Mobile API | Large | High | 4 |
| Webhooks | Medium | Low | 4 |
| Loading States | Small | Medium | 5 |
| Drag Enhancements | Medium | Low | 5 |
| Keyboard Nav | Small | Medium | 5 |
| Dark Mode | Small | Low | 5 |
| Multi-User | Large | Medium | 6 |
| API Docs | Medium | Low | 6 |
| Receipt Types | Large | Medium | 6 |
| Smart Suggestions | Medium | Medium | 6 |
| Scheduled Jobs | Medium | Medium | 6 |

---

## 🗺️ Recommended Implementation Order

### Phase 1: Stability & Performance (1-2 weeks)
1. Web layer refactoring
2. Health check endpoint
3. Rate limiting
4. OCR caching integration

### Phase 2: Enhanced Matching (2-3 weeks)
5. Duplicate detection
6. Real-time exchange rates
7. ML auto-matching

### Phase 3: Productivity (3-4 weeks)
8. Categories & tags
9. Bulk operations
10. Advanced search
11. Monthly reporting

### Phase 4: Integrations (4-6 weeks)
12. Email import
13. Accounting export
14. Cloud storage sync
15. Mobile API

### Phase 5: Polish (1-2 weeks)
16. Loading states
17. Keyboard navigation
18. Dark mode
19. UX improvements

### Phase 6: Advanced (4-6 weeks)
20. Multi-user auth
21. Smart suggestions
22. Receipt type detection
23. Scheduled jobs
24. API documentation

---

## 💡 Quick Wins (High Impact, Low Effort)

1. **Health Check Endpoint** (30 min) - Production monitoring
2. **Rate Limiting** (1 hour) - Prevent abuse
3. **Loading States** (2-3 hours) - Better UX
4. **Keyboard Shortcuts** (2 hours) - Power user features
5. **Bulk Operations** (2-3 hours) - Save time

Start with these to get quick improvements!

---

**Last Updated**: February 10, 2026  
**Maintained By**: Receipt Checker Team
