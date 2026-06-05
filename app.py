import os
import streamlit as st
import requests
import time
import uuid
import logfire
from dotenv import load_dotenv


# Load environment variables explicitly from the roote directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=env_path)

# Initialize logfire
try:
    token = os.getenv("LOGIFIRE_TOKEN")
    if not token:
        print("ERROR: LOGIFIRE_TOKEN is empty or None!")
    logfire.configure(token=token)
    # logfire.instrument_requests() # Disabled due to OpenTelemetry bug
    LOGFIRE_STATUS = "Connected & Tracing"
except Exception as e:
    print(f"Logfire Init Error in UI: {e}")
    LOGFIRE_STATUS = f"Standby (Error:{e})"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Enerprise Agentic RAG",
    page_icon="🤖",
    layout="wide"
)

# --- AVATARS ---
AI_AVTAR = "🤖"
USER_AVTAR = "🧑‍🦱"

# --- SESSIOn MANAGEMENT 000
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logfire.info(f"✨ New User Session Created: {st.session_state.session_id}")

if 'messages' not in st.session_state:
    st.session_state.messages = []

# -- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Agent OS")
    st.markdown("---")
    st.success(f"Logfire: {LOGFIRE_STATUS}")
    st.info(f"Memory ID: {st.session_state.session_id[:8]}")

    if st.button("🗑️ Clear History & Memory", width='stretch', type='primary'):
        logfire.warn(f"🗑️ Memory Wipe Triggered for session: {st.session_state}")
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


# --- MAIN CHAT ---
st.title("🤖 Enterprise Agentic Assistant")

# Display history
for message in st.session_state.messages:
    avatar = AI_AVTAR if message['role'] == "assistant" else USER_AVTAR
    with st.chat_message(message['role'], avatar=avatar):
        st.markdown(message['content'])