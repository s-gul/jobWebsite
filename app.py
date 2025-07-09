from flask import Flask, request, session, render_template, redirect, url_for, jsonify
import sqlite3
from datetime import datetime
import smtplib
import secrets
import uuid
import string
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

DATABASE = os.getenv('DATABASE_PATH')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

@app.route("/", methods=["GET"])
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    is_logged_in = 'user' in session
    print(f"User logged in: {is_logged_in}")

    # Retrieve search query, filters, and date posted from the request
    search_query = request.args.get("query", "").strip()
    filters = {
        "remote": request.args.get("remote"),
        "hybrid": request.args.get("hybrid"),
    }
    date_posted = request.args.get("date_posted", "").strip()

    print(f"Search Query: {search_query}")
    print(f"Filters: {filters}")
    print(f"Date Posted: {date_posted}")

    # Build the SQL query dynamically based on search query, filters, and date posted
    sql_query = "SELECT * FROM jobs WHERE 1=1"
    sql_params = []

    # Add search query conditions
    if search_query:
        sql_query += " AND (title LIKE ? OR company LIKE ?)"
        sql_params.extend([f"%{search_query}%", f"%{search_query}%"])

    # Add filter conditions
    filter_conditions = []
    for filter_key, filter_value in filters.items():
        if filter_value:
            filter_conditions.append(f"{filter_key} = 1")

    if filter_conditions:
        sql_query += " AND (" + " OR ".join(filter_conditions) + ")"

    # Add date posted filter
    if date_posted == "24_hours":
        sql_query += " AND date_posted >= datetime('now', '-1 day')"
    elif date_posted == "few_days":
        sql_query += " AND date_posted >= datetime('now', '-3 days')"
    elif date_posted == "last_week":
        sql_query += " AND date_posted >= datetime('now', '-7 days')"
    elif date_posted == "last_two_weeks":
        sql_query += " AND date_posted >= datetime('now', '-14 days')"

    sql_query += " ORDER BY date_posted DESC LIMIT 5"

    # Execute the query with parameters
    cursor.execute(sql_query, sql_params)
    jobs = cursor.fetchall()
    conn.close()

    return render_template("home.html", jobs=jobs, filters=filters, query=search_query, date_posted=date_posted, is_logged_in=is_logged_in)

@app.route("/load_jobs", methods=["GET"])
def load_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve pagination parameters
    offset = int(request.args.get("offset", 5))  # Starting point for jobs
    limit = int(request.args.get("limit", 5))   # Number of jobs to load per request

    # Retrieve search query, filters, and date posted from the request
    search_query = request.args.get("query", "").strip()
    filters = {
        "remote": request.args.get("remote"),
        "hybrid": request.args.get("hybrid"),
    }
    date_posted = request.args.get("date_posted", "").strip()

    # Build the SQL query dynamically based on search query, filters, and date posted
    sql_query = "SELECT * FROM jobs WHERE 1=1"
    sql_params = []

    # Add search query conditions
    if search_query:
        sql_query += " AND (title LIKE ? OR company LIKE ?)"
        sql_params.extend([f"%{search_query}%", f"%{search_query}%"])

    # Add filter conditions
    filter_conditions = []
    for filter_key, filter_value in filters.items():
        if filter_value:
            filter_conditions.append(f"{filter_key} = 1")

    if filter_conditions:
        sql_query += " AND (" + " OR ".join(filter_conditions) + ")"

    # Add date posted filter
    if date_posted == "24_hours":
        sql_query += " AND date_posted >= datetime('now', '-1 day')"
    elif date_posted == "few_days":
        sql_query += " AND date_posted >= datetime('now', '-3 days')"
    elif date_posted == "last_week":
        sql_query += " AND date_posted >= datetime('now', '-7 days')"
    elif date_posted == "last_two_weeks":
        sql_query += " AND date_posted >= datetime('now', '-14 days')"

    # Add pagination
    sql_query += " ORDER BY date_posted DESC LIMIT ? OFFSET ?"
    sql_params.extend([limit, offset])

    # Execute the query
    cursor.execute(sql_query, sql_params)
    jobs = cursor.fetchall()
    conn.close()

    # Convert jobs to a list of dictionaries for JSON response
    jobs_list = [dict(job) for job in jobs]

    return jsonify(jobs_list)

@app.route('/save_job', methods=['POST'])
def save_job():
    if 'user' not in session:
        # Return a 401 Unauthorized response if the user is not logged in
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    job_id = data.get('job_id')

    if not job_id:
        return jsonify({"error": "Invalid job ID"}), 400
    
    # Save the job to the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if the job is already saved
    cursor.execute(
        "SELECT * FROM saved_jobs WHERE user_id = (SELECT id FROM users WHERE email = ?) AND job_id = ?",
        (session['user'], job_id)
    )

    if cursor.fetchone():
        conn.close()
        return jsonify({"message": "Job already saved"}), 200
    
    # Insert the saved job into the database
    cursor.execute(
        "INSERT INTO saved_jobs (user_id, job_id) VALUES ((SELECT id FROM users WHERE email = ?), ?)",
        (session['user'], job_id)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Job saved successfully"}), 200

@app.route('/apply_job', methods=['POST'])
def apply_job():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    job_id = data.get('job_id')

    if not job_id:
        return jsonify({"error": "Invalid job ID"}), 400
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch the user_id using the email from the session
    cursor.execute("SELECT id FROM users WHERE email = ?", (session['user'],))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    user_id = user[0]
    
    # Check if the job is already applied
    cursor.execute(
        "SELECT * FROM applied_jobs WHERE user_id = ? AND job_id = ?",
        (user_id, job_id)
    )
    duplicate_job = cursor.fetchone()
    if duplicate_job:
        conn.close()
        return jsonify({"message": "Job already applied"}), 200
    
    # Insert the applied job into the database
    # Fetch job details from the jobs table
    cursor.execute("""
        SELECT title, company, location, remote, hybrid, url
        FROM jobs
        WHERE id = ?
    """, (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        return jsonify({"error": "Job not found"}), 404
    
    job_title, company, location, remote, hybrid, apply_link = job

    # Insert the applied job into the database
    cursor.execute("""
        INSERT INTO applied_jobs (id, job_id, user_id, job_title, company, location, remote, hybrid, apply_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),  # Generate a unique ID for the applied job
        job_id, # Job ID
        user_id,    # User ID
        job_title,          # Job title
        company,            # Company
        location,           # Location
        bool(remote),       # Remote (convert to boolean)
        bool(hybrid),       # Hybrid (convert to boolean)
        apply_link          # Apply link
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Job marked as applied successfully"}), 200

def send_email(to_email, code):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = app.secret_key  # Use an App Password for security

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        subject = "Your Login Code"
        body = f"Your login code is: {code}"
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(sender_email, to_email, message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']

        # Generate a random code
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))

        # Save the code to the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO auth_codes (email, code) VALUES (?, ?)", (email, code))
        conn.commit()
        conn.close()

        # Send the code via email
        try:
            send_email(email, code)
        except Exception as e:
            return jsonify({"success": False, "message": f"Failed to send email: {str(e)}"}), 500

    # Return a success response
    return jsonify({"success": True, "message": "Login code sent successfully"})

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        email = request.form['email']
        code = request.form['code']

        # Verify the code
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM auth_codes WHERE email = ?", (email,))
        result = cursor.fetchone()

        if result and result[0] == code:
            # Check if the user already exists in the users table
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user_exists = cursor.fetchone()

            if not user_exists:
                # Add the user to the users table
                cursor.execute("INSERT INTO users (id, email) VALUES (?, ?)", (str(uuid.uuid4()), email))
                conn.commit()

            # Delete the code from the auth_codes table (regardless of success or failure)
            cursor.execute("DELETE FROM auth_codes WHERE email = ?", (email,))
            conn.commit()

            conn.close()

            # Log the user in
            session['user'] = email
            return redirect(url_for('dashboard'))
        else:
            # Delete the code from the auth_codes table (regardless of success or failure)
            cursor.execute("DELETE FROM auth_codes WHERE email = ?", (email,))
            conn.commit()

            conn.close()
            return jsonify({"success": False, "message": "Invalid code"}), 400

@app.route('/dashboard', methods=["GET"])
def dashboard():
    # if 'user' not in session:
    #     return redirect(url_for('home'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable attribute-style access
    cursor = conn.cursor()

    # Fetch saved jobs for the logged-in user
    cursor.execute("""
        SELECT jobs.id, jobs.description, jobs.title, jobs.company, jobs.location, jobs.remote, jobs.hybrid, jobs.date_posted, jobs.url
        FROM saved_jobs
        JOIN jobs ON saved_jobs.job_id = jobs.id
        WHERE saved_jobs.user_id = (SELECT id FROM users WHERE email = ?)
    """, (session['user'],))
    saved_jobs = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM applied_jobs
        JOIN jobs ON applied_jobs.job_id = jobs.id
        WHERE applied_jobs.user_id = (SELECT id FROM users WHERE email = ?)
    """, (session['user'],))
    applied_jobs = cursor.fetchall()

    conn.close()

    return render_template('dashboard.html', saved_jobs=saved_jobs, applied_jobs=applied_jobs, filters={}, query="", date_posted="")

@app.route('/delete_saved_job', methods=['POST'])
def delete_saved_job():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    job_id = data.get('job_id')

    if not job_id:
        return jsonify({"error": "Invalid job ID"}), 400
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Delete the saved job from the database
    cursor.execute("""
        DELETE FROM saved_jobs
        WHERE user_id = (SELECT id FROM users WHERE email = ?) AND job_id = ?
    """, (session['user'], job_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Job deleted successfully"}), 200

@app.route('/delete_applied_job', methods=['POST'])
def delete_applied_job():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    job_id = data.get('job_id')

    if not job_id:
        return jsonify({"error": "Invalid job ID"}), 400
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Delete the applied job from the database
    cursor.execute("""
        DELETE FROM applied_jobs
        WHERE user_id = (SELECT id FROM users WHERE email = ?) AND job_id = ?
    """, (session['user'], job_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Applied job deleted successfully"}), 200

if __name__  == "__main__":
    app.run(DEBUG = False)