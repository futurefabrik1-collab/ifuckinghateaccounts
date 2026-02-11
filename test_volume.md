# Testing Railway Volume Persistence

## Test Steps:

### 1. Upload Test Data (BEFORE deployment)
- Go to: https://ifuckinghateaccounts-production.up.railway.app/
- Upload a test CSV statement
- Upload a test receipt
- Note the statement name and files uploaded

### 2. Trigger a Deployment
Make a trivial change to trigger redeployment:
```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
echo "# Volume test - $(date)" >> .test_volume
git add .test_volume
git commit -m "test: Verify volume persistence"
git push
```

### 3. Verify After Deployment
- Wait for Railway to finish deploying (~2 minutes)
- Refresh the app
- Check if your uploaded statement and receipts are still there

### Expected Results:
✅ **With Volume**: Files persist, statement and receipts still visible
❌ **Without Volume**: Files gone, need to re-upload

---

## Volume Configuration (Reference)

Railway Volume Settings:
- **Mount Path**: `/app/statements`
- **Size**: [Your chosen size]

This mounts persistent storage at the `/app/statements` directory, which is where the app stores:
- Uploaded CSV statements
- Processed matches
- Receipt files (matched and unmatched)

---

## If Files Disappear:

Check Railway dashboard:
1. Go to your service → **Settings** → **Volumes**
2. Verify volume is created and mounted at `/app/statements`
3. Check deployment logs for any volume mount errors
4. Verify the volume size isn't full

---

Created: 2026-02-11
