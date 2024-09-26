import streamlit as st
import sqlite3
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import os
import json

from groq import Groq

# Load environment variables
load_dotenv()


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

# Function to send email
def send_email(recipient, subject, body):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, message.as_string())
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

# Streamlit App Setup
st.set_page_config(page_title="Student Chatbot and Test Creator", layout="wide")

# Initialize session state variables
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

# Sidebar Navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Chatbot", "Create Test"])


# Chatbot Interface (Updated from main.py)
if page == "Chatbot":
    st.header("Student Chatbot Interface")
    user_input = st.text_input("Ask me a question:", key="input")
    submit_query = st.button("Submit")

    if submit_query and user_input:
        st.subheader("Chatbot Response:")
        try:
            # Get response from Gemini model
            response = get_gemini_response(user_input, gemini_prompt)
            st.write(response)
        except Exception as e:
            st.error(f"Error: {e}")

if page == "Chatbot":
    st.header("Student Chatbot Interface")
    user_input = st.text_input("Ask me a question:", key="input")
    submit_query = st.button("Submit")

    if submit_query and user_input:
        st.subheader("Chatbot Response:")
        try:
            response = get_gemini_response(user_input)
            st.write(response)
        except Exception as e:
            st.error(f"Error: {e}")

# Create Test Interface
elif page == "Create Test":
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

    student_email = st.text_input("Student Email")
    teacher_email = st.text_input("Teacher Email")

    submit_test = st.button("Create Test")

    if submit_test:
        st.write("Creating test...")
        
        subjects = st.session_state.get('selected_subjects', [])
        chapters = st.session_state.get('selected_chapters', [])
        difficulty_levels = st.session_state.get('difficulty', [])

        subject_condition = "SUBJECT IN ({})".format(", ".join(f"'{s}'" for s in subjects)) if subjects else "1=1"
        chapter_condition = "CHAPTER IN ({})".format(", ".join(f"'{ch}'" for ch in chapters)) if chapters else "1=1"
        difficulty_condition = "DIFFICULTY IN ({})".format(", ".join(f"'{d}'" for d in difficulty_levels)) if difficulty_levels else "1=1"

        sql_query = f"""
        SELECT SUBJECT, CHAPTER, DIFFICULTY, IMAGE, ans FROM STUDENT 
        WHERE {subject_condition}
        AND {chapter_condition}
        AND {difficulty_condition}
        ORDER BY RANDOM()
        LIMIT {num_questions};
        """
        
        try:
            data = read_sql_query(sql_query, "test.db")
            if data:
                st.session_state.test_questions = data
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
        # Display timer in the main content area
        time_left = max(st.session_state.end_time - time.time(), 0)
        st.write(f"Time left: {int(time_left // 60)}:{int(time_left % 60):02d}")

        if time_left <= 0:
            st.session_state.test_completed = True
            st.rerun()

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
            st.rerun()

    if st.session_state.test_completed:
        st.header("Test Completed")
        score = 0
        total_questions = len(st.session_state.test_questions)

        for i, question in enumerate(st.session_state.test_questions):
            user_answer = st.session_state.user_answers.get(i, "Not answered")
            if user_answer == question['ans']:
                score += 1

        st.write(f"Your score: {score} out of {total_questions}")

        st.subheader("Detailed Results")
        results = []
        for i, question in enumerate(st.session_state.test_questions):
            user_answer = st.session_state.user_answers.get(i, "Not answered")
            results.append(f"Question {i+1}:")
            results.append(f"Your answer: {user_answer}")
            results.append(f"Correct answer: {question['ans']}")
            results.append("---")

        # Send email to student and teacher
        scorecard = "\n".join(results)
        email_body = f"Test Results\n\nScore: {score} out of {total_questions}\n\n{scorecard}"
        
        if send_email(student_email, "Your Test Results", email_body):
            st.success("Scorecard sent to student's email.")
        if send_email(teacher_email, "Student Test Results", email_body):
            st.success("Scorecard sent to teacher's email.")

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
        st.write(f"Number of questions: {num_questions}")
        st.write(f"Timer duration: {timer_duration} minutes")
        st.write(f"User answers: {st.session_state.user_answers}")
        st.write(f"Test completed: {st.session_state.test_completed}")