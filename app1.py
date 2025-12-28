from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, qrcode, datetime, csv, io, os, base64
import urllib.parse
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
app.permanent_session_lifetime = timedelta(days=1)

# Database configuration
USE_POSTGRES = os.environ.get("DATABASE_URL") is not None

def get_db_connection():
    """Get database connection based on environment"""
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(os.environ.get("DATABASE_URL"))
    else:
        return sqlite3.connect("attendance.db")

# ---------- DATABASE SETUP ----------
def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS admin(
        username TEXT,
        password TEXT
    )
    """)

# ---------- DATABASE SETUP ----------
def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL syntax
        c.execute("""
        CREATE TABLE IF NOT EXISTS admin(
            username TEXT,
            password TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            roll TEXT,
            name TEXT,
            date TEXT,
            time TEXT,
            subject TEXT,
            branch TEXT
        )
        """)

        # Insert default admin (use ON CONFLICT for PostgreSQL)
        c.execute("""
            INSERT INTO admin (username, password) 
            VALUES ('admin', 'admin123')
            ON CONFLICT DO NOTHING
        """)
    else:
        # SQLite syntax
        c.execute("""
        CREATE TABLE IF NOT EXISTS admin(
            username TEXT,
            password TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            roll TEXT,
            name TEXT,
            date TEXT,
            time TEXT
        )
        """)

        # Migrate existing old table (with id) to new schema while preserving data
        c.execute("PRAGMA table_info(attendance)")
        cols = [r[1] for r in c.fetchall()]
        
        if 'id' in cols:
            c.execute("CREATE TABLE IF NOT EXISTS attendance_new(roll TEXT, name TEXT, date TEXT, time TEXT)")
            c.execute("INSERT INTO attendance_new(roll,name,date,time) SELECT roll,name,date,time FROM attendance")
            c.execute("DROP TABLE attendance")
            c.execute("ALTER TABLE attendance_new RENAME TO attendance")

        # Ensure subject column exists; if not, add it
        if 'subject' not in cols:
            try:
                c.execute("ALTER TABLE attendance ADD COLUMN subject TEXT")
            except Exception:
                pass

        # Ensure branch column exists; if not, add it
        if 'branch' not in cols:
            try:
                c.execute("ALTER TABLE attendance ADD COLUMN branch TEXT")
            except Exception:
                pass

        c.execute("INSERT OR IGNORE INTO admin VALUES('admin','admin123')")
        
        # Normalize legacy subject value 'P&S' to 'P and S'
        try:
            c.execute("UPDATE attendance SET subject = ? WHERE subject = ?", ('P and S', 'P&S'))
        except Exception:
            pass

    conn.commit()
    conn.close()

# Initialize database only if not in production or on first run
try:
    init_db()
except Exception as e:
    print(f"Database initialization warning: {e}")
    # Continue anyway - might succeed on first request

@app.before_request
def ensure_db():
    """Ensure database is initialized on each request"""
    try:
        init_db()
    except Exception:
        pass

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    # Admin Login Route
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        if u == "admin":
            if p == "admin123":
                session["admin"] = True
                if request.form.get("remember"):
                    session.permanent = True
                return redirect("/admin")
            else:
                error = "Wrong password"
        elif u == "student":
            error = "Please use the Student Login page."
        else:
            error = "Invalid Admin Credentials"

    return render_template("login.html", error=error, title="Admin Login", role="admin")

@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    # Student Login Route
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        if u == "student":
            if p == "student123":
                session.clear()
                session["role"] = "student"
                if request.form.get("remember"):
                    session.permanent = True
                return redirect("/student")
            else:
                error = "Wrong password"
        elif u == "admin":
            error = "Please use the Admin Login page."
        else:
            error = "Invalid Student Credentials"

    return render_template("login.html", error=error, title="Student Login", active_panel="student")

# ---------- ADMIN DASHBOARD ----------
@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/")
    added = request.args.get('added') or ''
    return render_template("admin.html", added=added)

# ---------- STUDENT DASHBOARD ----------
@app.route("/student", methods=["GET", "POST"])
def student():
    if session.get("role") != "student":
        return redirect("/student_login")
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            return redirect(f"/view?name={urllib.parse.quote_plus(name)}")
    return render_template("student.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- GENERATE QR ----------
@app.route("/generate")
def generate():
    if "admin" not in session:
        return redirect("/")
    subject = request.args.get('sub','')
    branch = request.args.get('branch','')
    expiry_dt = datetime.datetime.now() + datetime.timedelta(minutes=2)
    expiry = expiry_dt.strftime("%H:%M")
    expiry_ts = int(expiry_dt.timestamp())
    url = f"{request.host_url}scan?exp={expiry}"
    if subject:
        url += f"&sub={urllib.parse.quote_plus(subject)}"
    if branch:
        url += f"&branch={urllib.parse.quote_plus(branch)}"

    qr_ok = False
    qr_error = None
    qr_base64 = None
    try:
        img = qrcode.make(url)
        # Save to bytes buffer instead of file (for Vercel compatibility)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        qr_ok = True
    except Exception as e:
        qr_error = str(e)
        qr_ok = False

    return render_template("admin.html", qr=qr_ok, expiry=expiry, subject=subject, branch=branch, expiry_ts=expiry_ts, qr_error=qr_error, qr_base64=qr_base64)

# ---------- SCAN & MARK ----------
@app.route("/scan", methods=["GET", "POST"])
def scan():
    exp = request.args.get("exp")
    subj = request.args.get("sub") or None
    branch = request.args.get("branch") or None
    date = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime("%H:%M")

    if exp and now > exp:
        return "QR Expired ❌"

    # Check session to prevent multiple attempts from same device for this subject/branch today
    session_key = f"marked_{date}_{subj if subj else 'general'}_{branch if branch else 'general'}"
    if session.get(session_key):
        return "Attendance Already Marked for this Subject/Branch Today ⚠️"

    if request.method == "POST":
        try:
            roll = request.form.get("roll", "").strip()
            name = request.form.get("name", "").strip()
            
            if not roll or not name:
                return "Roll number and name are required ❌"
            
            subj = request.args.get("sub") or request.form.get("subject") or None
            branch = request.args.get("branch") or request.form.get("branch") or None
            time = datetime.datetime.now().strftime("%H:%M:%S")

            conn = get_db_connection()
            c = conn.cursor()

            # Check for duplicate: based on available columns
            cols = []
            if USE_POSTGRES:
                # PostgreSQL - check columns differently
                c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='attendance'")
                cols = [r[0] for r in c.fetchall()]
            else:
                # SQLite - use PRAGMA
                c.execute("PRAGMA table_info(attendance)")
                cols = [r[1] for r in c.fetchall()]
            
            # Check for duplicate attendance
            if subj and branch and 'subject' in cols and 'branch' in cols:
                if USE_POSTGRES:
                    c.execute("SELECT * FROM attendance WHERE roll=%s AND date=%s AND subject=%s AND branch=%s", (roll, date, subj, branch))
                else:
                    c.execute("SELECT * FROM attendance WHERE roll=? AND date=? AND subject=? AND branch=?", (roll, date, subj, branch))
            elif subj and 'subject' in cols:
                if USE_POSTGRES:
                    c.execute("SELECT * FROM attendance WHERE roll=%s AND date=%s AND subject=%s", (roll, date, subj))
                else:
                    c.execute("SELECT * FROM attendance WHERE roll=? AND date=? AND subject=?", (roll, date, subj))
            elif branch and 'branch' in cols:
                if USE_POSTGRES:
                    c.execute("SELECT * FROM attendance WHERE roll=%s AND date=%s AND branch=%s", (roll, date, branch))
                else:
                    c.execute("SELECT * FROM attendance WHERE roll=? AND date=? AND branch=?", (roll, date, branch))
            else:
                if USE_POSTGRES:
                    c.execute("SELECT * FROM attendance WHERE roll=%s AND date=%s", (roll, date))
                else:
                    c.execute("SELECT * FROM attendance WHERE roll=? AND date=?", (roll, date))
            
            if c.fetchone():
                session[session_key] = True
                session.permanent = True
                conn.close()
                return "Attendance Already Marked ⚠️"

            # Insert including available columns
            if 'subject' in cols and 'branch' in cols:
                if USE_POSTGRES:
                    c.execute("INSERT INTO attendance (roll, name, date, time, subject, branch) VALUES (%s,%s,%s,%s,%s,%s)",
                              (roll, name, date, time, subj, branch))
                else:
                    c.execute("INSERT INTO attendance (roll, name, date, time, subject, branch) VALUES (?,?,?,?,?,?)",
                              (roll, name, date, time, subj, branch))
            elif 'subject' in cols:
                if USE_POSTGRES:
                    c.execute("INSERT INTO attendance (roll, name, date, time, subject) VALUES (%s,%s,%s,%s,%s)",
                              (roll, name, date, time, subj))
                else:
                    c.execute("INSERT INTO attendance (roll, name, date, time, subject) VALUES (?,?,?,?,?)",
                              (roll, name, date, time, subj))
            elif 'branch' in cols:
                if USE_POSTGRES:
                    c.execute("INSERT INTO attendance (roll, name, date, time, branch) VALUES (%s,%s,%s,%s,%s)",
                              (roll, name, date, time, branch))
                else:
                    c.execute("INSERT INTO attendance (roll, name, date, time, branch) VALUES (?,?,?,?,?)",
                              (roll, name, date, time, branch))
            else:
                if USE_POSTGRES:
                    c.execute("INSERT INTO attendance (roll, name, date, time) VALUES (%s,%s,%s,%s)",
                              (roll, name, date, time))
                else:
                    c.execute("INSERT INTO attendance (roll, name, date, time) VALUES (?,?,?,?)",
                              (roll, name, date, time))
            conn.commit()
            conn.close()

            session[session_key] = True
            session.permanent = True

            return render_template("success.html")
        except Exception as e:
            print(f"Error in scan POST: {str(e)}")
            return f"Error: {str(e)}"

    return render_template("scan.html")

# ---------- VIEW ----------
@app.route("/view")
def view():
    # Allow both admin and student, but distinguish them
    if "admin" not in session and session.get("role") != "student":
        return redirect("/")
    
    is_admin = "admin" in session
    
    selected_subject = request.args.get('sub') or ''
    selected_branch = request.args.get('branch') or ''
    selected_name = request.args.get('name') or ''
    selected_month = request.args.get('month') or ''
    selected_day = request.args.get('day') or ''

    subjects = []
    branches = ["CAI", "CSM", "CSD", "CSE-A", "CSE-B", "CSE-C", "CSE-D", "MECH", "EEE", "ECE", "CIVIL"]

    conn = get_db_connection()
    c = conn.cursor()
    
    # Dynamic query construction for filtering
    query = "SELECT * FROM attendance WHERE 1=1"
    params = []
    if selected_subject:
        query += " AND subject=?"
        params.append(selected_subject)
    if selected_branch:
        query += " AND branch=?"
        params.append(selected_branch)
    if selected_name:
        query += " AND name LIKE ?"
        params.append(f"%{selected_name}%")
    if selected_month:
        query += " AND strftime('%m', date)=?"
        params.append(selected_month.zfill(2))
    if selected_day:
        query += " AND strftime('%d', date)=?"
        params.append(selected_day.zfill(2))
    
    query += " ORDER BY date DESC, time DESC"
    
    c.execute(query, params)
    data = c.fetchall()
    conn.close()

    cleared = request.args.get('cleared')
    backup = request.args.get('backup')
    added = request.args.get('added') or ''
    
    return render_template("view.html", data=data, cleared=cleared, backup=backup, 
                           subjects=subjects, selected_subject=selected_subject, 
                           branches=branches, selected_branch=selected_branch, 
                           selected_name=selected_name, added=added, is_admin=is_admin,
                           selected_month=selected_month, selected_day=selected_day)

# ---------- STUDENT VIEW ATTENDANCE ----------
@app.route("/student_view")
def student_view():
    if session.get("role") != "student":
        return redirect("/student_login")
    student_name = request.args.get('name', '').strip()
    selected_subject = request.args.get('sub', '').strip()
    if not student_name:
        return redirect("/student")

    subjects = []

    conn = get_db_connection()
    c = conn.cursor()
    # Fetch all records for the student to calculate correct stats regardless of filter
    c.execute("SELECT * FROM attendance WHERE name=? ORDER BY date DESC, time DESC", (student_name,))
    all_data = c.fetchall()
    conn.close()

    if selected_subject:
        data = [row for row in all_data if len(row) > 4 and row[4] == selected_subject]
    else:
        data = all_data

    # Calculate attendance count per subject
    attendance_count = {}
    for row in all_data:
        subj = row[4] if len(row) > 4 else ''
        if subj:
            attendance_count[subj] = attendance_count.get(subj, 0) + 1

    return render_template("student_view.html", data=data, student_name=student_name, subjects=subjects, selected_subject=selected_subject, attendance_count=attendance_count)

# ---------- MANUAL ADD ATTENDANCE ----------
@app.route("/manual_add", methods=["POST"])
def manual_add():
    if "admin" not in session:
        return redirect("/")
    roll = (request.form.get("roll") or "").strip()
    name = (request.form.get("name") or "").strip()
    subj = request.form.get("subject") or None
    branch = request.form.get("branch") or None
    date = request.form.get("date") or datetime.date.today().isoformat()
    time = request.form.get("time") or datetime.datetime.now().strftime("%H:%M:%S")

    if not roll or not name:
        return redirect(f"/admin?added=error")

    conn = get_db_connection()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='attendance'")
        cols = [r[0] for r in c.fetchall()]
    else:
        c.execute("PRAGMA table_info(attendance)")
        cols = [r[1] for r in c.fetchall()]

    # Duplicate check similar to /scan
    if subj and branch and 'subject' in cols and 'branch' in cols:
        c.execute("SELECT * FROM attendance WHERE roll=? AND date=? AND subject=? AND branch=?", (roll, date, subj, branch))
    elif subj and 'subject' in cols:
        c.execute("SELECT * FROM attendance WHERE roll=? AND date=? AND subject=?", (roll, date, subj))
    elif branch and 'branch' in cols:
        c.execute("SELECT * FROM attendance WHERE roll=? AND date=? AND branch=?", (roll, date, branch))
    else:
        c.execute("SELECT * FROM attendance WHERE roll=? AND date=?", (roll, date))
    if c.fetchone():
        conn.close()
        return redirect(f"/admin?added=exists")

    # Insert including available columns
    if 'subject' in cols and 'branch' in cols:
        c.execute("INSERT INTO attendance (roll, name, date, time, subject, branch) VALUES (?,?,?,?,?,?)",
                  (roll, name, date, time, subj, branch))
    elif 'subject' in cols:
        c.execute("INSERT INTO attendance (roll, name, date, time, subject) VALUES (?,?,?,?,?)",
                  (roll, name, date, time, subj))
    elif 'branch' in cols:
        c.execute("INSERT INTO attendance (roll, name, date, time, branch) VALUES (?,?,?,?,?)",
                  (roll, name, date, time, branch))
    else:
        c.execute("INSERT INTO attendance (roll, name, date, time) VALUES (?,?,?,?)",
                  (roll, name, date, time))
    conn.commit()
    conn.close()
    return redirect(f"/admin?added=1")

# ---------- DELETE RECORD ----------
@app.route("/delete")
def delete():
    if "admin" not in session:
        return redirect("/")
    roll = request.args.get("roll")
    date = request.args.get("date")
    time = request.args.get("time")
    subject = request.args.get("subject")
    if not (roll and date and time):
        return redirect("/view")
    conn = get_db_connection()
    c = conn.cursor()
    if subject:
        c.execute("DELETE FROM attendance WHERE roll=? AND date=? AND time=? AND subject=?", (roll, date, time, subject))
    else:
        c.execute("DELETE FROM attendance WHERE roll=? AND date=? AND time=?", (roll, date, time))
    conn.commit()
    conn.close()
    # preserve subject filter when redirecting
    if subject:
        return redirect(f"/view?sub={urllib.parse.quote_plus(subject)}")
    return redirect("/view")

# ---------- CLEAR ALL ATTENDANCE ----------
@app.route("/clear_all", methods=["POST"])
def clear_all():
    if "admin" not in session:
        return redirect("/")
    subject = request.form.get('subject') or ''
    branch = request.form.get('branch') or ''
    conn = get_db_connection()
    c = conn.cursor()
    if subject and branch:
        c.execute("SELECT * FROM attendance WHERE subject=? AND branch=?", (subject, branch))
    elif subject:
        c.execute("SELECT * FROM attendance WHERE subject=?", (subject,))
    elif branch:
        c.execute("SELECT * FROM attendance WHERE branch=?", (branch,))
    else:
        c.execute("SELECT * FROM attendance")
    data = c.fetchall()
    backup_name = ''
    if data:
        os.makedirs(os.path.join("static","backups"), exist_ok=True)
        backup_name = datetime.datetime.now().strftime(f"attendance_{subject}_{branch}_backup_%Y%m%d_%H%M%S.csv") if subject and branch else datetime.datetime.now().strftime(f"attendance_{subject or branch}_backup_%Y%m%d_%H%M%S.csv") if subject or branch else datetime.datetime.now().strftime("attendance_backup_%Y%m%d_%H%M%S.csv")
        backup_path = os.path.join("static","backups", backup_name)
        with open(backup_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # include columns if present
            if data and len(data[0]) > 4:
                writer.writerow(["Roll", "Name", "Subject", "Date", "Time"])
            else:
                writer.writerow(["Roll", "Name", "Date", "Time"])
            writer.writerows(data)
    if subject and branch:
        c.execute("DELETE FROM attendance WHERE subject=? AND branch=?", (subject, branch))
    elif subject:
        c.execute("DELETE FROM attendance WHERE subject=?", (subject,))
    elif branch:
        c.execute("DELETE FROM attendance WHERE branch=?", (branch,))
    else:
        c.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()
    if backup_name:
        return redirect(f"/view?cleared=1&backup={urllib.parse.quote_plus(backup_name)}&sub={urllib.parse.quote_plus(subject)}&branch={urllib.parse.quote_plus(branch)}")
    else:
        return redirect(f"/view?cleared=2&sub={urllib.parse.quote_plus(subject)}&branch={urllib.parse.quote_plus(branch)}")

# ---------- EXPORT CSV ----------
@app.route("/export")
def export():
    if "admin" not in session:
        return redirect("/")
    selected_subject = request.args.get('sub') or ''
    selected_branch = request.args.get('branch') or ''
    conn = get_db_connection()
    c = conn.cursor()
    if selected_subject and selected_branch:
        c.execute("SELECT * FROM attendance WHERE subject=? AND branch=? ORDER BY date DESC, time DESC", (selected_subject, selected_branch))
    elif selected_subject:
        c.execute("SELECT * FROM attendance WHERE subject=? ORDER BY date DESC, time DESC", (selected_subject,))
    elif selected_branch:
        c.execute("SELECT * FROM attendance WHERE branch=? ORDER BY date DESC, time DESC", (selected_branch,))
    else:
        c.execute("SELECT * FROM attendance ORDER BY date DESC, time DESC")
    data = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    # Include headers based on available columns
    header = ["Roll", "Name", "Date", "Time"]
    if data and len(data[0]) > 4:
        header.append("Subject")
    if data and len(data[0]) > 5:
        header.append("Branch")
    writer.writerow(header)
    writer.writerows(data)

    filename = "attendance.csv"
    if selected_subject:
        filename = f"attendance_{selected_subject}.csv"
    if selected_branch:
        filename = f"attendance_{selected_branch}.csv"

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)