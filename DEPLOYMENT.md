# I FUCKING HATE ACCOUNTS - Production Deployment Guide

**Version**: 4.0.0 (Multi-User Production Ready)  
**Date**: February 11, 2026

---

## 🎯 Overview

This guide covers deploying the multi-user, encrypted, production-ready version of "I FUCKING HATE ACCOUNTS" with:

✅ **User Authentication** - Secure login/registration  
✅ **Encrypted Database** - PostgreSQL with encrypted OCR text  
✅ **Docker Deployment** - Containerized for easy deployment  
✅ **Nginx Reverse Proxy** - Production-grade web server  
✅ **CSRF Protection** - Security hardened  
✅ **Audit Logging** - Track all user actions  

---

## 📋 Prerequisites

- **Docker** and **Docker Compose** installed
- **Domain name** (for production with SSL)
- **SSL certificate** (optional - can use Let's Encrypt)
- **Minimum 2GB RAM**, 10GB disk space

---

## 🚀 Quick Start (Development)

### 1. Clone the Repository

```bash
git clone https://github.com/futurefabrik1-collab/ifuckinghateaccounts.git
cd ifuckinghateaccounts
```

### 2. Create Environment File

```bash
cp .env.example .env
nano .env
```

Set these critical values:
```bash
SECRET_KEY=your-super-secret-key-here-change-this
DB_PASSWORD=your-database-password-here
DEBUG=False
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

### 4. Initialize Database

```bash
docker-compose exec web python -c "from src.database import init_database; init_database()"
```

### 5. Create Admin User

```bash
docker-compose exec web python -c "
from src.database import db
from src.models import User
with db.get_session() as session:
    admin = User(username='admin', email='admin@example.com', password='Admin123!')
    admin.is_admin = True
    session.add(admin)
print('Admin user created!')
"
```

### 6. Access the Application

Open: **http://localhost:5001**

---

## 🌐 Production Deployment

### Option 1: DigitalOcean / Linode / AWS

#### 1. Create a Droplet/Instance

- **Size**: 2GB RAM minimum ($12/month)
- **OS**: Ubuntu 22.04 LTS
- **Add SSH key** for secure access

#### 2. SSH into Server

```bash
ssh root@your-server-ip
```

#### 3. Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose-plugin -y
```

#### 4. Clone Repository

```bash
git clone https://github.com/futurefabrik1-collab/ifuckinghateaccounts.git
cd ifuckinghateaccounts
```

#### 5. Configure Environment

```bash
nano .env
```

Production settings:
```bash
SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -hex 16)
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://receipts_user:${DB_PASSWORD}@db:5432/receipts
```

#### 6. Setup SSL (Let's Encrypt)

```bash
apt install certbot -y
certbot certonly --standalone -d your-domain.com

# Copy certificates
mkdir ssl
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

#### 7. Update nginx.conf

Uncomment SSL lines in `nginx.conf`:
```nginx
listen 443 ssl http2;
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

#### 8. Deploy

```bash
docker-compose up -d
```

#### 9. Initialize Database

```bash
docker-compose exec web python -c "from src.database import init_database; init_database()"
```

#### 10. Setup Firewall

```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

---

### Option 2: Heroku

#### 1. Install Heroku CLI

```bash
curl https://cli-assets.heroku.com/install.sh | sh
heroku login
```

#### 2. Create Heroku App

```bash
heroku create your-app-name
```

#### 3. Add PostgreSQL

```bash
heroku addons:create heroku-postgresql:mini
```

#### 4. Set Environment Variables

```bash
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
heroku config:set FLASK_ENV=production
heroku config:set DEBUG=False
```

#### 5. Deploy

```bash
git push heroku main
```

#### 6. Initialize Database

```bash
heroku run python -c "from src.database import init_database; init_database()"
```

---

### Option 3: Railway.app

#### 1. Create Account

Go to [railway.app](https://railway.app) and sign in with GitHub

#### 2. Deploy from GitHub

- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose `ifuckinghateaccounts`
- Railway auto-detects Dockerfile

#### 3. Add PostgreSQL

- Click "New" → "Database" → "PostgreSQL"
- Railway automatically sets DATABASE_URL

#### 4. Set Environment Variables

- Click on service → "Variables"
- Add:
  - `SECRET_KEY`: Generate random string
  - `DEBUG`: False
  - `FLASK_ENV`: production

#### 5. Deploy

Railway auto-deploys on push to main branch!

#### 6. Get Domain

- Click "Settings" → "Generate Domain"
- Or add custom domain

---

## 🔐 Security Checklist

Before going live:

- [ ] Change all default passwords
- [ ] Set strong SECRET_KEY (32+ random characters)
- [ ] Enable HTTPS/SSL
- [ ] Set DEBUG=False
- [ ] Configure firewall (only ports 80, 443, 22)
- [ ] Setup automatic backups
- [ ] Enable rate limiting
- [ ] Review CSRF protection
- [ ] Test user registration/login
- [ ] Setup monitoring (uptime, errors)
- [ ] Create admin account
- [ ] Test file uploads
- [ ] Verify encryption is working

---

## 📊 Monitoring & Maintenance

### Check Application Logs

```bash
docker-compose logs -f web
```

### Check Database Logs

```bash
docker-compose logs -f db
```

### Backup Database

```bash
docker-compose exec db pg_dump -U receipts_user receipts > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
cat backup_20260211.sql | docker-compose exec -T db psql -U receipts_user receipts
```

### Update Application

```bash
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 🎨 Architecture

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Nginx     │  (Reverse Proxy, SSL, Rate Limiting)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Flask     │  (Application Server - Gunicorn)
│   App       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │  (Encrypted Database)
└─────────────┘
```

---

## 📝 Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask secret key for sessions | - | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ Yes |
| `DB_PASSWORD` | Database password | - | ✅ Yes |
| `DEBUG` | Enable debug mode | False | No |
| `FLASK_ENV` | Flask environment | production | No |
| `PORT` | Application port | 5001 | No |
| `MAX_FILE_SIZE` | Max upload size (bytes) | 52428800 | No |
| `OCR_CACHE_ENABLED` | Enable OCR caching | True | No |

---

## 🐛 Troubleshooting

### Database Connection Errors

```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Application Won't Start

```bash
# Check application logs
docker-compose logs web

# Rebuild image
docker-compose build --no-cache web
docker-compose up -d
```

### Can't Login

```bash
# Check if user exists
docker-compose exec db psql -U receipts_user receipts -c "SELECT * FROM users;"

# Reset user password
docker-compose exec web python -c "
from src.database import db
from src.models import User
with db.get_session() as session:
    user = session.query(User).filter_by(username='admin').first()
    user.set_password('NewPassword123!')
"
```

---

## 💰 Cost Estimates

### Hosting Options

| Provider | Plan | RAM | Storage | Cost/Month |
|----------|------|-----|---------|------------|
| **DigitalOcean** | Basic | 2GB | 50GB | $12 |
| **Linode** | Nanode | 1GB | 25GB | $5 |
| **AWS Lightsail** | Micro | 1GB | 40GB | $5 |
| **Heroku** | Basic | - | - | $7 |
| **Railway** | Hobby | - | - | $5 |

### Recommended: DigitalOcean ($12/month)
- Reliable
- Good documentation
- Easy backups
- Scalable

---

## 🎉 Post-Deployment

After successful deployment:

1. ✅ Test user registration
2. ✅ Test login/logout
3. ✅ Upload test statement
4. ✅ Upload test receipts
5. ✅ Test matching functionality
6. ✅ Verify encryption (check database)
7. ✅ Test on mobile devices
8. ✅ Setup monitoring alerts
9. ✅ Create backup schedule
10. ✅ Document admin procedures

---

## 📞 Support

For issues:
1. Check logs: `docker-compose logs`
2. Review this guide
3. Check GitHub issues
4. Create new issue with logs

---

**Deployment Date**: _____________  
**Deployed By**: _____________  
**Domain**: _____________  
**Admin Email**: _____________

---

**🎊 Congratulations! Your app is now production-ready!** 🎊
