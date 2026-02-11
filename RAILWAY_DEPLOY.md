# 🚂 Deploy to Railway.app - Quick Guide

**App**: I FUCKING HATE ACCOUNTS  
**Time**: ~10 minutes  
**Cost**: $5/month (Hobby plan)

---

## 🎯 Prerequisites

- GitHub account (you have this ✅)
- Railway.app account (free to create)
- Your GitHub repo pushed (we'll do this now ✅)

---

## 📝 Step-by-Step Deployment

### 1. Create Railway Account

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Click **"Login with GitHub"**
4. Authorize Railway to access your GitHub

---

### 2. Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose: `futurefabrik1-collab/ifuckinghateaccounts`
4. Railway will detect your Dockerfile automatically ✅

---

### 3. Add PostgreSQL Database

1. In your project, click **"New"** button
2. Select **"Database"** → **"PostgreSQL"**
3. Railway automatically creates the database
4. Railway automatically sets `DATABASE_URL` environment variable ✅

---

### 4. Configure Environment Variables

Click on your **web service** → **Variables** tab:

Add these variables:

```
SECRET_KEY = [Click "Generate" or paste a random 32-char string]
DEBUG = False
FLASK_ENV = production
PORT = ${{PORT}}
```

**Important**: Railway automatically provides:
- `DATABASE_URL` (from PostgreSQL service)
- `PORT` (dynamic port assignment)

---

### 5. Deploy!

1. Railway **auto-deploys** when you push to GitHub!
2. Watch the build logs in Railway dashboard
3. Wait for "Success" message (~2-3 minutes)

---

### 6. Initialize Database

Once deployed, click **web service** → **three dots (•••)** → **Shell**

Run:
```bash
python -c "from src.database import init_database; init_database()"
```

This creates all database tables.

---

### 7. Create Admin User

In the Railway shell, run:

```bash
python -c "
from src.database import db
from src.models import User

with db.get_session() as session:
    admin = User(
        username='admin',
        email='your-email@example.com',
        password='Admin123!'
    )
    admin.is_admin = True
    session.add(admin)
    
print('✅ Admin user created!')
print('Username: admin')
print('Password: Admin123!')
print('⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!')
"
```

---

### 8. Get Your URL

1. Click **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Your app will be at: `your-app-name.up.railway.app`

**Or add custom domain:**
- Click "Custom Domain"
- Enter your domain
- Update DNS records as shown

---

### 9. Test Your App! 🎉

1. Open your Railway URL
2. You should see the login page
3. Try registering a new account
4. Login with admin credentials
5. Upload a test statement

---

## 🔧 Ongoing Management

### View Logs
Railway Dashboard → Your Service → **Deployments** → Click latest → **View Logs**

### Redeploy
Just `git push` to GitHub! Railway auto-deploys ✅

### Update Environment Variables
Railway Dashboard → Variables → Edit → **Save**

### Database Backup
Railway Dashboard → PostgreSQL → **Backups** tab

### Monitor Usage
Railway Dashboard → **Usage** tab

---

## 💰 Pricing

**Free Tier:**
- $5 free credit/month
- Limited hours

**Hobby Plan ($5/month):**
- Unlimited usage
- Custom domains
- Better performance
- **Recommended for production** ✅

**Pro Plan ($20/month):**
- Higher limits
- Priority support
- Team features

---

## 🐛 Troubleshooting

### Build Failed
- Check build logs in Railway
- Ensure Dockerfile is correct
- Check requirements.txt for errors

### Can't Connect to Database
- Ensure PostgreSQL service is running
- Check DATABASE_URL is set
- Restart web service

### App Crashes
- View logs: Railway → Service → Logs
- Check environment variables
- Ensure `gunicorn` is installed

### Database Not Initialized
```bash
# In Railway shell:
python -c "from src.database import init_database; init_database()"
```

---

## 🎨 Custom Domain Setup

### 1. In Railway
- Settings → Networking → Custom Domain
- Enter: `receipts.yourdomain.com`

### 2. In Your DNS Provider
Add CNAME record:
```
Type: CNAME
Name: receipts (or @)
Value: [Railway provides this]
TTL: 3600
```

### 3. Wait for SSL
Railway automatically provisions SSL (Let's Encrypt)
Usually takes 1-5 minutes ✅

---

## 📊 Post-Deployment Checklist

After deployment:

- [ ] App is accessible at Railway URL
- [ ] Can register new account
- [ ] Can login/logout
- [ ] Can upload statement
- [ ] Can upload receipts
- [ ] PostgreSQL is connected
- [ ] Admin account created
- [ ] Changed admin password
- [ ] Custom domain configured (optional)
- [ ] Monitoring set up

---

## 🔐 Security Notes

**Change Immediately:**
1. Admin password (from default)
2. SECRET_KEY (if using default)

**Regular Maintenance:**
1. Backup database weekly
2. Monitor logs for errors
3. Update dependencies monthly
4. Review audit logs

---

## 📞 Support

**Railway Docs**: https://docs.railway.app  
**Railway Discord**: https://discord.gg/railway  
**GitHub Issues**: https://github.com/futurefabrik1-collab/ifuckinghateaccounts/issues

---

## 🎉 Success!

Your "I FUCKING HATE ACCOUNTS" app is now:
- ✅ Live on the internet
- ✅ Secure with user authentication
- ✅ Encrypted database
- ✅ Auto-deploying on git push
- ✅ Scalable and production-ready

**URL**: `https://your-app.up.railway.app`

---

**Deployment Date**: _____________  
**Railway URL**: _____________  
**Admin Username**: admin  
**Admin Email**: _____________

🚂 **All aboard the Railway to production!** 🎊
