# Deployment Guide

## ✅ Files Created for Deployment

1. **requirements.txt** - Python dependencies
2. **vercel.json** - Vercel configuration
3. **.gitignore** - Files to exclude from Git
4. **README.md** - Project documentation
5. **.env.example** - Environment variables template

## 🚀 Deployment Steps

### Step 1: Set Up PostgreSQL Database

Choose one of these **FREE** database providers:

#### Option A: Supabase (Recommended)
1. Go to [supabase.com](https://supabase.com/)
2. Create new project
3. Go to Settings → Database
4. Copy the **Connection String (URI)**
5. Format: `postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres`

#### Option B: Railway
1. Go to [railway.app](https://railway.app/)
2. New Project → Provision PostgreSQL
3. Copy **DATABASE_URL** from variables tab

#### Option C: Neon
1. Go to [neon.tech](https://neon.tech/)
2. Create new project
3. Copy connection string

### Step 2: Push to GitHub

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - QR attendance system"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/yourusername/qr-attendance.git

# Push
git push -u origin main
```

### Step 3: Deploy to Vercel

1. Go to [vercel.com](https://vercel.com/)
2. Sign in with GitHub
3. Click **"New Project"**
4. Import your GitHub repository
5. **Configure Environment Variables:**
   - `DATABASE_URL` = Your PostgreSQL connection string
   - `SECRET_KEY` = Generate random key (e.g., use: `python -c "import secrets; print(secrets.token_hex(32))"`)
6. Click **"Deploy"**

### Step 4: Test Your Deployment

After deployment:
1. Visit your Vercel URL (e.g., `your-project.vercel.app`)
2. Test admin login: username `admin`, password `admin123`
3. Test student login: username `student`, password `student123`

## 🔧 Local Development

To run locally with the updated code:

```bash
# Install dependencies
pip install -r requirements.txt

# Run (will use SQLite by default)
python app1.py

# Access at http://localhost:5000
```

## ⚠️ Important Notes

### Database Differences

- **Local**: Uses SQLite (`attendance.db`)
- **Production**: Uses PostgreSQL (from `DATABASE_URL` env variable)

The code automatically detects which database to use!

### Security

**IMPORTANT**: Change default credentials before production:

Edit [app1.py](app1.py) lines with default credentials:
- Admin: `admin` / `admin123`
- Student: `student` / `student123`

### Common Issues

**Issue**: "Module not found" error
- **Solution**: Make sure `requirements.txt` is in the root directory

**Issue**: Database connection error
- **Solution**: Verify `DATABASE_URL` is correctly set in Vercel environment variables

**Issue**: QR codes not generating
- **Solution**: Check Pillow is installed (`pip install Pillow`)

## 📝 Environment Variables

Set these in Vercel Dashboard → Settings → Environment Variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | ⚠️ Recommended | Flask session secret | `abc123def456...` |

## 🎯 Next Steps

1. ✅ Set up PostgreSQL database
2. ✅ Push code to GitHub
3. ✅ Deploy to Vercel
4. ⚠️ Change default passwords
5. ⚠️ Test all features
6. ⚠️ Configure custom domain (optional)

## 📞 Support

If you encounter issues:
1. Check Vercel deployment logs
2. Verify environment variables are set correctly
3. Test database connection string separately
4. Check the README.md for more details

---
Happy Deploying! 🚀
