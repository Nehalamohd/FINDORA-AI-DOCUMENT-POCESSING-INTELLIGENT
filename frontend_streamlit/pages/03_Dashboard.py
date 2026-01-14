import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import APIClient, require_auth

st.set_page_config(page_title="Dashboard", page_icon="📊")

require_auth()

st.title("📊 Dashboard")
st.write(f"Welcome, **{st.session_state.get('username', 'User')}**!")

api = APIClient()

# --- Create New Flow / Upload ---
with st.expander("Create New Flow / Upload Document", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("New Flow")
        new_flow_name = st.text_input("Flow Name")
        if st.button("Create Empty Flow"):
            if new_flow_name:
                res = api.create_flow(new_flow_name)
                if "flow_id" in res:
                    st.success(f"Flow '{res['name']}' created!")
                    st.rerun()
                else:
                    st.error("Failed to create flow")
    
    with col2:
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader("Choose a Document (PDF or PPTX)", type=["pdf", "pptx"])
        upload_flow_name = st.text_input("Flow Name for Document (Optional)")
        
        if st.button("Upload & Process"):
            if uploaded_file:
                with st.spinner("Uploading and processing..."):
                    res = api.upload_document(uploaded_file.getvalue(), uploaded_file.name, upload_flow_name)
                    if "task_id" in res:
                        st.success(f"File uploaded! Task ID: {res['task_id']}")
                        st.info("Processing started. You can check status or go to chat.")
                    else:
                        st.error(f"Upload failed: {res.get('error')}")

st.divider()

# --- List Flows ---
st.subheader("Your Flows")

flows = api.get_my_flows()

if not flows:
    st.info("No flows found. Create one above!")
else:
    for flow in flows:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(f"**{flow['name']}**")
        with col2:
            st.caption(flow['created_at'])
        with col3:
            if st.button("Chat", key=flow['flow_id']):
                st.session_state["current_flow_id"] = flow['flow_id']
                st.session_state["current_flow_name"] = flow['name']
                st.switch_page("pages/04_Chat.py")
#When Chat button is clicked:
#Saves selected flow info in session state
#Switches to the Chat page
#Chat page can know which flow to chat with