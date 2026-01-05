import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import APIClient

st.set_page_config(page_title="Register", page_icon="📝")

st.title("📝 Register New Account")

username = st.text_input("Username")
email = st.text_input("Email (Optional)")
password = st.text_input("Password", type="password")
confirm_password = st.text_input("Confirm Password", type="password")


#if the user clicked the "Register" button
if st.button("Register"):
    #Ensures the user entered both a username and a password
    if not username or not password:
        st.error("Username and Password are required")
    elif password != confirm_password:
        st.error("Passwords do not match")
    else:
        #talks to the backend API to register the user
        api = APIClient()
        #Sends registration details to backend
        result = api.register(username, password, email)
        
        if "user_id" in result:
            st.success("Registration successful! Please go to the **Login** page.")
        else:
            st.error(f"Registration failed: {result.get('error', 'Unknown error')}")
