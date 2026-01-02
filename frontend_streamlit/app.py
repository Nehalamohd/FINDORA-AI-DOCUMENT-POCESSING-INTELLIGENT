import streamlit as st

st.set_page_config(
    page_title="Findora AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Findora AI Assistant")

if "token" not in st.session_state:
    st.info("👋 Welcome! Please **Login** or **Register** using the sidebar to continue.")
    st.markdown("""
    ### Features
    - 📄 **Upload Documents**: Analyze document contents (PDF, PPTX).
    - 🧠 **RAG Chat**: Ask questions about your documents.
    - 🔐 **Secure**: User-isolated workspaces (Flows).
    """)
else:
    st.success(f"✅ Logged in as **{st.session_state.get('username', 'User')}**")
    st.markdown("### 🚀 Go to **Dashboard** to manage your flows.")
