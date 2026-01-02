import streamlit as st
import sys
import os

# Allow importing from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import APIClient

st.set_page_config(page_title="Login", page_icon="🔑")

st.title("🔑 Login")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if not username or not password:
        st.error("Please enter both username and password")
    else:
        api = APIClient()
        result = api.login(username, password)
        
        if "access_token" in result:
            st.session_state["token"] = result["access_token"]
            st.session_state["username"] = result.get("username", username) # Store username if available or input
            # Try to get user info to confirm
            # st.session_state["username"] = ...
            st.success("Login successful! Go to Dashboard.")
        else:
            st.error(f"Login failed: {result.get('error', 'Unknown error')}")
