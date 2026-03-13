import streamlit as st
import pandas as pd
import requests
import uuid
import time

# Page Configuration
st.set_page_config(
    page_title="Lyra Research - Agentic Healthcare Copilot",
    page_icon="🏥",
    layout="wide",
)

# Constants
API_BASE_URL = "http://localhost:8000"

# --- UI Styling ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0c111d;
    }
    .main-header {
        font-family: 'Outfit', sans-serif;
        color: #f0f9ff;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .secondary-text {
        color: #94a3b8;
        font-size: 1rem;
    }
    .disclaimer {
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 0.5rem;
        border-radius: 8px;
        color: #ef4444;
        font-size: 0.8rem;
        text-align: center;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "active_research" not in st.session_state:
    st.session_state.active_research = None

# --- Sidebar (Filters) ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/database.png", width=60)
    st.title("Lyra Research")
    
    st.subheader("🔍 Filters")
    year_from = st.number_input("Year From", min_value=1900, max_value=2026, value=2022)
    year_to = st.number_input("Year To", min_value=1900, max_value=2026, value=2024)
    
    study_types = st.multiselect(
        "Study Types",
        ["Guideline", "Meta-analysis", "RCT", "Cohort", "Case Study", "Preprint"],
        default=["RCT", "Meta-analysis", "Guideline"]
    )
    
    st.divider()
    st.info("💡 Filters are applied during the de-duplicated retrieval phase of the 6-agent pipeline.")

# --- Main Layout ---
# Disclaimer Banner
st.markdown('<div class="disclaimer">⚠️ RESEARCH & EDUCATION ONLY — NOT FOR CLINICAL DECISION MAKING</div>', unsafe_allow_html=True)

col_chat, col_evidence = st.columns([2, 1])

# --- Chat Panel ---
with col_chat:
    st.markdown('<h1 class="main-header">Research Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="secondary-text">Ask a clinical research question to activate the multi-agent pipeline.</p>', unsafe_allow_html=True)

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("What is the latest evidence for..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Triggers research
        with st.chat_message("assistant"):
            with st.spinner("Synthesizing evidence from PubMed via 6-agent pipeline..."):
                try:
                    payload = {
                        "question": prompt,
                        "thread_id": st.session_state.thread_id,
                        "filters": {
                            "year_from": year_from,
                            "year_to": year_to,
                            "study_types": study_types
                        }
                    }
                    response = requests.post(f"{API_BASE_URL}/ask", json=payload, timeout=900)
                    response.raise_for_status()
                    data = response.json()
                    
                    st.session_state.active_research = data
                    answer = data.get("answer", "No answer generated.")
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    error_msg = f"❌ Pipeline Failure: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Evidence Table (below chat)
    if st.session_state.active_research:
        st.divider()
        st.subheader("📊 Evidence Synthesis Table")
        evidence = st.session_state.active_research.get("evidence_table", [])
        if evidence:
            df = pd.DataFrame(evidence)
            # Reorder columns for readability
            cols = ["title", "type", "year", "journal", "source_url"]
            df = df[cols]
            st.dataframe(
                df,
                column_config={
                    "source_url": st.column_config.LinkColumn("Source"),
                },
                use_container_width=True,
                hide_index=True
            )

# --- Right Panel (Citations & Changes) ---
with col_evidence:
    if st.session_state.active_research:
        st.subheader("📜 Verified Citations")
        quotes = st.session_state.active_research.get("quotes", [])
        if quotes:
            for q in quotes:
                with st.expander(f"Source [{q['id']}]"):
                    st.markdown(f"*{q['quote']}*")
                    if q.get('pmid'):
                        st.markdown(f"[View on PubMed](https://pubmed.ncbi.nlm.nih.gov/{q['pmid']})")
        else:
            st.write("No source quotes extracted.")

        st.divider()
        
        st.subheader("✨ What Changed (Last 24mo)")
        changes = st.session_state.active_research.get("changed_in_last_24_months", [])
        if changes:
            for item in changes:
                st.info(f"**{item['year']}**: {item['summary']}")
        else:
            st.write("No major recent breakthroughs identified in this set.")
    else:
        st.write("Results will appear here once research is started.")

# Footer status
st.sidebar.divider()
st.sidebar.caption(f"Backend: {API_BASE_URL}")
st.sidebar.caption(f"Thread ID: {st.session_state.thread_id}")
