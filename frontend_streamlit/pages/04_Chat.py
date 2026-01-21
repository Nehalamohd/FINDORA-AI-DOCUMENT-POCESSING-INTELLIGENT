"""
Chat interface for interactive RAG conversations with documents.
"""
import streamlit as st # Force reload
import sys
import os
import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import APIClient, require_auth
import importlib
import utils
importlib.reload(utils)

st.set_page_config(page_title="Chat", page_icon="💬")

require_auth()

if "current_flow_id" not in st.session_state:
    st.warning("No flow selected. Please go to Dashboard.")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/03_Dashboard.py")
    st.stop()

# Read flow id stored in session state
flow_id = st.session_state["current_flow_id"]
flow_name = st.session_state.get("current_flow_name", "Unknown Flow")

st.title(f"💬 Chat: {flow_name}")

api = APIClient()

# Initialize chat history from DB if not already in session
if "messages" not in st.session_state or not st.session_state.messages:
    session_id = st.session_state.get("current_session_id")
    if session_id:
        with st.spinner("Loading chat history..."):
            try:
                history = api.get_chat_history(session_id)
                if history:
                    st.session_state.messages = history
                else:
                    st.session_state.messages = []
            except Exception as e:
                logger.error(f"Failed to load chat history for session {session_id}: {str(e)}")
                st.error("Error loading chat history.")
                st.session_state.messages = []
    else:
        st.session_state.messages = []

# Model Selection in Sidebar
with st.sidebar:
    st.header("Settings")
    model_option = st.selectbox(
        "Select AI Model",
        ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"],
        index=0
    )
    if st.button("Review Document"):
        st.switch_page("pages/05_Document_Review.py")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for s in message["sources"]:
                    st.markdown(f"- **{s['filename']}** (Page {s.get('page_number', '?')})")

# React to user input
if prompt := st.chat_input("Ask a question about your documents..."):
    logger.info(f"User {st.session_state.get('username')} sent chat message for flow {flow_id}: '{prompt[:50]}...'")
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    session_id = st.session_state.get("current_session_id")
    
    with st.chat_message("assistant"):
        # Use streaming
        response = api.chat_stream(prompt, flow_id, session_id, model=model_option)
        
        sources_container = {"data": None}
        if hasattr(response, 'iter_content'):
            import json
            def stream_data():
                # We expect __SOURCES__:{...}\n as the first part
                first_chunk = True
                for chunk in response.iter_content(chunk_size=None):
                    if chunk:
                        text_chunk = chunk.decode("utf-8")
                        if first_chunk and text_chunk.startswith("__SOURCES__:"):
                            try:
                                parts = text_chunk.split("\n", 1)
                                sources_json = parts[0].replace("__SOURCES__:", "")
                                sources_container["data"] = json.loads(sources_json)
                                if len(parts) > 1 and parts[1]:
                                    yield parts[1]
                            except Exception as json_e:
                                logger.error(f"Failed to parse sources JSON in stream: {str(json_e)}")
                                yield text_chunk
                            first_chunk = False
                        elif text_chunk.startswith("__ERROR__:"):
                            error_msg = text_chunk.replace("__ERROR__:", "")
                            logger.error(f"Chat stream error for flow {flow_id}: {error_msg}")
                            st.error(f"Stream Error: {error_msg}")
                            return
                        else:
                            yield text_chunk
            
            try:
                full_response = st.write_stream(stream_data())
                sources = sources_container["data"]
                # Save assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": full_response, "sources": sources})
                
                if sources:
                    with st.expander("Sources"):
                        for s in sources:
                            st.markdown(f"- **{s['filename']}** (Page {s.get('page_number', '?')})")
            except Exception as stream_ui_e:
                logger.error(f"UI Error during stream rendering: {str(stream_ui_e)}")
                st.error("The chat stream was interrupted. Please try re-sending your message.")
        else:
            error_msg = response.get('error', 'Unknown error')
            logger.error(f"Chat request failed for flow {flow_id}: {error_msg}")
            st.error(f"Error: {error_msg}")
