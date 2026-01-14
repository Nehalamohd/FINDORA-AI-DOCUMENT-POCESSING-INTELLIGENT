import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import APIClient, require_auth

st.set_page_config(page_title="Document Review", page_icon="📋")

require_auth()

if "current_flow_id" not in st.session_state:
    st.warning("No flow selected. Please go to Dashboard.")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/03_Dashboard.py")
    st.stop()

flow_id = st.session_state["current_flow_id"]
flow_name = st.session_state.get("current_flow_name", "Unknown Flow")

st.title(f"📋 AI Reviewer: {flow_name}")

st.info("Findora AI is analyzing your document flow to predict improvements and identify gaps...")

api = APIClient()

if st.button("Generate/Refresh Review"):
    with st.spinner("Analyzing document content..."):
        result = api.get_review(flow_id)
        if "review" in result:
            st.session_state[f"review_{flow_id}"] = result["review"]
        else:
            st.error(f"Error: {result.get('error', 'Failed to generate review')}")

# Display stored review if available
review_content = st.session_state.get(f"review_{flow_id}")

if review_content:
    st.markdown("---")
    st.markdown(review_content)
    
    # Simple export option
    st.download_button(
        label="Download Review Report",
        data=review_content,
        file_name=f"Review_{flow_name.replace(' ', '_')}.md",
        mime="text/markdown"
    )

st.sidebar.markdown("---")
if st.sidebar.button("Back to Chat"):
    st.switch_page("pages/04_Chat.py")
