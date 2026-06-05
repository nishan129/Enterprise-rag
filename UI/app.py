"""
Enterprise Agentic RAG — Premium UI
2026 · Built with Streamlit
"""

import os
import time
import uuid
from datetime import datetime

import logfire
import requests
import streamlit as st
from dotenv import load_dotenv

# ═══════════════════════════════════════════════
#  ENV & OBSERVABILITY
# ═══════════════════════════════════════════════
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=env_path)

try:
    token = os.getenv("LOGIFIRE_TOKEN")
    logfire.configure(token=token)
    LOGFIRE_OK = True
    LOGFIRE_STATUS = "Connected"
except Exception as e:
    LOGFIRE_OK = False
    LOGFIRE_STATUS = "Offline"


# ═══════════════════════════════════════════════
#  PAGE CONFIG  (must be first Streamlit call)
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="Enterprise RAG · AI Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════
def lf_span(name: str, **kw):
    if LOGFIRE_OK:
        return logfire.span(name, **kw)
    import contextlib
    return contextlib.nullcontext()


def ts() -> str:
    return datetime.now().strftime("%H:%M")


def call_backend(prompt: str, session_id: str) -> dict:
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    resp = requests.post(
        f"{base_url}/query",
        json={"q": prompt, "thread_id": session_id},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ═══════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    if LOGFIRE_OK:
        logfire.info("New session", session_id=st.session_state.session_id)

if "messages" not in st.session_state:
    st.session_state.messages = []

PALETTE = """
  --bg:#0F172A; --bg2:#0a101e; --surface:#1E293B; --surface2:#253347;
  --panel:#1a2438; --border:#2d3f58; --border-hi:#3d5478;
  --accent:#7C3AED; --accent2:#8B5CF6; --accent3:#A78BFA;
  --accent-glow:rgba(124,58,237,0.35);
  --success:#22C55E; --error:#EF4444; --warning:#F59E0B;
  --text:#F8FAFC; --text2:#CBD5E1; --muted:#94A3B8; --muted2:#64748B;
  --user-bubble:#1e2d4a; --ai-bubble:#16213a;
  --shadow:0 4px 24px rgba(0,0,0,.4); --shadow-lg:0 8px 48px rgba(0,0,0,.6);
"""


# ═══════════════════════════════════════════════
#  GLOBAL CSS
# ═══════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
  {PALETTE}
  --radius-sm:10px; --radius:16px; --radius-lg:24px; --radius-xl:32px;
  --font-head:'Plus Jakarta Sans',sans-serif;
  --font-body:'Inter',sans-serif;
  --font-mono:'JetBrains Mono',monospace;
}}

*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,[data-testid="stAppViewContainer"]{{background:var(--bg)!important;color:var(--text);font-family:var(--font-body);}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]>div{{padding:0!important}}

::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:99px}}
::-webkit-scrollbar-thumb:hover{{background:var(--border-hi)}}

/* ── Sidebar ── */
[data-testid="stSidebar"]{{background:var(--surface)!important;border-right:1px solid var(--border);min-width:272px!important;max-width:272px!important}}

.sb-brand{{padding:26px 22px 20px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,rgba(124,58,237,.08),transparent)}}
.sb-logo{{width:40px;height:40px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;margin-bottom:12px;box-shadow:0 0 20px var(--accent-glow)}}
.sb-name{{font-family:var(--font-head);font-weight:800;font-size:.98rem;color:var(--text);letter-spacing:-.03em}}
.sb-tag{{font-size:.64rem;color:var(--muted);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.1em;margin-top:3px}}

.sb-sec{{padding:16px 18px;border-bottom:1px solid var(--border)}}
.sb-lbl{{font-size:.6rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted2);font-family:var(--font-mono);margin-bottom:10px;font-weight:500}}

.spill{{display:flex;align-items:center;gap:7px;background:var(--panel);border:1px solid var(--border);border-radius:99px;padding:6px 13px;font-size:.73rem;font-family:var(--font-mono);color:var(--text2);margin-bottom:7px}}
.sdot{{width:7px;height:7px;border-radius:50%;flex-shrink:0;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.45}}}}
.ok{{background:var(--success);box-shadow:0 0 7px var(--success)}}
.err{{background:var(--error);box-shadow:0 0 7px var(--error)}}
.inf{{background:var(--accent3);box-shadow:0 0 7px var(--accent3)}}

.stat-row{{display:flex;gap:8px}}
.stat-box{{flex:1;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 10px;text-align:center;transition:border-color .2s}}
.stat-box:hover{{border-color:var(--accent3)}}
.stat-n{{font-family:var(--font-head);font-size:1.55rem;font-weight:800;background:linear-gradient(135deg,var(--accent3),#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1}}
.stat-l{{font-size:.6rem;color:var(--muted);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.08em;margin-top:5px}}

.stButton>button{{width:100%!important;background:transparent!important;color:var(--muted)!important;border:1px solid var(--border)!important;border-radius:var(--radius-sm)!important;padding:9px 14px!important;font-family:var(--font-body)!important;font-size:.83rem!important;font-weight:500!important;transition:all .2s!important}}
.stButton>button:hover{{background:rgba(239,68,68,.08)!important;border-color:var(--error)!important;color:var(--error)!important;transform:translateY(-1px)!important}}

.sb-foot{{padding:14px 18px;font-size:.63rem;color:var(--muted2);font-family:var(--font-mono);line-height:1.65}}

/* ── Topbar ── */
.topbar{{display:flex;align-items:center;justify-content:space-between;padding:17px 44px;border-bottom:1px solid var(--border);background:rgba(15,23,42,.8);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);position:sticky;top:0;z-index:100;flex-shrink:0}}
.t-title{{font-family:var(--font-head);font-size:1.08rem;font-weight:700;color:var(--text);letter-spacing:-.03em}}
.t-sub{{font-size:.71rem;color:var(--muted);font-family:var(--font-mono);margin-top:2px}}
.t-right{{display:flex;align-items:center;gap:8px}}
.chip{{display:inline-flex;align-items:center;gap:4px;background:var(--panel);border:1px solid var(--border);border-radius:99px;padding:5px 12px;font-size:.7rem;font-family:var(--font-mono);color:var(--accent3)}}

/* ── Messages ── */
.msgs-inner{{max-width:820px;margin:0 auto;padding:36px 24px 16px}}

.msg-row{{display:flex;gap:13px;margin-bottom:26px;animation:msgIn .35s cubic-bezier(.16,1,.3,1)}}
@keyframes msgIn{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
.msg-row.user{{flex-direction:row-reverse}}

.av{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.95rem;flex-shrink:0;border:2px solid transparent}}
.av.ai{{background:linear-gradient(135deg,#1e1040,#2d1b69);border-color:var(--accent);box-shadow:0 0 14px var(--accent-glow)}}
.av.user{{background:linear-gradient(135deg,#0d2137,#1a3a5c);border-color:#2d6aad}}

.bw{{display:flex;flex-direction:column;max-width:80%}}
.msg-row.user .bw{{align-items:flex-end}}

.bubble{{padding:15px 19px;border-radius:var(--radius-lg);font-size:.91rem;line-height:1.7;border:1px solid var(--border);word-break:break-word;transition:box-shadow .2s}}
.bubble:hover{{box-shadow:var(--shadow)}}
.bubble.ai{{background:var(--ai-bubble);border-color:var(--border);border-top-left-radius:var(--radius-sm)}}
.bubble.user{{background:var(--user-bubble);border-color:#2d4a7a;border-top-right-radius:var(--radius-sm)}}

.bf{{display:flex;align-items:center;gap:7px;margin-top:7px;font-size:.66rem;font-family:var(--font-mono);color:var(--muted2)}}
.cp{{display:inline-flex;align-items:center;gap:3px;background:var(--panel);border:1px solid var(--border);border-radius:5px;padding:3px 7px;cursor:pointer;font-size:.63rem;color:var(--muted);transition:all .2s}}
.cp:hover{{border-color:var(--accent3);color:var(--accent3)}}

/* ── Thinking ── */
.think-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px 22px;max-width:520px;margin:0 auto 26px;animation:msgIn .3s ease}}
.think-title{{font-family:var(--font-head);font-size:.8rem;font-weight:600;color:var(--text2);margin-bottom:13px;display:flex;align-items:center;gap:8px}}
.step{{display:flex;align-items:center;gap:9px;padding:7px 11px;border-radius:var(--radius-sm);background:var(--panel);border:1px solid var(--border);margin-bottom:7px;font-size:.78rem;font-family:var(--font-mono);color:var(--muted);animation:msgIn .3s ease}}
.step.active{{border-color:var(--accent);color:var(--accent3);background:rgba(124,58,237,.06)}}
.step.done{{border-color:var(--success);color:var(--success);background:rgba(34,197,94,.05)}}

.dots{{display:inline-flex;gap:4px;align-items:center}}
.dot{{width:6px;height:6px;background:var(--accent3);border-radius:50%;animation:db 1.2s infinite}}
.dot:nth-child(2){{animation-delay:.2s}}
.dot:nth-child(3){{animation-delay:.4s}}
@keyframes db{{0%,80%,100%{{transform:translateY(0);opacity:.4}}40%{{transform:translateY(-6px);opacity:1}}}}

/* ── Sources ── */
.src-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin:10px 0}}
.src-hdr{{display:flex;align-items:center;gap:7px;padding:11px 17px;border-bottom:1px solid var(--border);font-size:.76rem;font-family:var(--font-mono);color:var(--muted);background:var(--panel)}}
.src-card{{padding:13px 17px;border-bottom:1px solid var(--border);font-size:.78rem;font-family:var(--font-mono);line-height:1.55}}
.src-card:last-child{{border-bottom:none}}
.src-num{{display:inline-flex;align-items:center;justify-content:center;width:19px;height:19px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:4px;font-size:.58rem;font-weight:700;color:white;margin-right:8px;flex-shrink:0}}
.src-prev{{color:var(--text2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}

/* ── Hero ── */
.hero{{text-align:center;padding:72px 24px 36px;max-width:660px;margin:0 auto}}
.hero-icon{{width:68px;height:68px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:1.9rem;margin:0 auto 26px;box-shadow:0 0 40px var(--accent-glow);animation:float 3s ease-in-out infinite}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
.hero-title{{font-family:var(--font-head);font-size:clamp(1.8rem,4vw,2.5rem);font-weight:800;letter-spacing:-.04em;color:var(--text);line-height:1.15;margin-bottom:15px}}
.hero-title span{{background:linear-gradient(135deg,var(--accent3),#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero-sub{{font-size:.96rem;color:var(--muted);line-height:1.65;max-width:500px;margin:0 auto 36px}}
.qgrid{{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}}
.qcard{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:17px;text-align:left;transition:all .25s cubic-bezier(.16,1,.3,1)}}
.qcard:hover{{border-color:var(--accent3);transform:translateY(-3px);box-shadow:0 8px 32px var(--accent-glow)}}
.qi{{font-size:1.45rem;margin-bottom:9px}}
.qt{{font-family:var(--font-head);font-size:.85rem;font-weight:700;color:var(--text);margin-bottom:4px}}
.qd{{font-size:.73rem;color:var(--muted);line-height:1.5}}

/* ── Input ── */
[data-testid="stChatInput"]{{background:transparent!important}}
[data-testid="stChatInput"]>div{{background:var(--surface)!important;border:1.5px solid var(--border)!important;border-radius:var(--radius-xl)!important;transition:border-color .2s,box-shadow .2s!important}}
[data-testid="stChatInput"]:focus-within>div{{border-color:var(--accent)!important;box-shadow:0 0 0 4px var(--accent-glow)!important}}
[data-testid="stChatInput"] textarea{{font-family:var(--font-body)!important;font-size:.93rem!important;color:var(--text)!important;background:transparent!important;padding:15px 20px!important}}
[data-testid="stChatInput"] textarea::placeholder{{color:var(--muted2)!important}}

.inp-hint{{text-align:center;font-size:.66rem;color:var(--muted2);font-family:var(--font-mono);margin-top:9px}}

/* ── Misc overrides ── */
details{{background:var(--panel)!important;border:1px solid var(--border)!important;border-radius:var(--radius-sm)!important}}
details>summary{{font-family:var(--font-mono)!important;font-size:.78rem!important;color:var(--muted)!important;padding:9px 13px!important}}

@media(max-width:768px){{
  .topbar{{padding:13px 18px}}
  .msgs-inner{{padding:24px 14px 12px}}
  .qgrid{{grid-template-columns:1fr}}
  .bw{{max-width:92%}}
  .hero{{padding:44px 16px 22px}}
  .hero-title{{font-size:1.65rem}}
}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════
msg_count    = len([m for m in st.session_state.messages if m["role"] == "user"])
total_msgs   = len(st.session_state.messages)
logfire_dot  = "ok" if LOGFIRE_OK else "err"
sid_short    = st.session_state.session_id[:8]

with st.sidebar:
    st.markdown(f"""
    <div class="sb-brand">
      <div class="sb-logo">⚡</div>
      <div class="sb-name">Enterprise RAG</div>
      <div class="sb-tag">Agentic AI Assistant · v2.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-sec">', unsafe_allow_html=True)
    st.markdown('<div class="sb-lbl">System Status</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="spill"><span class="sdot {logfire_dot}"></span>Logfire · {LOGFIRE_STATUS}</div>
    <div class="spill"><span class="sdot inf"></span>Session · {sid_short}…</div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-sec">', unsafe_allow_html=True)
    st.markdown('<div class="sb-lbl">Session Analytics</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-box"><div class="stat-n">{msg_count}</div><div class="stat-l">Queries</div></div>
      <div class="stat-box"><div class="stat-n">{total_msgs}</div><div class="stat-l">Messages</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-sec">', unsafe_allow_html=True)
    st.markdown('<div class="sb-lbl">Controls</div>', unsafe_allow_html=True)
    if st.button("🗑️ Clear History & Reset Memory"):
        if LOGFIRE_OK:
            logfire.warn("Memory wipe", session_id=st.session_state.session_id)
        st.session_state.messages   = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sb-foot">Enterprise RAG · 2026<br>PydanticAI + Logfire<br>Session: {st.session_state.session_id[:18]}…</div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  TOPBAR
# ═══════════════════════════════════════════════
st.markdown("""
<div class="topbar">
  <div>
    <div class="t-title">Enterprise Agentic Assistant</div>
    <div class="t-sub">Intelligent retrieval across your entire knowledge base</div>
  </div>
  <div class="t-right">
    <span class="chip">⚡ RAG Mode</span>
    <span class="chip">🧠 Agent v2</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  MESSAGES
# ═══════════════════════════════════════════════
st.markdown('<div class="msgs-inner">', unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("""
    <div class="hero">
      <div class="hero-icon">⚡</div>
      <h1 class="hero-title">Enterprise <span>Agentic RAG</span></h1>
      <p class="hero-sub">
        Ask questions across your organisation's knowledge base and receive
        intelligent, context-aware answers powered by retrieval-augmented generation.
      </p>
      <div class="qgrid">
        <div class="qcard"><div class="qi">📄</div><div class="qt">Documentation</div><div class="qd">Summarize technical docs instantly</div></div>
        <div class="qcard"><div class="qi">🔍</div><div class="qt">Search Knowledge</div><div class="qd">Semantic search across indexed content</div></div>
        <div class="qcard"><div class="qi">📊</div><div class="qt">Analytics</div><div class="qd">Query reports, metrics & business data</div></div>
        <div class="qcard"><div class="qi">⚡</div><div class="qt">Agent Workflows</div><div class="qd">Multi-step agentic reasoning pipelines</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        role    = msg["role"]
        content = msg["content"]
        stamp   = msg.get("ts", "")
        avc     = "ai" if role == "assistant" else "user"
        avi     = "⚡" if role == "assistant" else "🧑"
        rowc    = "" if role == "assistant" else "user"
        bubc    = "ai" if role == "assistant" else "user"

        st.markdown(f"""
        <div class="msg-row {rowc}">
          <div class="av {avc}">{avi}</div>
          <div class="bw">
            <div class="bubble {bubc}">{content}</div>
            <div class="bf"><span>{stamp}</span>
              <span class="cp" onclick="navigator.clipboard.writeText(this.closest('.bw').querySelector('.bubble').innerText)">📋 copy</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  INPUT BAR
# ═══════════════════════════════════════════════
prompt = st.chat_input("Ask anything about your enterprise knowledge base…")
st.markdown('<div class="inp-hint">↵ send · Shift+↵ new line · Powered by RAG + PydanticAI</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  PROCESS PROMPT
# ═══════════════════════════════════════════════
if prompt:
    with lf_span("User Chat Interaction", user_query=prompt, session_id=st.session_state.session_id):
        st.session_state.messages.append({"role": "user", "content": prompt, "ts": ts()})

    # Animated thinking card
    STEPS = [
        ("🔍", "Retrieving knowledge"),
        ("🧠", "Reasoning over context"),
        ("📚", "Analysing sources"),
        ("✨", "Generating answer"),
    ]

    def render_think(active: int) -> str:
        rows = ""
        for i, (icon, label) in enumerate(STEPS):
            cls  = "done" if i < active else ("active" if i == active else "")
            tick = "✓ " if i < active else ""
            rows += f'<div class="step {cls}"><span>{icon}</span>{tick}{label}</div>'
        return (
            '<div class="think-card">'
            '<div class="think-title">'
            '<div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>'
            'Agent working…</div>' + rows + '</div>'
        )

    think_ph = st.empty()
    data: dict = {}
    err: str   = ""

    for i in range(len(STEPS)):
        think_ph.markdown(render_think(i), unsafe_allow_html=True)
        if i < len(STEPS) - 1:
            time.sleep(0.42)

    try:
        with lf_span("Calling RAG Backend"):
            data = call_backend(prompt, st.session_state.session_id)
    except Exception as e:
        if LOGFIRE_OK:
            logfire.error("Backend error", error=str(e))
        err = str(e)

    think_ph.empty()

    if err:
        st.error(f"❌ Could not reach backend — {err}")
        st.stop()

    # Backend thought steps
    steps_from_be = data.get("thought process", [])
    if steps_from_be:
        rows_html = "".join(
            f'<div class="step done"><span>⚙</span>{s}</div>'
            for s in steps_from_be
        )
        st.markdown(
            f'<div class="think-card" style="max-width:820px;margin:0 auto 18px;">'
            f'<div class="think-title">🧩 Agent Thought Process</div>{rows_html}</div>',
            unsafe_allow_html=True,
        )

    # Sources
    sources = data.get("sources", [])
    if sources:
        cards = "".join(
            f'<div class="src-card">'
            f'<div style="display:flex;align-items:flex-start;gap:7px">'
            f'<span class="src-num">{i+1}</span>'
            f'<span class="src-prev">{s[:190].replace(chr(10)," ")}…</span>'
            f'</div></div>'
            for i, s in enumerate(sources)
        )
        st.markdown(
            f'<div class="src-wrap" style="max-width:820px;margin:0 auto 18px;">'
            f'<div class="src-hdr">📄 Retrieved {len(sources)} source chunk(s)</div>{cards}</div>',
            unsafe_allow_html=True,
        )

    # Streaming answer
    full_answer = data.get("answer", "No response received.")
    ans_ph      = st.empty()
    curr        = ""
    stamp_now   = ts()

    for ch in full_answer:
        curr += ch
        ans_ph.markdown(
            f'<div class="msgs-inner" style="max-width:820px;margin:0 auto;">'
            f'<div class="msg-row"><div class="av ai">⚡</div>'
            f'<div class="bw"><div class="bubble ai">{curr}<span style="opacity:.45">▌</span></div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        time.sleep(0.006)

    ans_ph.empty()
    st.session_state.messages.append({"role": "assistant", "content": full_answer, "ts": stamp_now})

    if LOGFIRE_OK:
        logfire.info("Chat cycle complete", session_id=st.session_state.session_id)

    st.rerun()