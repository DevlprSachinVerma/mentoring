import streamlit as st
import sqlite3
from PIL import Image
from io import BytesIO
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import json
from groq import Groq

# Load environment variables
load_dotenv(override=True)

def load_credentials():
    with open("credentials.json", "r") as file:
        return json.load(file)

# Student credentials dictionary
STUDENT_CREDENTIALS = load_credentials()

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

def creds_entered():
    user = st.session_state["user"].strip()
    passwd = st.session_state["passwd"].strip()
    
    if user in STUDENT_CREDENTIALS and STUDENT_CREDENTIALS[user] == passwd:
        st.session_state["authenticated"] = True
        st.session_state["student_id"] = user
    else:
        st.session_state["authenticated"] = False
        st.error("Now Enter Correct Password")

def authenticate_user():
    if "authenticated" not in st.session_state:
        st.text_input(label="Username:", value="", key="user", on_change=creds_entered)
        st.text_input(label="Password:", value="", key="passwd", type="password", on_change=creds_entered)
        return False
    else:
        if st.session_state["authenticated"]:
            return True
        else:
            st.text_input(label="Username:", value="", key="user", on_change=creds_entered)
            st.text_input(label="Password:", value="", key="passwd", type="password", on_change=creds_entered)
            return False

# New function to send email
def send_email(email_body, user):
    try:
        # Email configuration
        smtp_host = "smtp.elasticemail.com"
        smtp_port = 2525  # or 587 if you prefer TLS
        sender_email = os.getenv("EMAIL_PASSWORD")
        receiver_email = os.getenv("EMAIL_PASSWORD")
        password = os.getenv("EMAIL_PASSWORD")  # Store this securely in your .env file

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = "Test Results"

        # Attach the email body
        message.attach(MIMEText(email_body + "\n\nUser: " + user, "plain"))

        # Create SMTP session
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()  # Enable TLS
            server.login(sender_email, password)
            server.send_message(message)
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

if authenticate_user():
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

    # Chatbot Interface
    if page == "Chatbot":
        st.header("Student Chatbot Interface")
        working_dir = os.path.dirname(os.path.abspath(__file__))
        config_data = json.load(open(f"{working_dir}/config.json"))

        GROQ_API_KEY = config_data["GROQ_API_KEY"]
        # save the api key to environment variable
        os.environ["GROQ_API_KEY"] = GROQ_API_KEY
        client = Groq()

        # initialize the chat history as streamlit session state of not present already
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # input field for user's message:
        user_prompt = st.chat_input("Ask LLAMA...")
        if user_prompt:
            st.chat_message("user").markdown(user_prompt)
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})

            # send user's message to the LLM and get a response
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "system", "content": "Give details in brief. Try to keep answer within 100 and 200 words"},
                *st.session_state.chat_history
            ]

            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=messages
            )

            assistant_response = response.choices[0].message.content
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})

            # display the LLM's response
            with st.chat_message("assistant"):
                st.markdown(assistant_response)

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
            SELECT SUBJECT, CHAPTER, DIFFICULTY, IMAGE, opt1, opt2, opt3, opt4, ans FROM STUDENT 
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

                options = [
                    'A',
                    'B',
                    'C',
                    'D'
                ]
                
                user_answers = st.multiselect(
                    f"Select your answer(s) for Question {i+1}:",
                    options,
                    format_func=lambda x: f"{x}",
                    key=f"q_{i}"
                )
                
                if user_answers:
                    st.session_state.user_answers[i] = "".join(sorted(user_answers))

                st.write("---")

            if st.button("Submit Test"):
                st.session_state.test_completed = True
                st.rerun()

        if st.session_state.test_completed:
            st.header("Test Completed")
            score = 0
            total_questions = len(st.session_state.test_questions)

            for i, question in enumerate(st.session_state.test_questions):
                user_answer = st.session_state.user_answers.get(i, "")
                if user_answer == question['ans']:
                    score += 1

            st.write(f"Your score: {score*4} out of {total_questions*4}")

            st.subheader("Detailed Results")
            results = []
            for i, question in enumerate(st.session_state.test_questions):
                user_answer = st.session_state.user_answers.get(i, "")
                correct_answer = question['ans']
                
                st.write(f"Question {i+1}:")
                st.write(f"Subject: {question['SUBJECT']}, Chapter: {question['CHAPTER']}, Difficulty: {question['DIFFICULTY']}")
                
                if question['IMAGE']:
                    display_image(question['IMAGE'])
                
                options = [
                    'A',
                    'B',
                    'C',
                    'D'
                ]
                
                for option in options:
                    if option in user_answer and option in correct_answer:
                        st.write(f":green[{option}] (Your answer - Correct)")
                    elif option in user_answer and option not in correct_answer:
                        st.write(f":red[{option}] (Your answer - Incorrect)")
                    elif option not in user_answer and option in correct_answer:
                        st.write(f":green[{option}] (Correct answer - Not selected)")
                    else:
                        st.write(f"{option}")
                
                st.write("---")
                
                results.append(f"Question {i+1}:")
                results.append(f"Your answer: {user_answer}")
                results.append(f"Correct answer: {correct_answer}")
                results.append("---")

            # Send email to student and teacher
            scorecard = "\n".join(results)
            email_body = f"Test Results\n\nScore: {score} out of {total_questions}\n\n{scorecard}"
            send_email(email_body, st.session_state["student_id"])
            
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