import streamlit as st

st.set_page_config(
    page_title="Findora AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Findora AI Assistant")

if "token" not in st.session_state:
    st.info("👋 Welcome! Please **Login** or **Register** using the sidebar to continue.")
    
    if st.button("✨ Learn more about Findora AI"):
        st.switch_page("pages/00_About_Findora.py")

    st.markdown("""
    ### Features
    - 📄 **Upload Documents**: Analyze document contents (PDF, PPTX).
    - 🧠 **RAG Chat**: Ask questions about your documents.
    - 🔐 **Secure**: User-isolated workspaces (Flows).
    """)
else:
    st.success(f"✅ Logged in as **{st.session_state.get('username', 'User')}**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Go to Dashboard"):
            st.switch_page("pages/03_Dashboard.py")
    with col2:
        if st.button("🌟 About Findora AI"):
            st.switch_page("pages/00_About_Findora.py")
