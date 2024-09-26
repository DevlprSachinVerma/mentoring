import streamlit as st
import sqlite3
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import os
import random

# Configuration
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
EMAIL_ADDRESS = "sachinverma70076@gmail.com"
EMAIL_PASSWORD = "mlpnko890"
TEACHER_EMAIL = "sachin_v@me.iitr.ac.in"

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Database setup
def init_db():
    conn = sqlite3.connect('test_app.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password, email):
    hashed_password = hash_password(password)
    conn = sqlite3.connect('test_app.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                  (username, hashed_password, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user(username, password):
    hashed_password = hash_password(password)
    conn = sqlite3.connect('test_app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user is not None

def get_user_email(username):
    conn = sqlite3.connect('test_app.db')
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username=?", (username,))
    email = c.fetchone()
    conn.close()
    return email[0] if email else None

# Function to send email
def send_email(recipient, subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# Function to get a response from the Gemini model
def get_gemini_response(question, prompt=None):
    model = genai.GenerativeModel('gemini-flash')
    response = model.generate_content([question])
    return response.text

# Function to retrieve data from the database using an SQL query
def read_sql_query(sql, db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

# Function to display image from BLOB data
def display_image(image_data):
    try:
        image = Image.open(BytesIO(image_data))
        st.image(image, caption="Question Image", use_column_width=True)
    except Exception as e:
        st.error(f"Error displaying image: {e}")

# Streamlit App Setup
st.set_page_config(page_title="Student Test Application", layout="wide")

# Initialize session state variables
if 'user' not in st.session_state:
    st.session_state.user = None
if 'test_questions' not in st.session_state:
    st.session_state.test_questions = []
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'test_completed' not in st.session_state:
    st.session_state.test_completed = False
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'end_time' not in st.session_state:
    st.session_state.end_time = None

# Initialize database
init_db()

# Authentication
def login_signup():
    st.sidebar.header("Authentication")
    action = st.sidebar.radio("Choose action", ["Login", "Sign Up"])
    
    if action == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if check_user(username, password):
                st.session_state.user = username
                st.sidebar.success("Logged in successfully!")
                st.rerun()
            else:
                st.sidebar.error("Invalid username or password")
    else:
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        email = st.sidebar.text_input("Email")
        if st.sidebar.button("Sign Up"):
            if add_user(username, password, email):
                st.sidebar.success("Account created successfully! Please login.")
            else:
                st.sidebar.error("Username already exists")

# Main app logic
if st.session_state.user is None:
    login_signup()
else:
    st.sidebar.success(f"Logged in as {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Main content
    st.title("Student Test Application")

    # Test creation and taking logic
    if not st.session_state.test_completed:
        st.header("Create a Student Test")
        
        subject_chapters = {
            "Math": ["Algebra", "Calculus", "Geometry"],
            "Physics": ["Mechanics", "Optics", "Thermodynamics"],
            "Chemistry": ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry"]
        }

        if 'available_chapters' not in st.session_state:
            st.session_state.available_chapters = []

        def update_chapters():
            selected_subjects = st.session_state.selected_subjects
            available_chapters = []
            if selected_subjects:
                for subject in selected_subjects:
                    available_chapters.extend(subject_chapters[subject])
            st.session_state.available_chapters = available_chapters

        st.multiselect("Select Subjects", list(subject_chapters.keys()), key="selected_subjects", on_change=update_chapters)
        st.multiselect("Select Chapters", st.session_state.available_chapters, key="selected_chapters")
        difficulty_levels = st.multiselect("Select Difficulty", ["Easy", "Medium", "Hard"], key="difficulty")
        
        num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=10)
        timer_duration = st.number_input("Test Duration (minutes)", min_value=1, max_value=180, value=30)

        if st.button("Create Test"):
            subjects = st.session_state.get('selected_subjects', [])
            chapters = st.session_state.get('selected_chapters', [])
            difficulty_levels = st.session_state.get('difficulty', [])

            subject_condition = "SUBJECT IN ({})".format(", ".join(f"'{s}'" for s in subjects)) if subjects else "1=1"
            chapter_condition = "CHAPTER IN ({})".format(", ".join(f"'{ch}'" for ch in chapters)) if chapters else "1=1"
            difficulty_condition = "DIFFICULTY IN ({})".format(", ".join(f"'{d}'" for d in difficulty_levels)) if difficulty_levels else "1=1"

            sql_query = f"""
            SELECT * FROM STUDENT 
            WHERE {subject_condition}
            AND {chapter_condition}
            AND {difficulty_condition}
            ORDER BY RANDOM()
            """
            
            try:
                all_questions = read_sql_query(sql_query, "test.db")
                if all_questions:
                    # Ensure we don't select more questions than available
                    num_questions = min(num_questions, len(all_questions))
                    st.session_state.test_questions = random.sample(all_questions, num_questions)
                    st.session_state.user_answers = {}
                    st.session_state.test_completed = False
                    st.session_state.start_time = time.time()
                    st.session_state.end_time = st.session_state.start_time + (timer_duration * 60)
                    st.rerun()
                else:
                    st.warning("No questions found for the selected criteria.")
            except Exception as e:
                st.error(f"Error accessing database: {e}")

    if st.session_state.test_questions and not st.session_state.test_completed:
        st.header("Take the Test")
        
        # Display timer
        placeholder = st.empty()
        while time.time() < st.session_state.end_time:
            time_left = max(st.session_state.end_time - time.time(), 0)
            placeholder.text(f"Time left: {int(time_left // 60)}:{int(time_left % 60):02d}")
            
            total_q = len(st.session_state.test_questions)
            
            for i, question in enumerate(st.session_state.test_questions):
                st.subheader(f"Question {i + 1} of {total_q}")
                st.write(f"Subject: {question['SUBJECT']}, Chapter: {question['CHAPTER']}, Difficulty: {question['DIFFICULTY']}")

                if question['IMAGE']:
                    display_image(question['IMAGE'])

                options = ['A', 'B', 'C', 'D']
                user_answer = st.radio(f"Select your answer for Question {i+1}:", 
                                       options, 
                                       key=f"q_{i}",
                                       index=None)
                
                if user_answer:
                    st.session_state.user_answers[i] = user_answer

                st.write("---")

            if st.button("Submit Test"):
                st.session_state.test_completed = True
                break

            time.sleep(0.1)  # Small delay to prevent excessive updates
        
        if time.time() >= st.session_state.end_time:
            st.session_state.test_completed = True
            st.warning("Time's up! The test has been automatically submitted.")
        
        st.rerun()

    if st.session_state.test_completed:
        st.header("Test Completed")
        score = sum(1 for i, q in enumerate(st.session_state.test_questions)
                    if st.session_state.user_answers.get(i) == q['ans'])
        total_questions = len(st.session_state.test_questions)
        
        st.write(f"Your score: {score} out of {total_questions}")

        # Detailed results
        st.subheader("Detailed Results")
        for i, question in enumerate(st.session_state.test_questions):
            st.write(f"Question {i+1}:")
            user_answer = st.session_state.user_answers.get(i, "Not answered")
            st.write(f"Your answer: {user_answer}")
            st.write(f"Correct answer: {question['ans']}")
            st.write("---")

        # Send email
        user_email = get_user_email(st.session_state.user)
        
        scorecard = f"Student: {st.session_state.user}\nScore: {score}/{total_questions}\n"
        scorecard += "\nDetailed Results:\n"
        for i, question in enumerate(st.session_state.test_questions):
            user_answer = st.session_state.user_answers.get(i, "Not answered")
            scorecard += f"Q{i+1}: Your answer: {user_answer}, Correct answer: {question['ans']}\n"

        if send_email(user_email, "Your Test Results", scorecard) and send_email(TEACHER_EMAIL, f"Test Results for {st.session_state.user}", scorecard):
            st.success("Test results have been sent to your email and the teacher.")
        else:
            st.error("Failed to send email. Please check the email configuration.")

        if st.button("Start New Test"):
            st.session_state.test_questions = []
            st.session_state.user_answers = {}
            st.session_state.test_completed = False
            st.session_state.start_time = None
            st.session_state.end_time = None
            st.rerun()

    # Debugging information (optional)
    if st.checkbox("Show Debug Info"):
        st.write("Debug: Current selections")
        st.write(f"Selected subjects: {st.session_state.get('selected_subjects', [])}")
        st.write(f"Selected chapters: {st.session_state.get('selected_chapters', [])}")
        st.write(f"Selected difficulty: {st.session_state.get('difficulty', [])}")
        st.write(f"Number of questions: {len(st.session_state.test_questions)}")
        st.write(f"User answers: {st.session_state.user_answers}")
        st.write(f"Test completed: {st.session_state.test_completed}")