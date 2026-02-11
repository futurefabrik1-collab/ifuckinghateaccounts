# User Capacity & Performance Monitoring

## Current Configuration
- **Workers**: 4 sync workers
- **Timeout**: 120 seconds
- **Platform**: Railway (Hobby/Pro plan)
- **Estimated Capacity**: 5-10 concurrent users

---

## How to Monitor Usage

### 1. Railway Dashboard Metrics
- Go to Railway → Your service → **Metrics**
- Watch:
  - **CPU Usage**: Should stay < 80%
  - **Memory**: Should stay < 80% of allocated
  - **Request Rate**: Requests per minute
  - **Response Time**: Should be < 2-3 seconds

### 2. Application Logs
Check for these warning signs:
```bash
# In Railway deployment logs, look for:
- "Worker timeout" (workers taking > 120s)
- "Out of memory" (RAM exhausted)
- Multiple 502/503 errors (workers overwhelmed)
```

### 3. User Experience Indicators
Signs you need to scale:
- ❌ Uploads failing frequently
- ❌ "Application failed to respond" errors
- ❌ Slow response times (> 5 seconds)
- ❌ Timeouts during OCR/matching

---

## Performance Benchmarks

### Expected Response Times:
| Operation | Normal | Concerning |
|-----------|--------|------------|
| Page load | < 1s | > 3s |
| CSV upload | 1-3s | > 10s |
| Receipt upload | 2-5s | > 15s |
| Match receipts | 5-20s | > 60s |
| OCR processing | 10-30s | > 120s |

---

## Scaling Triggers

### When to Upgrade:

**Upgrade to Pro Plan ($20/mo)** if:
- CPU consistently > 70%
- Memory consistently > 70%
- More than 5 active users regularly
- Users reporting slowness

**Add Background Workers** if:
- OCR/matching timeouts occurring
- More than 10 active users
- Heavy batch processing needed

**Horizontal Scaling** if:
- More than 30-50 users
- Global user base (need multiple regions)
- High availability requirements

---

## Quick Performance Improvements

### Low-Effort Wins:
1. **Switch to gevent workers** (15 min)
2. **Increase timeout to 300s** for OCR (2 min)
3. **Add caching** for repeat queries (30 min)
4. **Compress uploaded files** (20 min)

### Medium-Effort:
1. **Implement background jobs** (2-4 hours)
2. **Add Redis caching** (1-2 hours)
3. **Optimize database queries** (2-3 hours)

---

## Cost vs. Capacity Matrix

| Monthly Cost | Setup | Capacity | Best For |
|--------------|-------|----------|----------|
| **$0-5** | Current | 5-10 users | Personal use |
| **$20** | Railway Pro | 20-40 users | Small team |
| **$30-40** | Pro + Redis | 40-80 users | Growing business |
| **$50+** | Team plan | 100+ users | Enterprise |

---

## Testing Load

### Simple Load Test:
```bash
# Install Apache Bench
brew install apache-bench  # macOS

# Test with 10 concurrent users, 100 requests
ab -n 100 -c 10 https://ifuckinghateaccounts-production.up.railway.app/

# Look for:
# - Requests per second
# - Time per request
# - Failed requests (should be 0)
```

---

## Current Bottleneck Priority:

1. **Worker capacity** (4 sync workers)
2. **Memory limits** (depends on Railway plan)
3. **CPU for OCR** (shared vCPU)
4. **Database I/O** (SQLite on volume)

---

**Last Updated**: 2026-02-11
