# Stripe Setup Guide

## Step 1: Create Stripe Account (5 minutes)

1. **Go to Stripe**: https://stripe.com
2. **Sign Up** with email
3. **Verify email**
4. **Complete business profile** (you can use personal details for testing)

## Step 2: Activate Test Mode (1 minute)

1. In Stripe dashboard, **toggle "Test mode" ON** (top right)
2. All setup will be in test mode first
3. You'll see "Test mode" badge on all pages

## Step 3: Create Product and Price (5 minutes)

### Create Product

1. Go to **Products** in left sidebar
2. Click **+ Add product**
3. Fill in:
   - **Name**: Receipt Checker Pro (or your product name)
   - **Description**: Unlimited receipt matching and OCR processing
   - **Upload image**: Optional logo
   
### Create Price

4. In the same form, under "Pricing":
   - **Pricing model**: Standard pricing
   - **Price**: 19.00 EUR
   - **Billing period**: Monthly
   - **Payment type**: Recurring
   
5. Click **Save product**

### Get Price ID

6. Click on the product you just created
7. In the "Pricing" section, you'll see a price ID like: `price_1Abc123...`
8. **Copy this Price ID** - you'll need it for `.env`

## Step 4: Get API Keys (2 minutes)

1. Go to **Developers** → **API keys**
2. You'll see two keys:
   - **Publishable key**: `pk_test_51Abc...`
   - **Secret key**: `sk_test_51Abc...` (click "Reveal test key")
3. **Copy both keys**

## Step 5: Set Up Webhooks (5 minutes)

Webhooks allow Stripe to notify your app about payment events.

### Create Webhook Endpoint

1. Go to **Developers** → **Webhooks**
2. Click **+ Add endpoint**
3. **Endpoint URL**: `https://your-railway-app.up.railway.app/webhooks/stripe`
   - For local testing: `http://localhost:5001/webhooks/stripe`
   - For production: Use your Railway URL
   
4. **Description**: "Receipt Checker subscription events"

5. **Select events to listen to**:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `checkout.session.completed`

6. Click **Add endpoint**

### Get Webhook Secret

7. Click on the webhook you just created
8. Click **Reveal** next to "Signing secret"
9. **Copy the webhook secret**: `whsec_...`

## Step 6: Configure .env File

Add to your `.env`:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_51Abc...  # From Step 4
STRIPE_PUBLISHABLE_KEY=pk_test_51Abc...  # From Step 4
STRIPE_WEBHOOK_SECRET=whsec_...  # From Step 5
STRIPE_PRICE_ID=price_1Abc...  # From Step 3
```

## Step 7: Test Stripe Connection

Create test script:

```python
# test_stripe.py
from src.stripe_client import stripe_client

# Test creating a customer
result = stripe_client.create_customer(
    email="test@example.com",
    name="Test User"
)

if result['success']:
    print(f"✅ Stripe connected! Customer ID: {result['customer'].id}")
else:
    print(f"❌ Error: {result['error']}")
```

Run:
```bash
python test_stripe.py
```

## Step 8: Enable Customer Portal (3 minutes)

The Customer Portal allows users to manage their subscriptions.

1. Go to **Settings** → **Billing** → **Customer portal**
2. Click **Activate link**
3. Configure settings:
   - ✅ Allow customers to update payment methods
   - ✅ Allow customers to cancel subscriptions
   - ✅ Allow customers to update billing information
   - Invoice history: On
   
4. **Customize branding** (optional):
   - Add your logo
   - Set brand color
   - Custom message

5. Click **Save**

## Step 9: Test Payment Flow (Optional)

Use Stripe's test card numbers:

**Successful payment**:
- Card: `4242 4242 4242 4242`
- Exp: Any future date (e.g., `12/34`)
- CVC: Any 3 digits (e.g., `123`)
- ZIP: Any 5 digits (e.g., `12345`)

**Payment fails**:
- Card: `4000 0000 0000 0002`

**Requires authentication (3D Secure)**:
- Card: `4000 0027 6000 3184`

## ✅ Stripe Setup Complete!

Your Stripe account is ready with:
- ✅ Test mode activated
- ✅ Product created (Receipt Checker Pro)
- ✅ Price set (€19/month)
- ✅ API keys configured
- ✅ Webhooks configured
- ✅ Customer Portal enabled

---

## Next Steps

1. Implement authentication (users need accounts first)
2. Create checkout flow
3. Add webhook handler
4. Test subscription flow

---

## Going to Production

When ready to accept real payments:

1. **Switch to Live Mode**:
   - Toggle "Test mode" OFF in dashboard
   - Repeat Steps 3-6 in live mode
   - Update `.env` with live keys (use `STRIPE_LIVE_SECRET_KEY`, etc.)

2. **Verify Business Details**:
   - Go to **Settings** → **Business settings**
   - Complete all required information
   - Add bank account for payouts

3. **Update Webhook URL**:
   - Use production Railway URL
   - Test webhooks with Stripe CLI first

---

## Troubleshooting

**Problem**: "No such price: price_xxx"
- **Solution**: Make sure you copied the correct Price ID from Step 3

**Problem**: "Invalid API key"
- **Solution**: Check you're using test keys (start with `sk_test_` and `pk_test_`)

**Problem**: Webhooks not receiving events
- **Solution**: 
  - Check endpoint URL is correct and accessible
  - For local testing, use Stripe CLI: `stripe listen --forward-to localhost:5001/webhooks/stripe`

**Problem**: "No such customer"
- **Solution**: Make sure customer was created in same mode (test/live)

---

## Useful Stripe CLI Commands

Install Stripe CLI: https://stripe.com/docs/stripe-cli

```bash
# Login
stripe login

# Listen to webhooks locally
stripe listen --forward-to localhost:5001/webhooks/stripe

# Trigger test webhook
stripe trigger customer.subscription.created

# View logs
stripe logs tail
```

---

## Testing Checklist

- [ ] Created test customer
- [ ] Created test product and price
- [ ] Generated API keys
- [ ] Set up webhooks
- [ ] Tested connection with Python
- [ ] Configured Customer Portal
- [ ] Test card payment works
- [ ] Webhooks deliver to endpoint

