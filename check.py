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
import json
from groq import Groq

# Load environment variables
load_dotenv(override=True)  # Force reloading of the .env file

def send_email(email_body, user):
    try:
        # Email configuration
        smtp_host = "smtp.elasticemail.com"
        smtp_port = 2525  # or 587 if you prefer TLS
        sender_email = "psych9841@gmail.com"
        receiver_email = "psych9841@gmail.com"
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
        print(sender_email)
        print(password)
        return False
    
send_email("email_body", "st.session_state[]")