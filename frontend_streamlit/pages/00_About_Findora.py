"""
About page providing information and features of the Findora AI Assistant.
"""
import streamlit as st
import sys
import os

# Set page config for a premium look
st.set_page_config(
    page_title="About Findora AI",
    page_icon="🌟",
    layout="wide"
)

# Custom Styling for a modern, sleek look
st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.5rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .feature-card {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid #4facfe;
        height: 100%;
        transition: transform 0.3s ease;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .tech-pill {
        display: inline-block;
        background: #e1f5fe;
        color: #01579b;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown('<h1 class="main-title">Findora AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Intelligence. Insights. Instant Clarity.</p>', unsafe_allow_html=True)

st.markdown("---")

# Mission Section
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Our Mission")
    st.write("""
        Findora AI was built to solve the **information overload** problem. 
        In a world full of dense documents, spreadsheets, and complex presentations, 
        we provide a bridge between raw data and actionable knowledge.
        
        Our platform doesn't just "read" your files; it **understands** them, 
        **analyzes** their quality, and **predicts** how they can be better.
    """)
    
    st.header("The Experience")
    st.info("💡 **Pro-Tip**: Use the 'Document Review' feature to get a 1-10 quality score on any document flow.")

with col2:
    # Reverted to previous Unsplash image as requested
    st.image("https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800", caption="AI Powered Analysis")

st.markdown("---")

# Feature Section
st.header("Key Capabilities")
f_col1, f_col2 = st.columns(2)
f_col3, f_col4 = st.columns(2)

with f_col1:
    st.markdown("""
    <div class="feature-card">
        <h3>💬 Smart RAG Chat</h3>
        <p>Talk to your documents in plain English. Our advanced retrieval system finds the exact context you need.</p>
        <ul>
            <li>Streaming responses</li>
            <li>Interactive source citations</li>
            <li>Persistent chat memory</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with f_col2:
    st.markdown("""
    <div class="feature-card">
        <h3>📋 AI Reviewer</h3>
        <p>Proactive document analysis that identifies gaps and predicts improvements automatically.</p>
        <ul>
            <li>Predictive quality scoring</li>
            <li>Gap identification</li>
            <li>Innovation suggestions</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with f_col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🌐 Hybrid Search</h3>
        <p>If the answer isn't in your document, we securely bridge the gap with real-time web search.</p>
        <ul>
            <li>Cross-document reasoning</li>
            <li>Real-time web verification</li>
            <li>Seamless fallback logic</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with f_col4:
    st.markdown("""
    <div class="feature-card" style="border-left-color: #ff9800;">
        <h3>🚀 Parallel Ingestion</h3>
        <p>Optimized for large files and architectural plans using high-speed concurrent processing.</p>
        <ul>
            <li>10x faster processing</li>
            <li>Smart text extraction</li>
            <li>Multi-worker page analysis</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Tech Stack Section
st.header("The Tech Stack")
st.write("Findora AI is powered by an elite selection of cutting-edge technologies:")

tech_col1, tech_col2 = st.columns(2)

with tech_col1:
    st.subheader("Compute & LLMs")
    st.markdown("""
    <span class="tech-pill">Groq LPU™ Inference</span>
    <span class="tech-pill">Llama 3.3 (70B)</span>
    <span class="tech-pill">Llama 4 Scout (Vision)</span>
    """, unsafe_allow_html=True)

with tech_col2:
    st.subheader("Infrastructure")
    st.markdown("""
    <span class="tech-pill">FastAPI</span>
    <span class="tech-pill">PGVector (PostgreSQL)</span>
    <span class="tech-pill">Celery Parallel Workers</span>
    <span class="tech-pill">Redis Task Broker</span>
    """, unsafe_allow_html=True)

import logging
logger = logging.getLogger(__name__)

st.sidebar.markdown("---")
if st.sidebar.button("Go to Login"):
    try:
        st.switch_page("app.py")
    except Exception as e:
        logger.error(f"Navigation to app.py failed: {str(e)}")
if st.sidebar.button("Go to Dashboard"):
    try:
        st.switch_page("pages/03_Dashboard.py")
    except Exception as e:
        logger.error(f"Navigation to Dashboard failed: {str(e)}")
