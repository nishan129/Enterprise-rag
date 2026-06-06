import os
import streamlit as st
import requests
import time
import uuid
import logfire
from dotenv import load_dotenv

# ── Environment ─────────────────────────────────────────────────────────────
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)

# ── Logfire ──────────────────────────────────────────────────────────────────
try:
    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        print("ERROR: LOGFIRE_TOKEN is empty or None!")
    logfire.configure(token=token)
    LOGFIRE_STATUS = "Connected"
except Exception as e:
    print(f"Logfire Init Error in UI: {e}")
    LOGFIRE_STATUS = f"Standby"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise RAG",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Tokens ─────────────────────────────────────────── */
:root {
  --bg:       #0f172a;
  --surface:  #1e293b;
  --border:   #334155;
  --text:     #f8fafc;
  --muted:    #94a3b8;
  --primary:  #6366f1;
  --primary-d:#4f46e5;
  --radius:   12px;
  --radius-sm: 8px;
}

/* ── Global reset ────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'DM Sans', 'Segoe UI', sans-serif;
}

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background-color: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
  color: var(--text) !important;
}
[data-testid="stSidebarContent"] {
  padding: 1.5rem 1rem !important;
}

/* ── Main content wrapper ────────────────────────────── */
.main .block-container {
  max-width: 860px !important;
  margin: 0 auto !important;
  padding: 1.5rem 1.25rem 6rem !important;
}

/* ── Hide default Streamlit chrome ───────────────────── */
#MainMenu, footer, header { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Chat messages ───────────────────────────────────── */
[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin-bottom: 0.25rem !important;
}
[data-testid="stChatMessageContent"] {
  background: transparent !important;
}

/* User bubble */
[data-testid="stChatMessage"][data-testid*="user"] .stMarkdown,
.user-bubble {
  background: var(--primary) !important;
  color: #fff !important;
  border-radius: 18px 18px 4px 18px !important;
  padding: 0.75rem 1rem !important;
  display: inline-block;
  max-width: 78%;
  float: right;
  clear: both;
}

/* Assistant bubble */
.assistant-bubble {
  background: var(--surface) !important;
  border: 1px solid var(--border);
  border-radius: 18px 18px 18px 4px !important;
  padding: 0.75rem 1rem !important;
  display: inline-block;
  max-width: 82%;
  float: left;
  clear: both;
  line-height: 1.65;
}

.msg-row { overflow: hidden; margin-bottom: 1rem; }

/* ── Input area ──────────────────────────────────────── */
[data-testid="stChatInputContainer"] {
  background-color: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 0.15rem 0.5rem !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.35) !important;
}
[data-testid="stChatInputContainer"] textarea {
  background: transparent !important;
  color: var(--text) !important;
  font-size: 0.95rem !important;
}
[data-testid="stChatInputContainer"] textarea::placeholder {
  color: var(--muted) !important;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  font-size: 0.85rem !important;
  padding: 0.5rem 1rem !important;
  width: 100% !important;
  transition: background 0.15s, border-color 0.15s !important;
}
.stButton > button:hover {
  background: var(--border) !important;
  border-color: var(--muted) !important;
}

/* ── Status box ─────────────────────────────────────── */
[data-testid="stStatusWidget"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--muted) !important;
}

/* ── Expanders (sources) ─────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  margin-top: 0.5rem !important;
}
[data-testid="stExpander"] summary {
  color: var(--muted) !important;
  font-size: 0.82rem !important;
}

/* ── Info / success / error pills ────────────────────── */
[data-testid="stAlert"] {
  border-radius: var(--radius-sm) !important;
  font-size: 0.82rem !important;
}

/* ── Sidebar metadata pills ──────────────────────────── */
.meta-pill {
  background: var(--border);
  border-radius: 6px;
  padding: 0.35rem 0.65rem;
  font-size: 0.78rem;
  color: var(--muted);
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.meta-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #22c55e;
  flex-shrink: 0;
}
.meta-dot.warn { background: #f59e0b; }

/* ── Welcome screen ──────────────────────────────────── */
.welcome-wrap {
  text-align: center;
  padding: 5rem 1rem 2rem;
  max-width: 560px;
  margin: 0 auto;
}
.welcome-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}
.welcome-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 0.5rem;
}
.welcome-sub {
  color: var(--muted);
  font-size: 0.95rem;
  margin-bottom: 2.5rem;
  line-height: 1.6;
}
.example-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  max-width: 420px;
  margin: 0 auto;
}
.example-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.65rem 0.85rem;
  font-size: 0.83rem;
  color: var(--muted);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.example-card:hover {
  border-color: var(--primary);
  color: var(--text);
}

/* ── Source cards ────────────────────────────────────── */
.source-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.65rem 0.85rem;
  margin-bottom: 0.5rem;
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.55;
}
.source-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--primary);
  margin-bottom: 0.25rem;
  font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ── Session ───────────────────────────────────────────────────────────────────
def init_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        logfire.info(f"New session: {st.session_state.session_id}")
    if "messages" not in st.session_state:
        st.session_state.messages = []


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### ◆ Enterprise RAG")
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        dot_class = "meta-dot" if "Connected" in LOGFIRE_STATUS else "meta-dot warn"
        st.markdown(
            f"<div class='meta-pill'><span class='{dot_class}'></span>Logfire · {LOGFIRE_STATUS}</div>",
            unsafe_allow_html=True,
        )
        short_id = st.session_state.session_id[:8]
        st.markdown(
            f"<div class='meta-pill'><span style='opacity:.5'>◈</span>Session · {short_id}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        if st.button("🗑  Clear Chat", key="clear"):
            logfire.warn(f"Memory wipe: {st.session_state.session_id}")
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()


# ── Welcome screen ────────────────────────────────────────────────────────────
def render_welcome():
    st.markdown("""
    <div class='welcome-wrap'>
      <div class='welcome-icon'>◆</div>
      <div class='welcome-title'>Enterprise Agentic RAG</div>
      <div class='welcome-sub'>
        Ask questions across your organisation's knowledge base.<br>
        Get answers grounded in your documentation.
      </div>
      <div class='example-grid'>
        <div class='example-card'>Summarise our documentation</div>
        <div class='example-card'>Explain the architecture</div>
        <div class='example-card'>Search company knowledge</div>
        <div class='example-card'>Find relevant information</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Chat history ──────────────────────────────────────────────────────────────
def render_chat_history():
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f"<div class='msg-row'><div class='user-bubble'>{msg['content']}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='msg-row'><div class='assistant-bubble'>{msg['content']}</div></div>",
                unsafe_allow_html=True,
            )


# ── Backend call ──────────────────────────────────────────────────────────────
def call_backend(prompt: str) -> dict:
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    url = f"{base_url}/query"
    payload = {"q": prompt, "thread_id": st.session_state.session_id}
    with logfire.span("Calling RAG backend"):
        response = requests.post(url, json=payload, timeout=60)
    return response.json()


# ── Sources ───────────────────────────────────────────────────────────────────
def render_sources(sources: list):
    if not sources:
        return
    with st.expander(f"📄 Sources ({len(sources)} chunks)", expanded=False):
        for i, source in enumerate(sources):
            preview = source[:200].replace("\n", " ")
            st.markdown(
                f"<div class='source-card'>"
                f"<div class='source-label'>Chunk {i + 1}</div>"
                f"{preview}{'…' if len(source) > 200 else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )


# ── Streaming response ────────────────────────────────────────────────────────
def stream_response(placeholder, full_answer: str):
    curr = ""
    for char in full_answer:
        curr += char
        placeholder.markdown(
            f"<div class='msg-row'><div class='assistant-bubble'>{curr}▌</div></div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.005)
    placeholder.markdown(
        f"<div class='msg-row'><div class='assistant-bubble'>{full_answer}</div></div>",
        unsafe_allow_html=True,
    )


# ── App entrypoint ────────────────────────────────────────────────────────────
def main():
    init_session()
    render_sidebar()

    if not st.session_state.messages:
        render_welcome()
    else:
        render_chat_history()

    if prompt := st.chat_input("Ask anything about your documents…"):
        with logfire.span("User chat interaction", query=prompt, session=st.session_state.session_id):

            # User bubble
            st.markdown(
                f"<div class='msg-row'><div class='user-bubble'>{prompt}</div></div>",
                unsafe_allow_html=True,
            )
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Thinking status
            with st.status("Thinking…", expanded=True) as status:
                try:
                    data = call_backend(prompt)
                    for step in data.get("thought_process", []):
                        st.write(f"⚙ {step}")
                    status.update(label="Done", state="complete", expanded=False)
                except Exception as e:
                    logfire.error(f"Backend error: {e}")
                    status.update(label="Connection failed", state="error")
                    st.error("Could not reach the backend. Is it running?")
                    st.stop()

            # Stream answer
            answer = data.get("answer", "No response.")
            placeholder = st.empty()
            stream_response(placeholder, answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

            # Sources
            render_sources(data.get("sources", []))

            logfire.info("Chat cycle complete.")


if __name__ == "__main__":
    main()