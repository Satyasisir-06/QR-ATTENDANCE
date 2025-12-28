# QR Code Attendance System

A Flask-based web application for managing student attendance using QR codes.

## Features

- **Admin Dashboard**: Generate time-limited QR codes for attendance
- **Student Portal**: Scan QR codes and mark attendance
- **Attendance Records**: View and download attendance data
- **Auto-expire QR Codes**: QR codes expire after 2 minutes
- **Subject & Branch Tracking**: Record attendance by subject and branch
- **CSV Export**: Download attendance records as CSV files

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL (for production) / SQLite (for local development)
- **Frontend**: HTML, CSS, JavaScript
- **QR Generation**: Python qrcode library

## Local Development Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd QR
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app1.py
```

4. Access the application:
   - Admin Login: http://localhost:5000/ (username: `admin`, password: `admin123`)
   - Student Login: http://localhost:5000/student_login (username: `student`, password: `student123`)

## Deployment to Vercel

### Prerequisites

1. Create a PostgreSQL database (recommended providers):
   - [Supabase](https://supabase.com/) (Free tier available)
   - [Railway](https://railway.app/) (Free tier available)
   - [Neon](https://neon.tech/) (Free tier available)

2. Get your database connection URL (format: `postgresql://user:password@host:port/database`)

### Deploy Steps

1. Push your code to GitHub

2. Import project to Vercel:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository

3. Configure Environment Variables in Vercel:
   - `DATABASE_URL` = your PostgreSQL connection string
   - `SECRET_KEY` = a random secret key for Flask sessions

4. Deploy!

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required for production)
- `SECRET_KEY`: Flask secret key for sessions (recommended to change from default)

## Default Credentials

**Admin:**
- Username: `admin`
- Password: `admin123`

**Student:**
- Username: `student`
- Password: `student123`

⚠️ **Important**: Change these credentials in production!

## Project Structure

```
QR/
├── app1.py                 # Main Flask application
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment config
├── templates/             # HTML templates
│   ├── admin.html
│   ├── login.html
│   ├── scan.html
│   ├── student.html
│   ├── success.html
│   └── view.html
└── static/                # Static files (CSS, JS)
    └── style.css
```

## License

MIT License
