from flask import Flask, render_template, request, redirect, url_for, session
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
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS teachers
                   (
                       username
                       TEXT
                       PRIMARY
                       KEY,
                       name
                       TEXT,
                       email
                       TEXT,
                       password
                       TEXT
                   )
                   ''')
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS students
                   (
                       usn
                       TEXT
                       PRIMARY
                       KEY,
                       name
                       TEXT
                   )
                   ''')
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS attendance_log
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       date
                       TEXT,
                       usn
                       TEXT,
                       name
                       TEXT,
                       subject
                       TEXT,
                       section
                       TEXT
                   )
                   ''')

    cursor.execute("SELECT COUNT(*) FROM teachers")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO teachers VALUES (?, ?, ?, ?)", [
            ("demo_teacher", "Demo Teacher", "demo@example.com", "demo123")
        ])

    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO students VALUES (?, ?)", [
            ("DEMO001", "Demo Student 1"),
            ("DEMO002", "Demo Student 2"),
            ("DEMO003", "Demo Student 3"),
            ("DEMO004", "Demo Student 4"),
            ("DEMO005", "Demo Student 5")
        ])
    conn.commit()
    conn.close()


init_db()

current_attendance = {
    "subject": "", "section": "", "otp": "", "start_time": 0, "present_students": {}
}


def generate_otp():
    return str(random.randint(100000, 999999))


def otp_remaining_seconds():
    if current_attendance["start_time"] == 0:
        return 0
    elapsed = int(time.time() - current_attendance["start_time"])
    return max(0, 120 - elapsed)


def is_otp_valid():
    return otp_remaining_seconds() > 0


@app.route("/")
def index():
    return redirect(url_for("teacher_login"))


@app.route("/teacher-login", methods=["GET", "POST"])
def teacher_login():
    message = ""
    if request.method == "POST":
        input_user = request.form.get("username", "").lower().strip()
        input_gmail = request.form.get("gmail", "").lower().strip()
        input_password = request.form.get("password", "").strip()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, password FROM teachers WHERE username = ?", (input_user,))
        row = cursor.fetchone()
        conn.close()

        if row and row[2] == input_password and row[1] == input_gmail:
            session["teacher_logged_in"] = True
            session["teacher_name"] = row[0]
            session["teacher_email"] = row[1]
            return redirect(url_for("setup_class"))
        else:
            message = "Invalid Username, Gmail, or Password combination."
    return render_template("teacher_login.html", message=message)


@app.route("/setup-class", methods=["GET", "POST"])
def setup_class():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login"))
    if request.method == "POST":
        current_attendance["subject"] = request.form.get("subject")
        current_attendance["section"] = request.form.get("section")
        current_attendance["otp"] = generate_otp()
        current_attendance["start_time"] = time.time()
        current_attendance["present_students"] = {}
        return redirect(url_for("teacher_dashboard"))
    return render_template("setup_class.html")


@app.route("/teacher-dashboard")
def teacher_dashboard():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login"))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    conn.close()

    # Optimized counters calculate directly from RAM state instead of database processing
    present_count = len(current_attendance["present_students"])
    absent_count = max(0, total_students - present_count)
    percentage = round((present_count / total_students) * 100, 1) if total_students > 0 else 0.0

    return render_template(
        "teacher_dashboard.html",
        attendance=current_attendance, total_students=total_students,
        present_count=present_count, absent_count=absent_count,
        percentage=percentage, remaining=otp_remaining_seconds()
    )


@app.route("/refresh-otp", methods=["POST"])
def refresh_otp():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login"))
    current_attendance["otp"] = generate_otp()
    current_attendance["start_time"] = time.time()
    return redirect(url_for('teacher_dashboard'))


@app.route("/student", methods=["GET", "POST"])
def student_dashboard():
    message = ""
    success_message = ""
    is_locked_out = False
    today_date = datetime.now().strftime("%Y-%m-%d")

    # Persistent anti-proxy device handshake tracking
    if session.get("last_submission_date") == today_date:
        is_locked_out = True

    if request.method == "POST":
        input_usn = request.form.get("usn", "").upper().strip()
        input_otp = request.form.get("otp", "").strip()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE usn = ?", (input_usn,))
        student_row = cursor.fetchone()

        if not current_attendance["otp"]:
            message = "No active attendance tracking session found."
        elif is_locked_out:
            message = "Proxy Blocked! This device is already registered for an attendance log today."
        elif not student_row:
            message = "Student USN Not Found! Please check your credentials."
        elif not is_otp_valid():
            message = "The active attendance OTP has expired!"
        elif input_otp != current_attendance["otp"]:
            message = "Incorrect OTP code. Look at the board and try again."
        elif input_usn in current_attendance["present_students"]:
            message = f"Submission Blocked: USN {input_usn} has already checked in today!"
        else:
            student_name = student_row[0]
            current_attendance["present_students"][input_usn] = student_name

            cursor.execute(
                "INSERT INTO attendance_log (date, usn, name, subject, section) VALUES (?, ?, ?, ?, ?)",
                (today_date, input_usn, student_name, current_attendance["subject"], current_attendance["section"])
            )
            conn.commit()

            session["submitted_usn"] = input_usn
            session["last_submission_date"] = today_date
            is_locked_out = True

            success_message = f"Verified profile: {student_name}."

        conn.close()

    return render_template(
        "student_attendance.html",
        message=message,
        success_message=success_message,
        attendance=current_attendance,
        is_locked_out=is_locked_out
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("teacher_login"))


if __name__ == "__main__":
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "0.0.0.0"
    app.run(debug=True, host="0.0.0.0", port=5000)