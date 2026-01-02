import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import APIClient, require_auth

st.set_page_config(page_title="Chat", page_icon="💬")

require_auth()

if "current_flow_id" not in st.session_state:
    st.warning("No flow selected. Please go to Dashboard.")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/03_Dashboard.py")
    st.stop()

flow_id = st.session_state["current_flow_id"]
flow_name = st.session_state.get("current_flow_name", "Unknown Flow")

st.title(f"💬 Chat: {flow_name}")

api = APIClient()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask a question about your documents..."):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get session_id if exists
    session_id = st.session_state.get("current_session_id")

    with st.spinner("Thinking..."):
        response = api.chat(prompt, flow_id, session_id)
        
        if "answer" in response:
            answer = response["answer"]
            # Save session_id if returned
            if "session_id" in response:
                st.session_state["current_session_id"] = response["session_id"]
            
            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            error_msg = response.get('error', 'Unknown error')
            st.error(f"Error: {error_msg}")
