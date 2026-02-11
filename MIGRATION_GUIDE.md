# Migration Guide: Local Auth → Supabase Auth

## Overview

This guide explains how to migrate from the existing local authentication system to Supabase-based authentication for the SaaS transformation.

---

## Current System vs. New System

### Current (Local Auth)
- **Storage**: SQLite database (`data/users.db`)
- **Auth**: Flask-Login with local password hashing
- **User Management**: Manual user table management
- **Scaling**: Single-server, limited to local storage

### New (Supabase Auth)
- **Storage**: Supabase PostgreSQL (cloud)
- **Auth**: Supabase Auth with JWT tokens
- **User Management**: Automatic via Supabase
- **Scaling**: Multi-tenant, cloud-based

---

## Migration Strategy

We have **two options**:

### Option 1: Gradual Migration (Recommended)
Keep both systems running in parallel:
1. New users → Supabase auth
2. Existing users → Local auth (still works)
3. Gradually migrate existing users
4. Eventually deprecate local auth

**Pros**:
- No downtime
- Existing users not disrupted
- Can test thoroughly

**Cons**:
- More complex temporarily
- Two auth systems to maintain

### Option 2: Hard Switch
Replace local auth completely with Supabase:
1. Export existing users
2. Import to Supabase
3. Force password reset for all users
4. Switch to Supabase auth

**Pros**:
- Clean cutover
- Single system immediately

**Cons**:
- Requires downtime
- Users must reset passwords
- Higher risk

---

## Implementation Steps (Option 1 - Recommended)

### Phase 1: Set Up Supabase (✅ Already Done)
- [x] Create Supabase client
- [x] Create database schema
- [x] Create SupabaseAuthService
- [x] Create auth middleware

### Phase 2: Add Dual Auth Support

#### 1. Update `web/app.py`

```python
# Add at top
from src.auth_supabase import SupabaseAuthService, SupabaseUser
import os

# Add environment variable to toggle auth system
USE_SUPABASE_AUTH = os.getenv('USE_SUPABASE_AUTH', 'false').lower() == 'true'

# Update user_loader
@login_manager.user_loader
def load_user(user_id):
    if USE_SUPABASE_AUTH:
        return SupabaseAuthService.load_user_by_id(user_id)
    else:
        # Existing local auth
        return AuthService.get_user_by_id(user_id)
```

#### 2. Update `web/auth_routes.py`

```python
# At top
from src.auth_supabase import SupabaseAuthService, SupabaseUser
import os

USE_SUPABASE_AUTH = os.getenv('USE_SUPABASE_AUTH', 'false').lower() == 'true'

# Update register route
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Use Supabase or local auth based on config
        if USE_SUPABASE_AUTH:
            success, message, user = SupabaseAuthService.register_user(
                email, password
            )
        else:
            # Existing local auth
            success, message, user = AuthService.register_user(
                username, email, password
            )
        
        if success:
            login_user(user, remember=True)
            flash('Registration successful!', 'success')
            
            # If using Supabase, redirect to subscription checkout
            if USE_SUPABASE_AUTH:
                return redirect(url_for('subscription.checkout'))
            else:
                return redirect(url_for('index'))
        else:
            flash(message, 'error')
    
    return render_template('auth/register.html')

# Similar updates for login route
```

### Phase 3: Add Subscription Routes

Create `web/subscription_routes.py` (covered in Phase 5)

### Phase 4: Testing

1. **Test with local auth** (default):
   ```bash
   USE_SUPABASE_AUTH=false python web/app.py
   ```

2. **Test with Supabase auth**:
   ```bash
   USE_SUPABASE_AUTH=true python web/app.py
   ```

### Phase 5: Gradual Rollout

1. Deploy with `USE_SUPABASE_AUTH=false` (existing users work)
2. Test Supabase auth in staging
3. Enable for new users only
4. Monitor for issues
5. Migrate existing users (optional)
6. Eventually switch fully to Supabase

---

## Environment Variables

Add to `.env`:

```bash
# Authentication System
USE_SUPABASE_AUTH=false  # Set to 'true' to use Supabase auth

# Supabase (required if USE_SUPABASE_AUTH=true)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Stripe (required if USE_SUPABASE_AUTH=true)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# Encryption
ENCRYPTION_KEY=your-encryption-key
```

---

## User Data Migration (Optional)

If you want to migrate existing users to Supabase:

### Step 1: Export Users

```python
# migrate_users.py
from src.auth import AuthService
from src.auth_supabase import SupabaseAuthService

# Get all local users
local_users = AuthService.get_all_users()  # You'll need to add this method

for user in local_users:
    print(f"Migrating: {user.email}")
    
    # Create in Supabase (they'll need to reset password)
    # Supabase doesn't allow importing password hashes for security
    # Users will receive password reset email
```

### Step 2: Notify Users

Send email to all existing users:
```
Subject: Action Required: Password Reset

We've upgraded our authentication system for better security.
Please reset your password to continue using Receipt Checker.

[Reset Password Button]
```

---

## Testing Checklist

### Local Auth (Existing System)
- [ ] Existing users can login
- [ ] New users can register
- [ ] Logout works
- [ ] Profile page loads
- [ ] All features work

### Supabase Auth (New System)
- [ ] New users can register
- [ ] Users can login
- [ ] Session persists across page loads
- [ ] Logout works
- [ ] Profile page loads
- [ ] Subscription checkout redirects
- [ ] API endpoints protected

### Both Systems
- [ ] No interference between systems
- [ ] Can switch via environment variable
- [ ] Session handling works correctly

---

## Rollback Plan

If Supabase auth has issues:

1. Set `USE_SUPABASE_AUTH=false` in `.env`
2. Restart application
3. All users revert to local auth
4. Fix issues with Supabase setup
5. Try again when ready

---

## Complete Cutover (Future)

When ready to fully switch to Supabase:

1. Announce migration date to users
2. Send password reset emails
3. Set `USE_SUPABASE_AUTH=true`
4. Remove local auth code (optional)
5. Archive old user database

---

## Current Status

- ✅ Supabase client created
- ✅ Database schema designed
- ✅ SupabaseAuthService created
- ⏳ Dual auth support (pending)
- ⏳ Subscription routes (pending)
- ⏳ Testing (pending)

---

## Next Steps

1. **Set up Supabase account** (if not done)
2. **Add dual auth support** to `web/app.py`
3. **Test both auth systems** work independently
4. **Create subscription routes** (Phase 5)
5. **Deploy with local auth** as default
6. **Gradually enable** Supabase for new users

---

## Questions?

- Should we migrate existing users or keep them on local auth?
- When do you want to switch to Supabase auth?
- Do you have many existing users to migrate?

**Recommendation**: Start with `USE_SUPABASE_AUTH=false`, build out subscription system, then switch when ready.
