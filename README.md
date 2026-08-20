# Online Smart Attendance System Using Dynamic OTP

A beginner-friendly **Python Flask** web application for managing classroom attendance using a time-limited 6-digit OTP.

## Features

- Teacher login
- Subject and section selection
- Dynamic 6-digit OTP generation
- OTP validity for 2 minutes
- Student attendance using USN/ID and OTP
- Wrong and expired OTP rejection
- Duplicate attendance prevention
- Teacher dashboard with attendance statistics

## Technologies Used

- Python
- Flask
- SQLite
- HTML
- CSS

## Project Structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── templates/
└── static/
```

## How to Run Locally

1. Install Python 3.
2. Open a terminal in the project folder.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set a local secret key if desired:

**Windows PowerShell**
```powershell
$env:SECRET_KEY="your-local-secret"
```

5. Run the application:

```bash
python app.py
```

6. Open:

```text
http://127.0.0.1:5000/teacher-login
```

Student attendance page:

```text
http://127.0.0.1:5000/student
```

## Demo Login

For demonstration purposes, the project seeds a sample teacher account:

- Username: `demo_teacher`
- Email: `demo@example.com`
- Password: `demo123`

Sample student IDs:

- `DEMO001`
- `DEMO002`
- `DEMO003`
- `DEMO004`
- `DEMO005`

> These are demo credentials only. Change authentication and secret management before using the application in a real environment.

## Project Description

The system starts with teacher authentication. After login, the teacher selects the subject and section, and the application generates a dynamic OTP. Students enter their student ID and the active OTP on the attendance page. The system validates the OTP, checks whether it has expired, and prevents duplicate submissions. The teacher dashboard displays attendance statistics.

## Future Improvements

- Secure password hashing
- User registration and role-based access
- Production database
- Better authentication and authorization
- Cloud deployment
- Responsive UI improvements
