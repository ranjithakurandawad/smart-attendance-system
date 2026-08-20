from flask import Flask, request, redirect, url_for, session, render_template_string
import random
import time
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")
DB_FILE = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS teachers (
        username TEXT PRIMARY KEY, name TEXT, email TEXT, password TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS students (
        usn TEXT PRIMARY KEY, name TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS attendance_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, usn TEXT,
        name TEXT, subject TEXT, section TEXT)""")
    if cur.execute("SELECT COUNT(*) FROM teachers").fetchone()[0] == 0:
        cur.execute("INSERT INTO teachers VALUES (?, ?, ?, ?)",
                    ("demo_teacher", "Demo Teacher", "demo@example.com", "demo123"))
    if cur.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        cur.executemany("INSERT INTO students VALUES (?, ?)",
                        [(f"DEMO00{i}", f"Demo Student {i}") for i in range(1, 6)])
    conn.commit()
    conn.close()

init_db()

current_attendance = {
    "subject": "", "section": "", "otp": "",
    "start_time": 0, "present_students": {}
}

def generate_otp():
    return str(random.randint(100000, 999999))

def otp_remaining_seconds():
    if not current_attendance["start_time"]:
        return 0
    return max(0, 120 - int(time.time() - current_attendance["start_time"]))

def is_otp_valid():
    return otp_remaining_seconds() > 0

BASE = """
<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f4f7fb;color:#172033}
.wrap{max-width:900px;margin:40px auto;padding:20px}.card{background:#fff;border-radius:18px;padding:28px;box-shadow:0 8px 30px rgba(0,0,0,.08)}
h1{margin-top:0}.sub,.small{color:#64748b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}
label{display:block;font-weight:700;margin:12px 0 7px}input,select{width:100%;padding:13px;border:1px solid #cbd5e1;border-radius:10px;font-size:16px}
button,.btn{display:inline-block;margin-top:18px;padding:13px 18px;border:0;border-radius:10px;background:#2563eb;color:#fff;font-weight:700;text-decoration:none;cursor:pointer}
button:disabled{opacity:.5;cursor:not-allowed}.secondary{background:#475569}.danger{background:#dc2626}
.otp{font-size:42px;font-weight:800;letter-spacing:8px;text-align:center;padding:20px;background:#eef4ff;border-radius:14px;margin:20px 0}
.msg{padding:12px;border-radius:10px;margin:15px 0;background:#fee2e2;color:#991b1b}.success{background:#dcfce7;color:#166534}
.stat{padding:18px;border-radius:14px;background:#f8fafc}.stat b{font-size:28px;display:block;margin-top:5px}
table{width:100%;border-collapse:collapse;margin-top:18px}th,td{padding:10px;border-bottom:1px solid #e2e8f0;text-align:left}
.actions{display:flex;gap:10px;flex-wrap:wrap}
</style></head><body><div class="wrap"><div class="card">{{ body|safe }}</div></div></body></html>
"""

def page(title, body):
    return render_template_string(BASE, title=title, body=body)

@app.route("/")
def index():
    return redirect(url_for("teacher_login"))

@app.route("/teacher-login", methods=["GET", "POST"])
def teacher_login():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").lower().strip()
        gmail = request.form.get("gmail", "").lower().strip()
        password = request.form.get("password", "").strip()
        conn = sqlite3.connect(DB_FILE)
        row = conn.execute(
            "SELECT name,email,password FROM teachers WHERE username=?",
            (username,)).fetchone()
        conn.close()
        if row and row[2] == password and row[1] == gmail:
            session["teacher_logged_in"] = True
            session["teacher_name"] = row[0]
            session["teacher_email"] = row[1]
            return redirect(url_for("setup_class"))
        message = "Invalid Username, Gmail, or Password combination."

    error = f'<div class="msg">{message}</div>' if message else ""
    body = f"""
    <h1>Teacher Login</h1>
    <p class="sub">Online Smart Attendance System using Dynamic OTP</p>
    {error}
    <form method="post">
      <label>Username</label><input name="username" required>
      <label>Gmail</label><input type="email" name="gmail" required>
      <label>Password</label><input type="password" name="password" required>
      <button type="submit">Login</button>
    </form>
    <p class="small">Demo: demo_teacher / demo@example.com / demo123</p>
    <a class="btn secondary" href="/student">Student Attendance</a>
    """
    return page("Teacher Login", body)

@app.route("/setup-class", methods=["GET", "POST"])
def setup_class():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login"))
    if request.method == "POST":
        current_attendance["subject"] = request.form.get("subject", "").strip()
        current_attendance["section"] = request.form.get("section", "").strip()
        current_attendance["otp"] = generate_otp()
        current_attendance["start_time"] = time.time()
        current_attendance["present_students"] = {}
        return redirect(url_for("teacher_dashboard"))

    body = """
    <h1>Set Up Attendance</h1>
    <p class="sub">Choose the class before generating the OTP.</p>
    <form method="post">
      <label>Subject</label><input name="subject" placeholder="e.g. Python" required>
      <label>Section</label>
      <select name="section" required>
        <option value="">Select section</option><option>A</option><option>B</option><option>C</option>
      </select>
      <button type="submit">Start Attendance</button>
    </form>
    <a class="btn secondary" href="/logout">Logout</a>
    """
    return page("Set Up Attendance", body)

@app.route("/teacher-dashboard")
def teacher_dashboard():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login"))
    conn = sqlite3.connect(DB_FILE)
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    conn.close()
    present = len(current_attendance["present_students"])
    absent = max(0, total_students - present)
    pct = round(present / total_students * 100, 1) if total_students else 0
    rows = "".join(
        f"<tr><td>{usn}</td><td>{name}</td></tr>"
        for usn, name in current_attendance["present_students"].items()
    ) or "<tr><td colspan='2'>No students marked yet.</td></tr>"

    body = f"""
    <h1>Teacher Dashboard</h1>
    <p class="sub">Welcome, {session.get("teacher_name", "Teacher")}</p>
    <p><b>Subject:</b> {current_attendance["subject"] or "-"}
       &nbsp; <b>Section:</b> {current_attendance["section"] or "-"}</p>
    <div class="otp">{current_attendance["otp"] or "------"}</div>
    <p style="text-align:center"><b>OTP expires in {otp_remaining_seconds()} seconds</b></p>
    <div class="grid">
      <div class="stat">Total Students<b>{total_students}</b></div>
      <div class="stat">Present<b>{present}</b></div>
      <div class="stat">Absent<b>{absent}</b></div>
      <div class="stat">Attendance<b>{pct}%</b></div>
    </div>
    <div class="actions">
      <form method="post" action="/refresh-otp"><button>Refresh OTP</button></form>
      <a class="btn secondary" href="/student">Open Student Page</a>
      <a class="btn danger" href="/logout">Logout</a>
    </div>
    <h2>Present Students</h2>
    <table><tr><th>USN</th><th>Name</th></tr>{rows}</table>
    """
    return page("Teacher Dashboard", body)

@app.route("/refresh-otp", methods=["POST"])
def refresh_otp():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login"))
    current_attendance["otp"] = generate_otp()
    current_attendance["start_time"] = time.time()
    return redirect(url_for("teacher_dashboard"))

@app.route("/student", methods=["GET", "POST"])
def student_dashboard():
    message = ""
    success = ""
    today = datetime.now().strftime("%Y-%m-%d")
    locked = session.get("last_submission_date") == today

    if request.method == "POST":
        usn = request.form.get("usn", "").upper().strip()
        otp = request.form.get("otp", "").strip()
        conn = sqlite3.connect(DB_FILE)
        row = conn.execute("SELECT name FROM students WHERE usn=?", (usn,)).fetchone()

        if not current_attendance["otp"]:
            message = "No active attendance tracking session found."
        elif locked:
            message = "This device has already submitted attendance today."
        elif not row:
            message = "Student USN Not Found!"
        elif not is_otp_valid():
            message = "The active attendance OTP has expired!"
        elif otp != current_attendance["otp"]:
            message = "Incorrect OTP code."
        elif usn in current_attendance["present_students"]:
            message = f"USN {usn} has already checked in."
        else:
            name = row[0]
            current_attendance["present_students"][usn] = name
            conn.execute(
                "INSERT INTO attendance_log(date,usn,name,subject,section) VALUES(?,?,?,?,?)",
                (today, usn, name, current_attendance["subject"], current_attendance["section"]))
            conn.commit()
            session["last_submission_date"] = today
            success = f"Attendance verified for {name}."
            locked = True
        conn.close()

    disabled = "disabled" if locked else ""
    error = f'<div class="msg">{message}</div>' if message else ""
    ok = f'<div class="msg success">{success}</div>' if success else ""
    body = f"""
    <h1>Student Attendance</h1>
    <p class="sub">Enter your USN and the active 6-digit OTP shown by the teacher.</p>
    {error}{ok}
    <form method="post">
      <label>Student USN</label><input name="usn" placeholder="DEMO001" required {disabled}>
      <label>OTP</label><input name="otp" inputmode="numeric" maxlength="6"
          placeholder="6-digit OTP" required {disabled}>
      <button type="submit" {disabled}>Mark Attendance</button>
    </form>
    <a class="btn secondary" href="/teacher-login">Teacher Login</a>
    <p class="small">Demo student IDs: DEMO001 to DEMO005</p>
    """
    return page("Student Attendance", body)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("teacher_login"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
