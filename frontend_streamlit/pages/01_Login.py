
"""
About page providing information and features of the Findora AI Assistant.
"""
import streamlit as st
import sys
import os
import logging

logger = logging.getLogger(__name__)

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
        try:
            # class that handles requests to your backend
            api = APIClient()
            result = api.login(username, password)
            
            #check if login was successful
            if "access_token" in result:
                #Stores the access token in Streamlit session state
                st.session_state["token"] = result["access_token"]
                st.session_state["username"] = result.get("username", username) # Store username if available or input
                # Try to get user info to confirm
                # st.session_state["username"] = ...
                logger.info(f"Login successful for user: {username}")
                st.success("Login successful! Go to Dashboard.")
            else:
                logger.error(f"Login failed for user {username}: {result.get('error', 'Unknown error')}")
                st.error(f"Login failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Unexpected error during login for {username}: {str(e)}")
            st.error("An unexpected error occurred. Please try again later.")
