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
from groq import Groq
from datetime import datetime, timedelta
import json
import threading
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.timer import Timer

# Function to initialize the results database
def init_results_db():
    conn = sqlite3.connect('result.db')
    cursor = conn.cursor()
    
    # Create test_results table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            subjects TEXT NOT NULL,
            chapters TEXT NOT NULL,
            difficulty_levels TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()


# Add this to your existing Streamlit app setup
if 'initialized_db' not in st.session_state:
    init_results_db()
    st.session_state.initialized_db = True

# Streamlit App Setup
st.set_page_config(
    page_title="Mentors Mantra", 
    page_icon="Logo.png",  # Change 'logo.png' to your file path or URL
    layout="wide"
)
# Load environment variables
load_dotenv(override=True)

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# Student credentials dictionary
STUDENT_CREDENTIALS = st.secrets["student_credentials"]

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
        st.markdown(
            """
            <h2 style='text-align: center; font-size: 40px;'>Hello, Welcome to 
            <span style='color: purple; font-size: 48px;'>Mentors Mantra!</span> 😄</h2>
            """,
            unsafe_allow_html=True
        )
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



# Function to save test results
def save_test_results(student_id, score, total_questions, subjects, chapters, 
                     difficulty_levels, duration):
    try:
        conn = sqlite3.connect('result.db')
        cursor = conn.cursor()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO test_results (
                student_id, timestamp, score, total_questions, subjects,
                chapters, difficulty_levels, duration_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            student_id,
            timestamp,
            score,
            total_questions,
            json.dumps(subjects),
            json.dumps(chapters),
            json.dumps(difficulty_levels),
            duration
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving test results: {e}")
        return False

# Function to get student performance history
def get_student_performance(student_id):
    conn = sqlite3.connect('result.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, score, total_questions, subjects, chapters, 
               difficulty_levels, duration_minutes
        FROM test_results
        WHERE student_id = ?
        ORDER BY timestamp DESC
    ''', (student_id,))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def create_test_timer(duration_minutes):
    """
    Create a timer using streamlit-extras
    
    Args:
        duration_minutes (int): Total test duration in minutes
    """
    # Create a timer
    timer = Timer(duration_minutes * 60, text="⏰ Time Remaining")
    
    # When timer expires
    if timer.is_expired():
        st.warning("Time's up! Test will be automatically submitted.")
        st.session_state.test_completed = True
        st.rerun()



if authenticate_user():
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
    st.sidebar.header("")
    page = st.sidebar.radio("Go to", ["Chatbot", "Create Test", "View Performance"])

    # Chatbot Interface
    if page == "Chatbot":
        st.header("Student Chatbot Interface")


        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

        client = Groq()

        # initialize the chat history as streamlit session state of not present already
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # input field for user's message:
        user_prompt = st.chat_input("Wanna ask Something....")
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

    if page == "View Performance":
        st.header("Your Test Performance History")
        
        performance_data = get_student_performance(st.session_state["student_id"])
        
        if performance_data:
            st.subheader("Test History")
            for test in performance_data:
                with st.expander(f"Test on {test[0]}"):
                    st.write(f"Score: {test[1]} out of {test[2]*4}")
                    st.write(f"Subjects: {', '.join(json.loads(test[3]))}")
                    st.write(f"Chapters: {', '.join(json.loads(test[4]))}")
                    st.write(f"Difficulty Levels: {', '.join(json.loads(test[5]))}")
                    st.write(f"Duration: {test[6]} minutes")
            
            # Calculate and show statistics
            scores = [test[1] for test in performance_data]
            if scores:
                st.subheader("Performance Statistics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Score", f"{sum(scores)/len(scores):.1f}")
                with col2:
                    st.metric("Highest Score", max(scores))
                with col3:
                    st.metric("Total Tests Taken", len(scores))
        else:
            st.info("No test history available yet. Take a test to see your performance!")
            
    elif page == "Create Test":
        st.header("Create a Test")
        
        # Only show test creation form if no test is in progress
        if not st.session_state.test_questions:
            subject_chapters = {
                "Math": [],
                "Physics": ["Magnetism and Matter"],
                "Chemistry": []
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
                create_test_timer(timer_duration)
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
                        st.session_state.test_saved = False  # Add this flag
                        st.rerun()
                    else:
                        st.warning("No questions found for the selected criteria.")
                except Exception as e:
                    st.error(f"Error accessing database: {e}")


        # Show test questions if test is in progress
        if st.session_state.test_questions and not st.session_state.test_completed:
            # Display timer in the main content area
            

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

        # Test completion and results
        if st.session_state.test_completed:
            if not hasattr(st.session_state, 'test_saved') or not st.session_state.test_saved:
                score = 0
                total_questions = len(st.session_state.test_questions)
                detailed_results = []

                for i, question in enumerate(st.session_state.test_questions):
                    user_answer = st.session_state.user_answers.get(i, "")
                    correct_answer = question['ans']
                    if user_answer == correct_answer:
                        score += 1
                    
                    result_entry = {
                        'question_num': i + 1,
                        'user_answer': user_answer,
                        'correct_answer': correct_answer,
                        'subject': question['SUBJECT'],
                        'chapter': question['CHAPTER'],
                        'difficulty': question['DIFFICULTY']
                    }
                    detailed_results.append(result_entry)

                # Calculate final score and store in session state
                st.session_state.final_score = score * 4
                st.session_state.total_questions = total_questions
                
                # Save results only once
                subjects = list(set(q['SUBJECT'] for q in st.session_state.test_questions))
                chapters = list(set(q['CHAPTER'] for q in st.session_state.test_questions))
                difficulties = list(set(q['DIFFICULTY'] for q in st.session_state.test_questions))
                duration = int((st.session_state.end_time - st.session_state.start_time) / 60)
                
                if save_test_results(
                    st.session_state["student_id"],
                    st.session_state.final_score,
                    st.session_state.total_questions,
                    subjects,
                    chapters,
                    difficulties,
                    duration
                ):
                    st.session_state.test_saved = True
                    st.success("Test results have been saved successfully!")
                else:
                    st.warning("There was an issue saving your test results.")

            # Display results
            st.header("Test Completed")
            st.write(f"Your score: {st.session_state.final_score} out of {st.session_state.total_questions*4}")

            st.subheader("Detailed Results")
            for i, question in enumerate(st.session_state.test_questions):
                user_answer = st.session_state.user_answers.get(i, "")
                correct_answer = question['ans']
                
                st.write(f"Question {i+1}:")
                st.write(f"Subject: {question['SUBJECT']}, Chapter: {question['CHAPTER']}, Difficulty: {question['DIFFICULTY']}")
                
                if question['IMAGE']:
                    display_image(question['IMAGE'])
                
                options = ['A', 'B', 'C', 'D']
                
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

            # Add button to start new test
            if st.button("Start New Test"):
                # Clear all test-related session state variables
                st.session_state.test_questions = []
                st.session_state.user_answers = {}
                st.session_state.test_completed = False
                st.session_state.start_time = None
                st.session_state.end_time = None
                st.session_state.final_score = None
                st.session_state.total_questions = None
                st.session_state.test_saved = False
                st.rerun()
