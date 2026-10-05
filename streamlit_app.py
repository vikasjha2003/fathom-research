"""Fathom Research - Streamlit front end for the LangGraph research pipeline."""
import re
import time

import streamlit as st

st.set_page_config(page_title="Fathom Research", page_icon="🌊", layout="wide")

import main as pipeline  # noqa: E402  (importing builds the graph)

# ---------- Styling ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Inter+Tight:wght@400;500;600&display=swap');
:root{--ink:#0c2a33;--sea:#0f7c8a;--brass:#b07d1e;--paper:#f4f7f7;--line:#d5e0e2;--mute:#5d737a}
html,body,[class*="css"]{font-family:'Inter Tight',sans-serif}
.stApp{background:var(--paper)}
.block-container{padding-top:2.2rem;max-width:1100px}
[data-testid="stSidebar"]{background:var(--ink)}
[data-testid="stSidebar"] *{color:#d9ecef !important}
h1,h2,h3{font-family:'Newsreader',serif !important;color:var(--ink);letter-spacing:-.01em}
.brand{font-family:'Newsreader',serif;font-size:1.7rem;font-weight:600;margin-bottom:.1rem}
.hero h1{font-size:3.4rem;line-height:1.05;margin:0 0 .6rem;font-weight:600}
.hero p{font-size:1.15rem;color:var(--mute);max-width:36rem;margin:0 0 1.6rem}
.tracker{display:flex;gap:0;margin:1.2rem 0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff}
.stage{flex:1;padding:.85rem 1rem;border-right:1px solid var(--line);color:var(--mute);font-weight:500}
.stage:last-child{border-right:0}
.stage small{display:block;font-weight:400;font-size:.78rem;margin-top:.15rem}
.stage.active{background:var(--sea);color:#fff}
.stage.active::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:#fff;margin-right:.5rem;animation:p 1s infinite}
.stage.done{background:#e6f2f3;color:var(--ink)}
.stage.done::before{content:"✓ ";color:var(--sea)}
@keyframes p{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.stage.active::before{animation:none}}
.metric{background:#fff;border:1px solid var(--line);border-radius:10px;padding:.9rem 1.1rem}
.metric b{display:block;font-family:'Newsreader',serif;font-size:1.9rem;color:var(--ink)}
.metric span{color:var(--mute);font-size:.85rem}
.metric.ok b{color:var(--sea)} .metric.warn b{color:var(--brass)}
.source{background:#fff;border:1px solid var(--line);border-left:3px solid var(--sea);border-radius:6px;padding:.7rem 1rem;margin-bottom:.6rem}
.source a{color:var(--ink);font-weight:600;text-decoration:none}
.source div{color:var(--mute);font-size:.8rem;word-break:break-all}
.report{background:#fff;border:1px solid var(--line);border-radius:10px;padding:1.6rem 2.2rem;font-family:'Newsreader',serif;font-size:1.08rem;line-height:1.7}
.stButton>button[kind="primary"]{background:var(--sea);border:0;font-weight:600}

/* ---- Theme-proofing: force the light palette even if Streamlit is in dark mode ---- */
header[data-testid="stHeader"]{background:var(--paper) !important}
header[data-testid="stHeader"] *{color:var(--ink) !important}
.block-container h1,.block-container h2,.block-container h3{color:var(--ink) !important}
.block-container p,.block-container li,.block-container label,
[data-testid="stWidgetLabel"] p,[data-testid="stMarkdownContainer"] p{color:var(--ink)}
.block-container .hero p{color:var(--mute)}
.block-container .metric span,.block-container .source div{color:var(--mute)}
.block-container .stage{color:var(--mute)}
.block-container .stage.done{color:var(--ink)}
.block-container .stage.active{color:#fff}
[data-baseweb="input"],[data-baseweb="base-input"]{background:#fff !important;border-color:var(--line) !important}
.stTextInput input{background:#fff !important;color:var(--ink) !important;-webkit-text-fill-color:var(--ink) !important}
.stTextInput input::placeholder{color:#8aa0a6 !important;-webkit-text-fill-color:#8aa0a6 !important}
.stButton>button,.stDownloadButton>button{background:#fff;color:var(--ink);border:1px solid var(--line)}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--sea);color:var(--sea)}
.stButton>button p,.stDownloadButton>button p{color:inherit !important}
.stButton>button[kind="primary"]{background:var(--sea);color:#fff;border:0}
.stButton>button[kind="primary"]:hover{background:#0b6572;color:#fff}
.stButton>button[kind="primary"] p{color:#fff !important}
.stButton>button:disabled{opacity:.45}
details{background:#fff !important;border:1px solid var(--line) !important;border-radius:10px}
details summary,details summary *{color:var(--ink) !important}
button[data-baseweb="tab"] p{color:var(--mute) !important}
button[data-baseweb="tab"][aria-selected="true"] p{color:var(--sea) !important}
[data-testid="stAlert"] *{color:var(--ink) !important}
.report,.report *{color:var(--ink)}
</style>
""",
    unsafe_allow_html=True,
)

STAGES = [("Search", "Querying the web"), ("Read", "Scraping top sources"),
          ("Write", "Drafting the report"), ("Review", "Critic scoring")]
NODE_STAGE = {"searcher": 0, "search_tool": 0, "extract_search_result": 0,
              "reader": 1, "read_tool": 1, "extract_read_result": 1,
              "writer": 2, "critic": 3}
EXAMPLES = ["Impact of AI agents on software development",
            "State of solid-state batteries in 2026",
            "How are cities adapting to extreme heat?"]


def tracker_html(active: int, finished: bool = False) -> str:
    cells = []
    for i, (name, sub) in enumerate(STAGES):
        cls = "done" if finished or i < active else "active" if i == active else ""
        cells.append(f'<div class="stage {cls}">{name}<small>{sub}</small></div>')
    return f'<div class="tracker">{"".join(cells)}</div>'


def parse_score(text: str) -> float:
    m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", text, re.I)
    return float(m.group(1)) if m else 0.0


def parse_sources(text: str):
    seen, out = set(), []
    for title, url in re.findall(r"Title:\s*(.*)\nURL:\s*(\S+)", text):
        if url not in seen:
            seen.add(url)
            out.append((title.strip() or url, url))
    return out


def metric(value, label, cls=""):
    return f'<div class="metric {cls}"><b>{value}</b><span>{label}</span></div>'


def run_pipeline(topic: str):
    state = {"topic": topic, "messages": [], "searcher": "", "reader": "",
             "writer": "", "critic": "", "is_approved": False, "attempt": 0,
             "search_attempts": 0, "read_attempts": 0, "reader_start": 0}
    history, start = [], time.time()
    slot = st.empty()
    slot.markdown(tracker_html(0), unsafe_allow_html=True)
    with st.status("Diving in…", expanded=True) as status:
        for chunk in pipeline.app.stream(state, config={"recursion_limit": 50},
                                         stream_mode="updates"):
            for node, upd in chunk.items():
                upd = upd or {}
                state.update({k: v for k, v in upd.items() if k != "messages"})
                slot.markdown(tracker_html(NODE_STAGE.get(node, 0)), unsafe_allow_html=True)
                if node == "extract_search_result":
                    st.write(f"Found **{len(parse_sources(state['searcher']))}** candidate sources")
                elif node == "extract_read_result":
                    n = state["reader"].count("\n\n---\n\n") + 1 if state["reader"] else 0
                    st.write(f"Read **{n}** pages in depth")
                elif node == "writer":
                    st.write(f"Draft {state['attempt']} written")
                elif node == "critic":
                    s = parse_score(state["critic"])
                    history.append({"attempt": state["attempt"], "score": s, "review": state["critic"]})
                    verdict = "approved" if state["is_approved"] else "needs revision"
                    st.write(f"Critic scored draft {state['attempt']}: **{s:g}/10** ({verdict})")
        slot.markdown(tracker_html(3, finished=True), unsafe_allow_html=True)
        status.update(label=f"Done in {time.time() - start:.0f}s", state="complete", expanded=False)
    return {"state": state, "history": history, "elapsed": time.time() - start}


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div class="brand">🌊 Fathom</div>', unsafe_allow_html=True)
    st.caption("Research that goes below the surface.")
    st.divider()
    st.markdown("**How it works**")
    st.caption("1. A search agent runs several web queries.\n\n2. A reader agent scrapes the best pages.\n\n"
               "3. A writer drafts a sourced report.\n\n4. A second model critiques it, and the writer revises.")
    st.divider()
    st.caption("Built with LangGraph · Groq · Gemini · Tavily")

# ---------- Hero / input ----------
st.markdown('<div class="hero"><h1>Fathom Research</h1>'
            "<p>Ask a question. Get a sourced report, drafted by one model and "
            "critiqued by another.</p></div>", unsafe_allow_html=True)

if "topic" not in st.session_state:
    st.session_state.topic = ""
cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    if c.button(ex, use_container_width=True):
        st.session_state.topic = ex

topic = st.text_input("Research topic", key="topic", placeholder="e.g. Impact of AI agents on software development")
go = st.button("Start research", type="primary", disabled=not topic.strip())

if go:
    try:
        st.session_state.result = run_pipeline(topic.strip())
    except Exception as e:  # surface API/key errors clearly
        st.error(f"The pipeline stopped: {e}. Check your API keys in `.env` and try again.")

# ---------- Results ----------
res = st.session_state.get("result")
if res:
    s, hist = res["state"], res["history"]
    score = parse_score(s["critic"])
    approved = s["is_approved"]
    sources = parse_sources(s["searcher"])

    m = st.columns(4)
    m[0].markdown(metric(f"{score:g}/10", "Final critic score", "ok" if approved else "warn"), unsafe_allow_html=True)
    m[1].markdown(metric("Approved" if approved else "Best effort", "Status", "ok" if approved else "warn"), unsafe_allow_html=True)
    m[2].markdown(metric(s["attempt"], "Drafts written"), unsafe_allow_html=True)
    m[3].markdown(metric(f"{res['elapsed']:.0f}s", "Total time"), unsafe_allow_html=True)
    st.write("")

    t1, t2, t3, t4 = st.tabs(["Report", f"Sources ({len(sources)})", "Critic & revisions", "Raw research"])
    with t1:
        st.markdown(f'<div class="report">\n\n{s["writer"]}\n\n</div>', unsafe_allow_html=True)
        st.download_button("Download report (.md)", s["writer"],
                           file_name="fathom_report.md", mime="text/markdown")
    with t2:
        if not sources:
            st.info("No sources were returned for this topic. Try rephrasing it.")
        for title, url in sources:
            st.markdown(f'<div class="source"><a href="{url}" target="_blank">{title}</a><div>{url}</div></div>',
                        unsafe_allow_html=True)
    with t3:
        if len(hist) > 1:
            st.line_chart({"Critic score": [h["score"] for h in hist]}, height=180)
        for h in reversed(hist):
            with st.expander(f"Draft {h['attempt']}: {h['score']:g}/10", expanded=h is hist[-1]):
                st.markdown(h["review"])
    with t4:
        st.subheader("Search results")
        st.text(s["searcher"] or "None")
        st.subheader("Pages read")
        st.text(s["reader"] or "None")